"""Contract tests for the invitation-role schema migration."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20260909000001_add_invitation_roles.py"
)


def _load_migration():
    """Load the migration without bootstrapping an Alembic environment."""
    spec = importlib.util.spec_from_file_location(
        "invitation_roles_migration", MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _executed_sql(op: MagicMock) -> str:
    """Join migration SQL statements for readable contract assertions."""
    return "\n".join(str(call.args[0]) for call in op.execute.call_args_list)


def test_revision_is_connected_to_the_current_launch_head():
    """The migration must extend the launch branch's existing history."""
    migration = _load_migration()

    assert migration.revision == "20260909000001"
    assert migration.down_revision == "20260906000004"
    assert migration.branch_labels in (None, (), [])
    assert migration.depends_on in (None, (), [])


def test_upgrade_adds_role_storage_and_claims_the_selected_role():
    """Upgrade stores a safe role and applies it atomically on claim."""
    migration = _load_migration()
    migration.op = MagicMock()

    migration.upgrade()

    column = migration.op.add_column.call_args.args[1]
    assert column.name == "role_id"
    assert column.nullable is True
    migration.op.create_foreign_key.assert_called_once_with(
        "fk_invitations_role_id",
        "invitations",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    migration.op.create_index.assert_called_once_with(
        "idx_invitations_role_id", "invitations", ["role_id"]
    )

    sql = _executed_sql(migration.op)
    assert "CREATE OR REPLACE FUNCTION claim_invitation" in sql
    assert "name IN ('regular_user', 'org_admin')" in sql
    assert "ON CONFLICT (user_id, organization_id) DO NOTHING" in sql
    assert "invitation_role_invalid" in sql
    assert "GRANT EXECUTE ON FUNCTION claim_invitation(text, uuid, text)" in sql


def test_downgrade_restores_regular_user_only_claim_behavior():
    """Downgrade removes role storage and restores the legacy claim contract."""
    migration = _load_migration()
    migration.op = MagicMock()

    migration.downgrade()

    migration.op.drop_index.assert_called_once_with(
        "idx_invitations_role_id", table_name="invitations"
    )
    migration.op.drop_constraint.assert_called_once_with(
        "fk_invitations_role_id", "invitations", type_="foreignkey"
    )
    migration.op.drop_column.assert_called_once_with("invitations", "role_id")
    sql = _executed_sql(migration.op)
    assert "CREATE OR REPLACE FUNCTION claim_invitation" in sql
    assert "name = 'regular_user'" in sql
