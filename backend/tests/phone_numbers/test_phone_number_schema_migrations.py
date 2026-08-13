"""Tests for phone-number schema compatibility migrations."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock, patch

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20260812000007_expand_phone_number_status_length.py"
)
SPEC = spec_from_file_location("phone_number_status_migration", MIGRATION_PATH)
assert SPEC and SPEC.loader
MIGRATION = module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_phone_number_status_migration_supports_verification_required() -> None:
    """The status column is wide enough for every supported lifecycle value."""
    migration_op = MagicMock()
    MIGRATION.op = migration_op

    MIGRATION.upgrade()

    migration_op.alter_column.assert_called_once()
    args, kwargs = migration_op.alter_column.call_args
    assert args == ("phone_numbers", "status")
    assert kwargs["existing_type"].length == 20
    assert kwargs["type_"].length == 30
    assert kwargs["existing_nullable"] is False


def test_phone_number_webhook_token_migration_adds_encrypted_storage() -> None:
    """Customer setup tokens have a dedicated encrypted database column."""
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "20260812000008_add_phone_number_webhook_token_encryption.py"
    )
    migration_spec = spec_from_file_location(
        "phone_number_webhook_token_migration", migration_path
    )
    assert migration_spec and migration_spec.loader
    migration = module_from_spec(migration_spec)
    migration_spec.loader.exec_module(migration)

    migration_op = MagicMock()
    migration.op = migration_op

    migration.upgrade()

    migration_op.add_column.assert_called_once()
    args, kwargs = migration_op.add_column.call_args
    assert args[0] == "phone_numbers"
    assert args[1].name == "connection_token_encrypted"
    assert kwargs == {}


def test_phone_number_performance_migration_adds_agent_lookup_indexes() -> None:
    """Production deploys indexes for agent and assigned-number lookups."""
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "20260812000009_add_phone_number_lookup_indexes.py"
    )
    migration_spec = spec_from_file_location(
        "phone_number_lookup_indexes_migration", migration_path
    )
    assert migration_spec and migration_spec.loader
    migration = module_from_spec(migration_spec)
    migration_spec.loader.exec_module(migration)

    operations = []
    with patch.object(
        migration.op,
        "create_index",
        side_effect=lambda *args, **kwargs: operations.append((args, kwargs)),
    ):
        migration.upgrade()

    names = [operation[0][0] for operation in operations]
    assert "ix_voice_agents_organization_active" in names
    assert "ix_phone_numbers_organization_agent_active" in names
    phone_index = next(
        operation
        for operation in operations
        if operation[0][0] == "ix_phone_numbers_organization_agent_active"
    )
    assert phone_index[0][2] == ["organization_id", "assigned_agent_id"]
    assert "cancelled" in str(phone_index[1]["postgresql_where"])
    assert "disconnected" in str(phone_index[1]["postgresql_where"])
