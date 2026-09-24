"""Regression checks for organization OAuth notification migration safety."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock


def _load_migration():
    """Load the migration without initializing an application database."""
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260924000002_organization_notification_channels.py"
    )
    spec = spec_from_file_location("organization_notification_channels", migration_path)
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


def test_upgrade_adds_tenant_scoped_destinations_and_atomic_partial_update(monkeypatch):
    """Settings have DB constraints and concurrent partial changes use one RPC."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.upgrade()

    table_call = next(
        call
        for call in migration_ops.create_table.call_args_list
        if call.args[0] == "organization_notification_settings"
    )
    columns = {item.name: item for item in table_call.args[1:] if hasattr(item, "name")}
    assert {
        "organization_id",
        "alert_email",
        "sms_phone",
        "sms_enabled",
        "telegram_chat_id",
        "telegram_enabled",
        "updated_by",
    } <= set(columns)
    assert columns["organization_id"].primary_key is True
    checks = {item.name for item in table_call.args[1:] if getattr(item, "name", None)}
    assert "ck_org_notification_sms_enabled_has_phone" in checks
    assert "ck_org_notification_telegram_enabled_has_chat_id" in checks

    sql = " ".join(_executed_sql(migration_ops))
    assert "security definer" in sql
    assert "on conflict (organization_id) do update" in sql
    assert "p_updates ? 'sms_phone'" in sql
    assert "revoke all on function update_organization_notification_settings" in sql
    assert "grant execute on function update_organization_notification_settings" in sql


def test_upgrade_tracks_each_delivery_channel_and_claims_rows_once(monkeypatch):
    """Each recipient channel has an independent retry state under a row lease."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.upgrade()

    sql = " ".join(_executed_sql(migration_ops))
    assert "for update skip locked" in sql
    assert "outbox.lease_claim = p_claim" in sql
    assert "organization_telegram_state = 'pending'" in sql
    assert "organization_sms_state = 'pending'" in sql
    assert "p_attempted_organization_telegram" in sql
    assert "p_attempted_organization_sms" in sql
    assert (
        "alter table organization_notification_settings enable row level security"
        in sql
    )
    assert migration.revision == "20260924000002"
    assert migration.down_revision == "20260924000001"


def test_downgrade_restores_previous_outbox_rpc_signature(monkeypatch):
    """Rollback drops tenant settings and restores platform-only worker RPCs."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.downgrade()

    sql = " ".join(_executed_sql(migration_ops))
    assert "drop function complete_oauth_attention_outbox" in sql
    assert "create function complete_oauth_attention_outbox" in sql
    assert "organization_notification_settings" in sql
    migration_ops.drop_table.assert_called_once_with(
        "organization_notification_settings"
    )
    dropped = {call.args[1] for call in migration_ops.drop_column.call_args_list}
    assert {
        "organization_telegram_state",
        "organization_sms_state",
        "organization_telegram_attempts",
        "organization_sms_attempts",
    } <= dropped
