"""Contract tests for the call_log:delete grants migration (20260821000001).

Loads the migration module directly (no alembic env) and asserts the same
invariants the N1 grants migration test suite enforces: permission naming
convention, org_admin-only grant, and revision metadata sanity.

Mirrors backend/tests/auth/test_n1_org_admin_grants_migration.py.
"""

import importlib.util
import re
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / (
    "alembic/versions/20260821000001_add_call_log_delete_permission.py"
)


def _load_migration_module():
    """Import the migration file as a module without alembic bootstrap."""
    spec = importlib.util.spec_from_file_location(
        "call_log_delete_grants_migration", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_file_exists():
    assert MIGRATION_PATH.exists(), f"Expected migration at {MIGRATION_PATH}"


def test_permission_name_follows_contract():
    m = _load_migration_module()
    assert re.match(r"^[a-z_]+:[a-z_*]+$", m.PERMISSION_NAME)


def test_permission_is_call_log_delete():
    m = _load_migration_module()
    assert m.PERMISSION_NAME == "call_log:delete"


def test_regular_user_never_appears_in_upgrade_sql():
    """Product rule: recording deletion is admin-only; regular_user must
    not be granted call_log:delete by this migration."""
    m = _load_migration_module()
    import inspect

    upgrade_sql = inspect.getsource(m.upgrade)
    assert "regular_user" not in upgrade_sql


def test_downgrade_removes_grant_before_permission_row():
    """Downgrade must delete role_permissions rows before deleting the
    permission row to avoid dangling FK references."""
    m = _load_migration_module()
    import inspect

    source = inspect.getsource(m.downgrade)
    grant_delete_pos = source.find("DELETE FROM role_permissions")
    perm_delete_pos = source.rfind("DELETE FROM permissions")
    assert grant_delete_pos != -1, "downgrade must revoke role_permissions"
    assert perm_delete_pos != -1, "downgrade must remove the permission row"
    assert grant_delete_pos < perm_delete_pos


def test_revision_and_down_revision_match_project_conventions():
    m = _load_migration_module()
    assert m.revision == "20260821000001"
    assert m.down_revision == "20260819000001"
    assert m.branch_labels in (None, (), [])
    assert m.depends_on in (None, (), [])
