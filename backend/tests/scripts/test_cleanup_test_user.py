"""Tests for the ``scripts/cleanup_test_user.py`` dev helper.

The script is a standalone file (not a package), so these tests load it via
``importlib`` from its on-disk location and exercise the pure decision logic and
the CLI/db flow with mocked psycopg2 connections.
"""

import importlib.util
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cleanup_test_user.py"


@pytest.fixture(scope="module")
def mod():
    """Load the cleanup script into a fresh module."""
    spec = importlib.util.spec_from_file_location(
        "cleanup_test_user", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(SCRIPT_PATH)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    """Minimal stand-in for a psycopg2 cursor that records executed SQL."""

    def __init__(self, rows=None):
        self.executed = []  # list of (sql, params)
        self._rows = rows or []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        return self

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    """A tiny psycopg2-like connection sufficient for the deletion helpers."""

    def __init__(self, cursor_rows=None):
        self.pending_cursor = FakeCursor(rows=cursor_rows)
        self.last_cursor = None
        self.closed = False

    def cursor(self, cursor_factory=None):
        self.last_cursor = self.pending_cursor
        return self.last_cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        self.closed = True


@pytest.fixture
def db():
    """A fake connection for mutation / plan / main tests."""
    return FakeConn()


def make_row(**kwargs):
    """Build an org row dict suitable for :func:`classify_org`."""
    row = {
        "org_id": str(uuid.uuid4()),
        "org_name": "Test Org",
        "org_slug": "test-org",
        "member_ids": [],
        "member_count": 0,
    }
    row.update(kwargs)
    return row


class TestClassifyOrg:
    """Decision logic: delete only sole-member orgs."""

    def test_sole_member_org_is_deleted(self, mod):
        uid = str(uuid.uuid4())
        row = make_row(member_ids=[uid], member_count=1)
        plan = mod.classify_org(row, uid)
        assert plan.delete_org is True
        assert plan.shared_with_user_ids == []
        assert plan.summary.startswith("[DELETE ORG]")

    def test_shared_org_is_kept(self, mod):
        uid = str(uuid.uuid4())
        other = str(uuid.uuid4())
        row = make_row(member_ids=[uid, other], member_count=2)
        plan = mod.classify_org(row, uid)
        assert plan.delete_org is False
        assert plan.shared_with_user_ids == [other]
        assert plan.summary.startswith("[KEEP ORG]")

    def test_shared_org_count_reporting(self, mod):
        uid = str(uuid.uuid4())
        row = make_row(member_ids=[uid, "a", "b"], member_count=3)
        plan = mod.classify_org(row, uid)
        assert plan.delete_org is False
        assert plan.member_count == 3


class TestBuildCleanupPlan:
    """Plan builder only deletes orgs where the user is the only member."""

    def test_plan_splits_delete_and_keep_orgs(self, mod, db):
        uid = str(uuid.uuid4())
        sole_id = str(uuid.uuid4())
        shared_id = str(uuid.uuid4())
        rows = [
            make_row(
                org_id=sole_id,
                org_name="Sole",
                org_slug="sole",
                member_ids=[uid],
                member_count=1,
            ),
            make_row(
                org_id=shared_id,
                org_name="Shared",
                org_slug="shared",
                member_ids=[uid, str(uuid.uuid4())],
                member_count=2,
            ),
        ]

        with patch.object(mod, "_list_user_orgs", return_value=rows) as mock_list:
            plan = mod.build_cleanup_plan(db, uid, "u@example.com")

        mock_list.assert_called_once_with(db, uid)
        assert plan.user_id == uid
        assert plan.user_email == "u@example.com"
        assert plan.delete_org_ids == [sole_id]
        assert plan.kept_org_ids == [shared_id]


class TestListUserOrgs:
    """Org listing must normalize member ids returned by psycopg2.

    psycopg2 returns ``uuid[]`` (ARRAY_AGG output) as a raw Postgres array
    literal string such as ``{uuid-1,uuid-2}`` unless the uuid typecaster is
    registered. Iterating that string directly yields individual characters,
    so the helper must parse the literal into a real list before counting.
    """

    def test_parses_raw_pg_array_literal(self, mod, db):
        uid_a, uid_b = str(uuid.uuid4()), str(uuid.uuid4())
        db.pending_cursor._rows = [
            {
                "org_id": str(uuid.uuid4()),
                "org_name": "Test Org",
                "org_slug": "test-org",
                "member_ids": "{%s,%s}" % (uid_a, uid_b),
            }
        ]
        rows = mod._list_user_orgs(db, uid_a)
        assert len(rows) == 1
        assert rows[0]["member_ids"] == [uid_a, uid_b]
        assert rows[0]["member_count"] == 2

    def test_parses_single_member_raw_literal(self, mod, db):
        uid = str(uuid.uuid4())
        db.pending_cursor._rows = [
            {
                "org_id": str(uuid.uuid4()),
                "org_name": "Test Org",
                "org_slug": "test-org",
                "member_ids": "{%s}" % uid,
            }
        ]
        rows = mod._list_user_orgs(db, uid)
        assert rows[0]["member_ids"] == [uid]
        assert rows[0]["member_count"] == 1

    def test_handles_null_member_ids(self, mod, db):
        db.pending_cursor._rows = [
            {
                "org_id": str(uuid.uuid4()),
                "org_name": "Test Org",
                "org_slug": "test-org",
                "member_ids": None,
            }
        ]
        rows = mod._list_user_orgs(db, str(uuid.uuid4()))
        assert rows[0]["member_ids"] == []
        assert rows[0]["member_count"] == 0

    def test_aggregates_over_all_org_members_not_just_target(self, mod, db):
        """The org query must count every member, not just the target user.

        Filtering the outer WHERE by the target user's id would collapse the
        ``ARRAY_AGG`` to a single member and wrongly classify shared orgs as
        deletable. The query must scope by org membership instead: orgs the
        user belongs to, then aggregate across ALL of their members.
        """
        uid = str(uuid.uuid4())
        db.pending_cursor._rows = []
        mod._list_user_orgs(db, uid)
        sql = db.pending_cursor.executed[0][0]
        assert "WHERE ur.user_id = %s" not in sql
        assert "WHERE user_id = %s AND organization_id IS NOT NULL" in sql
        assert "ARRAY_AGG(DISTINCT ur.user_id)" in sql


class TestDeleteOperations:
    """Mutation primitives only delete the orgs/users they are told to."""

    def test_delete_organizations_iterates_over_deletable_orgs(self, mod, db):
        mod.delete_organizations(db, ["org-1", "org-2"])
        executed = db.pending_cursor.executed
        assert len(executed) == 2
        assert (executed[0][0], executed[0][1]) == (
            "DELETE FROM organizations WHERE id = %s",
            ("org-1",),
        )
        assert (executed[1][0], executed[1][1]) == (
            "DELETE FROM organizations WHERE id = %s",
            ("org-2",),
        )
    def test_delete_organizations_noop_when_empty(self, mod, db):
        mod.delete_organizations(db, [])
        assert db.last_cursor is None  # cursor never requested

    def test_delete_user_rows_deletes_non_cascading_tables(self, mod, db):
        uid = str(uuid.uuid4())
        mod._delete_user_rows(db, uid)
        executed = db.pending_cursor.executed
        assert len(executed) == 2
        tables = {sql.split("FROM ")[1].split(" ")[0] for sql, _ in executed}
        assert "notification_logs" in tables
        assert "email_verification_tokens" in tables

    def test_delete_user_deletes_auth_users_row(self, mod, db):
        uid = str(uuid.uuid4())
        mod.delete_user(db, uid)
        sql = db.pending_cursor.executed[0][0]
        assert "auth.users" in sql


class TestResolveDatabaseUrl:
    """URL resolution priority: arg > env > settings."""

    def test_prefers_arg_over_env(self, mod, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://env")
        with patch.object(
            mod, "settings", MagicMock(database_url="postgresql://settings")
        ):
            assert mod.resolve_database_url("postgresql://arg") == "postgresql://arg"

    def test_env_used_when_no_arg(self, mod, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://env")
        with patch.object(
            mod, "settings", MagicMock(database_url="postgresql://settings")
        ):
            assert mod.resolve_database_url(None) == "postgresql://env"


class TestMainFlow:
    """End-to-end CLI behavior with a fully mocked database connection."""

    def _run_main(self, mod, args, user, plan, confirm=True):
        """Run mod.main with a fake db and patched user/plan + connect."""
        db = FakeConn()
        with (
            patch.object(mod, "_database_url", return_value="postgresql://x"),
            patch("psycopg2.connect", return_value=db),
            patch.object(mod, "resolve_user", return_value=user),
            patch.object(mod, "build_cleanup_plan", return_value=plan),
            patch.object(mod, "_confirm", return_value=confirm),
            patch.object(mod, "delete_organizations") as mock_del_orgs,
            patch.object(mod, "_delete_user_rows") as mock_del_user_rows,
            patch.object(mod, "delete_user") as mock_del_user,
        ):
            code = mod.main(args)
        return code, db, mock_del_orgs, mock_del_user_rows, mock_del_user

    def test_dry_run_does_not_delete(self, mod):
        uid = str(uuid.uuid4())
        plan = mod.CleanupPlan(user_id=uid, user_email="t@example.com")
        code, db, mock_del_orgs, _, mock_del_user = self._run_main(
            mod,
            ["--email", "t@example.com"],
            user={"id": uid, "email": "t@example.com"},
            plan=plan,
        )
        assert code == 0
        mock_del_orgs.assert_not_called()
        mock_del_user.assert_not_called()
        assert db.closed is True

    def test_apply_deletes_user_and_sole_orgs(self, mod):
        uid = str(uuid.uuid4())
        sole_id = str(uuid.uuid4())
        plan = mod.CleanupPlan(user_id=uid, user_email="t@example.com")
        plan.orgs.append(
            mod.OrgPlan(
                org_id=sole_id,
                org_name="Sole",
                org_slug="sole",
                member_count=1,
                delete_org=True,
            )
        )
        code, db, mock_del_orgs, mock_del_user_rows, mock_del_user = self._run_main(
            mod,
            ["--email", "t@example.com", "--apply", "--yes"],
            user={"id": uid, "email": "t@example.com"},
            plan=plan,
        )
        assert code == 0
        mock_del_orgs.assert_called_once_with(db, [sole_id])
        mock_del_user_rows.assert_called_once_with(db, uid)
        mock_del_user.assert_called_once_with(db, uid)
        assert db.closed is True

    def test_apply_aborted_when_not_confirmed(self, mod):
        uid = str(uuid.uuid4())
        plan = mod.CleanupPlan(user_id=uid)
        code, db, mock_del_orgs, mock_del_user_rows, mock_del_user = self._run_main(
            mod,
            ["--email", "t@example.com", "--apply"],
            user={"id": uid, "email": "t@example.com"},
            plan=plan,
            confirm=False,
        )
        assert code == 0
        mock_del_orgs.assert_not_called()
        mock_del_user_rows.assert_not_called()
        mock_del_user.assert_not_called()
        assert db.closed is True

    def test_user_not_found_exits_1(self, mod):
        db = FakeConn()
        with (
            patch.object(mod, "_database_url", return_value="postgresql://x"),
            patch("psycopg2.connect", return_value=db),
            patch.object(mod, "resolve_user", return_value=None),
        ):
            code = mod.main(["--email", "missing@example.com"])
        assert code == 1
        assert db.closed is True