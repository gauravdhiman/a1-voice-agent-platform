"""Contract tests for the legal document versioning migration.

The migration is loaded as a pure module with a recording ``alembic.op`` stub
so the DDL it emits can be asserted without a database. The contract pinned
here is the schema the service layer depends on:

- one draft and one current published version per document key (partial
  unique indexes),
- acceptances idempotent on ``(user_id, document_key, version_number)`` with a
  signup/oauth/reaccept source CHECK,
- outbox idempotent on ``(dispatch_id, user_id)`` with NULL ``processed_at``
  meaning pending,
- FK delete semantics: publish events survive their referenced version being
  deleted only for the SET NULL predecessor pointer; everything else cascades,
- RLS enabled on all four tables (service-role-only access),
- downgrade drops in dependency-safe order.
"""

import importlib.util
import sys
import types
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / (
    "alembic/versions/20261012000001_add_legal_document_versioning.py"
)

TABLES = (
    "legal_document_versions",
    "legal_document_publish_events",
    "legal_document_acceptances",
    "legal_update_notification_outbox",
)


class RecordingOp:
    """Records alembic operations instead of executing them."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def create_table(self, name, *columns, **kwargs):
        self.calls.append(("create_table", name, columns, kwargs))

    def create_index(self, name, table, columns, **kwargs):
        self.calls.append(("create_index", name, table, list(columns), kwargs))

    def drop_table(self, name):
        self.calls.append(("drop_table", name))

    def execute(self, sql):
        self.calls.append(("execute", sql))


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "legal_versioning_migration", MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {MIGRATION_PATH}")

    recording_op = RecordingOp()
    fake_alembic = types.ModuleType("alembic")
    fake_alembic.op = recording_op
    previous = sys.modules.get("alembic")
    sys.modules["alembic"] = fake_alembic
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is not None:
            sys.modules["alembic"] = previous
        else:
            del sys.modules["alembic"]
    return module, recording_op


def _upgrade_calls():
    module, recording_op = _load_migration()
    recording_op.calls.clear()
    module.upgrade()
    return recording_op.calls


def _columns(calls, table_name):
    create = next(c for c in calls if c[0] == "create_table" and c[1] == table_name)
    columns = {}
    for col in create[2]:
        name = getattr(col, "name", None) or getattr(col, "key", None)
        if name is not None:
            columns[name] = col
    return columns


def _constraints(calls, table_name):
    create = next(c for c in calls if c[0] == "create_table" and c[1] == table_name)
    unique, checks, fks = [], [], []
    for col in create[2]:
        if col.__class__.__name__ == "UniqueConstraint":
            unique.append(col)
        elif col.__class__.__name__ == "CheckConstraint":
            checks.append(col)
        elif col.__class__.__name__ == "ForeignKeyConstraint":
            fks.append(col)
    return unique, checks, fks


def _unique_columns(constraint) -> tuple:
    """Column names of an unbound UniqueConstraint (string col args)."""
    return tuple(constraint._pending_colargs)


def _fk_source(constraint) -> str:
    return constraint.column_keys[0]


def _fk_target(constraint) -> str:
    return constraint.elements[0]._colspec


class TestMigrationIdentity:
    def test_migration_file_exists(self):
        assert MIGRATION_PATH.exists()

    def test_revision_chain(self):
        module, _ = _load_migration()
        assert module.revision == "20261012000001"
        assert module.down_revision == "20261008000001"


class TestVersionsTableContract:
    def test_key_version_uniqueness(self):
        calls = _upgrade_calls()
        unique, checks, _ = _constraints(calls, "legal_document_versions")
        names = {_unique_columns(u) for u in unique}
        assert ("document_key", "version_number") in names

    def test_single_draft_and_single_current_partial_uniques(self):
        calls = _upgrade_calls()
        partial = {
            idx[1]: idx
            for idx in calls
            if idx[0] == "create_index" and idx[2] == "legal_document_versions"
        }
        draft = partial["ux_legal_document_versions_single_draft"]
        current = partial["ux_legal_document_versions_single_current"]
        assert draft[4].get("unique") is True
        assert "status = 'draft'" in str(draft[4].get("postgresql_where"))
        assert current[4].get("unique") is True
        assert "is_current" in str(current[4].get("postgresql_where"))

    def test_status_and_key_check_constraints(self):
        calls = _upgrade_calls()
        _, checks, _ = _constraints(calls, "legal_document_versions")
        by_name = {c.name: str(c.sqltext) for c in checks}
        assert by_name["ck_legal_document_versions_key"] == (
            "document_key IN ('terms', 'privacy')"
        )
        assert by_name["ck_legal_document_versions_status"] == (
            "status IN ('draft', 'published', 'deprecated', 'retired')"
        )

    def test_required_columns_exist(self):
        calls = _upgrade_calls()
        columns = _columns(calls, "legal_document_versions")
        for name in (
            "id",
            "document_key",
            "version_number",
            "status",
            "content_markdown",
            "summary_of_changes",
            "is_current",
            "published_at",
            "published_by",
            "created_by",
            "created_at",
            "updated_at",
        ):
            assert name in columns, f"missing column {name}"


class TestPublishEventsTableContract:
    def test_version_fks_cascade_and_set_null(self):
        calls = _upgrade_calls()
        _, _, fks = _constraints(calls, "legal_document_publish_events")
        by_column = {_fk_source(fk): fk for fk in fks}
        assert by_column["legal_document_version_id"].ondelete == "CASCADE"
        assert by_column["previous_legal_document_version_id"].ondelete == "SET NULL"
        targets = {_fk_target(fk) for fk in fks}
        assert targets == {"legal_document_versions.id"}

    def test_notify_and_dispatch_columns(self):
        calls = _upgrade_calls()
        columns = _columns(calls, "legal_document_publish_events")
        assert "notify_users" in columns
        assert "notified_count" in columns
        assert "dispatch_id" in columns
        assert "previous_legal_document_version_id" in columns


class TestAcceptancesTableContract:
    def test_unique_on_user_key_version(self):
        calls = _upgrade_calls()
        unique, _, _ = _constraints(calls, "legal_document_acceptances")
        names = {_unique_columns(u) for u in unique}
        assert ("user_id", "document_key", "version_number") in names

    def test_source_check_allows_signup_oauth_reaccept(self):
        calls = _upgrade_calls()
        _, checks, _ = _constraints(calls, "legal_document_acceptances")
        by_name = {c.name: str(c.sqltext) for c in checks}
        assert by_name["ck_legal_document_acceptances_source"] == (
            "source IN ('signup', 'oauth', 'reaccept')"
        )

    def test_audit_columns_are_nullable(self):
        calls = _upgrade_calls()
        columns = _columns(calls, "legal_document_acceptances")
        for name in ("user_agent", "ip_address"):
            assert name in columns
            assert getattr(columns[name], "nullable", False) is True


class TestOutboxTableContract:
    def test_unique_on_dispatch_user(self):
        calls = _upgrade_calls()
        unique, _, _ = _constraints(calls, "legal_update_notification_outbox")
        names = {_unique_columns(u) for u in unique}
        assert ("dispatch_id", "user_id") in names

    def test_processed_at_null_means_pending(self):
        calls = _upgrade_calls()
        columns = _columns(calls, "legal_update_notification_outbox")
        processed_at = columns["processed_at"]
        assert getattr(processed_at, "nullable", False) is True
        # Retry bookkeeping columns the scheduler depends on.
        for name in ("attempt_count", "last_attempt_at", "last_error"):
            assert name in columns

    def test_version_fk_cascades(self):
        calls = _upgrade_calls()
        _, _, fks = _constraints(calls, "legal_update_notification_outbox")
        assert _fk_source(fks[0]) == "legal_document_version_id"
        assert _fk_target(fks[0]) == "legal_document_versions.id"
        assert fks[0].ondelete == "CASCADE"

    def test_pending_and_dispatch_indexes(self):
        calls = _upgrade_calls()
        indexes = {
            idx[1]: idx
            for idx in calls
            if idx[0] == "create_index" and idx[2] == "legal_update_notification_outbox"
        }
        pending = indexes["ix_legal_update_notification_outbox_pending"]
        assert pending[3] == ["processed_at", "created_at"]
        assert indexes["ix_legal_update_notification_outbox_dispatch"][3] == [
            "dispatch_id"
        ]


class TestSecurityAndDowngrade:
    def test_rls_enabled_on_all_four_tables(self):
        calls = _upgrade_calls()
        rls = [c[1] for c in calls if c[0] == "execute"]
        for table in TABLES:
            assert any(
                f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql for sql in rls
            ), f"RLS must be enabled on {table}"

    def test_downgrade_drops_in_dependency_safe_order(self):
        module, recording_op = _load_migration()
        recording_op.calls.clear()
        module.downgrade()
        dropped = [c[1] for c in recording_op.calls if c[0] == "drop_table"]
        assert dropped == [
            "legal_update_notification_outbox",
            "legal_document_acceptances",
            "legal_document_publish_events",
            "legal_document_versions",
        ]
