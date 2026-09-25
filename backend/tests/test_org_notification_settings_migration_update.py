"""Regression checks for destination-driven organization notification settings."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _load_migration():
    """Load the migration without initializing an application database."""
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260925000001_org_notification_settings_channels.py"
    )
    spec = spec_from_file_location("org_notification_settings_channels", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _executed_sql(migration_ops):
    return (
        " ".join(str(call.args[0]) for call in migration_ops.execute.call_args_list)
        .lower()
        .split()
    )


def test_upgrade_preserves_opt_out_and_stores_encrypted_org_bot_token(monkeypatch):
    """The schema removes switches without silently enabling old destinations."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.upgrade()

    add_column = migration_ops.add_column.call_args
    assert add_column.args[0] == "organization_notification_settings"
    assert add_column.args[1].name == "telegram_bot_token_encrypted"
    dropped = {call.args[1] for call in migration_ops.drop_column.call_args_list}
    assert dropped == {"sms_enabled", "telegram_enabled"}
    sql = " ".join(_executed_sql(migration_ops))
    assert "sms_phone = case when sms_enabled then sms_phone else null end" in sql
    assert "when telegram_enabled then telegram_chat_id else null end" in sql
    assert "p_updates ? 'telegram_bot_token_encrypted'" in sql
    assert "security definer" in sql
    assert migration.revision == "20260925000001"
    assert migration.down_revision == "20260924000002"


def test_downgrade_refuses_to_discard_organization_telegram_state(monkeypatch):
    """A legacy schema cannot safely restore org Telegram channel state."""
    migration = _load_migration()
    migration_ops = MagicMock()
    migration_ops.get_bind.return_value.execute.return_value.scalar_one.return_value = 1
    monkeypatch.setattr(migration, "op", migration_ops)

    with pytest.raises(RuntimeError, match="Telegram destination or bot token"):
        migration.downgrade()

    migration_ops.drop_column.assert_not_called()
    query = migration_ops.get_bind.return_value.execute.call_args.args[0]
    assert "OR telegram_chat_id IS NOT NULL" in str(query)


def test_downgrade_restores_legacy_fields_when_no_bot_token_would_be_lost(monkeypatch):
    """A safe rollback restores the historical schema and derives SMS status."""
    migration = _load_migration()
    migration_ops = MagicMock()
    migration_ops.get_bind.return_value.execute.return_value.scalar_one.return_value = 0
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.downgrade()

    columns = {call.args[1].name for call in migration_ops.add_column.call_args_list}
    assert columns == {"sms_enabled", "telegram_enabled"}
    assert "telegram_bot_token_encrypted" in {
        call.args[1] for call in migration_ops.drop_column.call_args_list
    }
    sql = " ".join(_executed_sql(migration_ops))
    assert "sms_enabled = sms_phone is not null" in sql
    assert "telegram_enabled = false" in sql
    assert "create function update_organization_notification_settings" in sql
