"""Contract tests for encrypted platform voice-provider credential storage."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261031000001_platform_voice_provider_credentials.py"
)


def _load_migration():
    """Load the Alembic revision without starting the migration environment."""
    spec = importlib.util.spec_from_file_location(
        "platform_voice_provider_credentials_migration", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_platform_preset_credential_migration():
    migration = _load_migration()

    assert migration.revision == "20261031000001"
    assert migration.down_revision == "20261030000001"
    assert migration.branch_labels in (None, (), [])
    assert migration.depends_on in (None, (), [])


def test_upgrade_creates_encrypted_provider_table_and_service_role_access():
    migration = _load_migration()
    migration.op = MagicMock()

    migration.upgrade()

    args, kwargs = migration.op.create_table.call_args
    assert args[0] == "platform_voice_provider_credentials"
    assert {column.name for column in args[1:] if hasattr(column, "name")} >= {
        "provider",
        "credential_encrypted",
        "updated_by",
        "created_at",
        "updated_at",
    }
    check_constraint = next(
        constraint for constraint in args if hasattr(constraint, "sqltext")
    )
    assert "provider IN ('google', 'deepgram', 'openai', 'cartesia'" in str(
        check_constraint.sqltext
    )
    assert kwargs == {}

    statements = [str(call.args[0]) for call in migration.op.execute.call_args_list]
    sql = "\n".join(statements)
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert (
        "REVOKE ALL ON TABLE platform_voice_provider_credentials "
        "FROM anon, authenticated" in sql
    )
    assert "GRANT SELECT, INSERT, UPDATE, DELETE" in sql
    assert "TO service_role" in sql
    assert "WITH CHECK (true)" in sql


def test_downgrade_drops_only_the_new_credentials_table():
    migration = _load_migration()
    migration.op = MagicMock()

    migration.downgrade()

    migration.op.drop_table.assert_called_once_with(
        "platform_voice_provider_credentials"
    )
    sql = "\n".join(str(call.args[0]) for call in migration.op.execute.call_args_list)
    assert "DROP POLICY IF EXISTS" in sql
    assert "ON platform_voice_provider_credentials" in sql
