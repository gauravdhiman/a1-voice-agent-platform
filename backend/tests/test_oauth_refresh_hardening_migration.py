"""Regression coverage for the OAuth refresh fencing migration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock


def _load_migration():
    """Load the migration module without initializing an application database."""
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260924000001_harden_oauth_refresh_and_alerts.py"
    )
    spec = spec_from_file_location("oauth_refresh_hardening_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_upgrade_fences_refresh_writes_to_current_credentials_and_lease(
    monkeypatch,
) -> None:
    """A stale worker cannot overwrite a newer OAuth callback or lease owner."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.upgrade()

    sql = (
        " ".join(str(call.args[0]) for call in migration_ops.execute.call_args_list)
        .lower()
        .split()
    )
    sql = " ".join(sql)
    assert "new.oauth_credential_version := old.oauth_credential_version + 1" in sql
    assert "tool.oauth_credential_version = p_expected_version" in sql
    assert "lease.claim = p_claim" in sql
    assert "lease.locked_at >= now() - make_interval" in sql
    assert "tool.oauth_refresh_status = 'refreshing'" in sql
    assert "set sensitive_config = p_encrypted_config" in sql
    assert "new.oauth_refresh_status := 'ready'" in sql


def test_upgrade_adds_claimed_outbox_and_explicit_sms_opt_in(monkeypatch) -> None:
    """Concurrent workers share a fenced outbox; SMS stays explicitly opted in."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.upgrade()

    sql = (
        " ".join(str(call.args[0]) for call in migration_ops.execute.call_args_list)
        .lower()
        .split()
    )
    sql = " ".join(sql)
    assert "for update skip locked" in sql
    assert "outbox.lease_claim = p_claim" in sql
    assert "alter table oauth_attention_outbox enable row level security" in sql

    table_call = next(
        call
        for call in migration_ops.create_table.call_args_list
        if call.args[0] == "oauth_attention_outbox"
    )
    columns = {item.name: item for item in table_call.args[1:] if hasattr(item, "name")}
    assert {"event_key", "telegram_state", "sms_state", "lease_claim"} <= set(columns)
    assert columns["event_key"].unique is True

    added_columns = [call.args[1] for call in migration_ops.add_column.call_args_list]
    sms_opt_in = next(
        column
        for column in added_columns
        if column.name == "platform_admin_sms_notifications_enabled"
    )
    assert sms_opt_in.nullable is False
    assert str(sms_opt_in.server_default.arg) == "false"


def test_downgrade_removes_refresh_and_notification_objects(monkeypatch) -> None:
    """Rollback removes every database object introduced by the revision."""
    migration = _load_migration()
    migration_ops = MagicMock()
    monkeypatch.setattr(migration, "op", migration_ops)

    migration.downgrade()

    sql = (
        " ".join(str(call.args[0]) for call in migration_ops.execute.call_args_list)
        .lower()
        .split()
    )
    sql = " ".join(sql)
    assert "drop function if exists complete_token_refresh" in sql
    assert "drop function if exists claim_oauth_attention_outbox" in sql
    assert (
        "drop trigger if exists " "trg_reset_oauth_refresh_state_on_credentials_change"
    ) in sql
    migration_ops.drop_table.assert_called_once_with("oauth_attention_outbox")
    dropped_columns = {
        call.args[1] for call in migration_ops.drop_column.call_args_list
    }
    assert {
        "oauth_credential_version",
        "oauth_refresh_status",
        "platform_admin_sms_phone",
        "platform_admin_sms_notifications_enabled",
    } <= dropped_columns
