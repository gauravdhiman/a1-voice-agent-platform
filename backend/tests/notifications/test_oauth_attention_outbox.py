"""Tests for durable platform-channel OAuth attention delivery."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.notifications.oauth_attention_outbox import OAuthAttentionOutbox


class _FakeQuery:
    def __init__(self, execute_data=None):
        self.execute_data = execute_data
        self.upsert_payload = None
        self.upsert_options = None

    def upsert(self, payload, **options):
        self.upsert_payload = payload
        self.upsert_options = options
        return self

    def execute(self):
        return SimpleNamespace(data=self.execute_data)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows
        self.rpc_calls = []
        self.table_query = _FakeQuery()

    def table(self, _name):
        return self.table_query

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        if name == "claim_oauth_attention_outbox":
            data = self.rows
        else:
            data = {"updated": True}
        return _FakeQuery(execute_data=data)


def _row(**overrides):
    row = {
        "id": str(uuid4()),
        "event_key": "oauth-attention:tool:v1:provider_invalid_grant:unknown",
        "organization_id": str(uuid4()),
        "payload": {
            "organization_name": "Example Org",
            "agent_name": "Support Agent",
            "tool_name": "Calendar",
            "status_text": "requires immediate action",
            "reason": "Reconnect the tool to restore access.",
            "action_url": "https://247ai.live/agents/agent-id?tab=tools",
        },
        "telegram_state": "pending",
        "sms_state": "pending",
        "telegram_attempts": 0,
        "sms_attempts": 0,
    }
    row.update(overrides)
    return row


def _settings(*, telegram=True, sms=False, sms_ready=False):
    return SimpleNamespace(
        platform_admin_sms_phone="+15551234567" if sms else None,
        platform_admin_sms_notifications_enabled=sms,
        sms_sender_configured=sms_ready,
        get_platform_admin_email=AsyncMock(return_value="admin@example.com"),
    )


def _organization_settings(
    *, telegram=False, sms=False, sms_ready=False, telegram_ready=False
):
    return SimpleNamespace(
        telegram_chat_id="-100987654321" if telegram else None,
        telegram_enabled=telegram,
        telegram_bot_configured=telegram_ready,
        sms_phone="+15557654321" if sms else None,
        sms_enabled=sms,
        sms_sender_configured=sms_ready,
    )


def _patch_organization_settings(monkeypatch, settings=None):
    settings = settings or _organization_settings()
    service = SimpleNamespace(get_settings=AsyncMock(return_value=settings))
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox."
        "organization_notification_settings_service",
        service,
    )
    return service


@pytest.mark.asyncio
async def test_outbox_retries_failed_telegram_and_skips_unconfigured_sms(monkeypatch):
    """A failed provider attempt stays queued with a safe error category."""
    row = _row()
    client = _FakeSupabase([row])
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.supabase_config",
        SimpleNamespace(service_client=client, client=client),
    )
    _patch_organization_settings(monkeypatch)
    settings_service = SimpleNamespace(
        get_settings=AsyncMock(return_value=_settings(telegram=True)),
        get_telegram_credentials=AsyncMock(return_value=("bot-token", "-100123", True)),
    )
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox."
        "platform_notification_settings_service",
        settings_service,
    )
    send = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.telegram_service.send_message", send
    )

    count = await OAuthAttentionOutbox().process_pending(event_key=row["event_key"])

    assert count == 1
    send.assert_awaited_once()
    assert "bot-token" not in send.await_args.args[2]
    name, completion = client.rpc_calls[-1]
    assert name == "complete_oauth_attention_outbox"
    assert completion["p_telegram_state"] == "pending"
    assert completion["p_sms_state"] == "skipped"
    assert completion["p_attempted_telegram"] is True
    assert completion["p_error_code"] == "provider_delivery_failed"
    assert completion["p_retry_seconds"] >= 60


@pytest.mark.asyncio
async def test_outbox_delivers_configured_telegram_and_sms(monkeypatch):
    """Configured channels are attempted once under one row claim."""
    row = _row()
    client = _FakeSupabase([row])
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.supabase_config",
        SimpleNamespace(service_client=client, client=client),
    )
    _patch_organization_settings(monkeypatch)
    settings_service = SimpleNamespace(
        get_settings=AsyncMock(return_value=_settings(sms=True, sms_ready=True)),
        get_telegram_credentials=AsyncMock(return_value=("bot-token", "-100123", True)),
    )
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox."
        "platform_notification_settings_service",
        settings_service,
    )
    telegram_send = AsyncMock(return_value=True)
    sms_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.telegram_service.send_message",
        telegram_send,
    )
    monkeypatch.setattr(
        "src.phone_numbers.twilio_service.twilio_service.send_sms", sms_send
    )

    count = await OAuthAttentionOutbox().process_pending()

    assert count == 1
    telegram_send.assert_awaited_once()
    sms_send.assert_awaited_once_with(
        "+15551234567",
        "24x7 AI OAuth connection needs attention. Organization: Example Org. "
        "Agent: Support Agent. Tool: Calendar. Status: requires immediate action. "
        "Reconnect the tool to restore access. Next step: open the agent Tools page: "
        "https://247ai.live/agents/agent-id?tab=tools",
    )
    name, completion = client.rpc_calls[-1]
    assert name == "complete_oauth_attention_outbox"
    assert completion["p_telegram_state"] == "sent"
    assert completion["p_sms_state"] == "sent"
    assert completion["p_attempted_telegram"] is True
    assert completion["p_attempted_sms"] is True
    assert completion["p_organization_telegram_state"] == "skipped"
    assert completion["p_organization_sms_state"] == "skipped"


@pytest.mark.asyncio
async def test_outbox_delivers_organization_channels_even_when_platform_telegram_is_off(
    monkeypatch,
):
    """Tenant opt-ins use provider credentials independently of platform opt-ins."""
    row = _row()
    client = _FakeSupabase([row])
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.supabase_config",
        SimpleNamespace(service_client=client, client=client),
    )
    _patch_organization_settings(
        monkeypatch,
        _organization_settings(
            telegram=True, sms=True, sms_ready=True, telegram_ready=True
        ),
    )
    settings_service = SimpleNamespace(
        get_settings=AsyncMock(return_value=_settings(sms=False)),
        get_telegram_credentials=AsyncMock(
            return_value=("bot-token", "-100platform", False)
        ),
    )
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox."
        "platform_notification_settings_service",
        settings_service,
    )
    telegram_send = AsyncMock(return_value=True)
    sms_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.telegram_service.send_message",
        telegram_send,
    )
    monkeypatch.setattr(
        "src.phone_numbers.twilio_service.twilio_service.send_sms", sms_send
    )

    count = await OAuthAttentionOutbox().process_pending()

    assert count == 1
    telegram_send.assert_awaited_once()
    assert telegram_send.await_args.args[:2] == ("bot-token", "-100987654321")
    sms_send.assert_awaited_once_with(
        "+15557654321", OAuthAttentionOutbox._sms_message(row["payload"])
    )
    completion = client.rpc_calls[-1][1]
    assert completion["p_telegram_state"] == "skipped"
    assert completion["p_sms_state"] == "skipped"
    assert completion["p_organization_telegram_state"] == "sent"
    assert completion["p_organization_sms_state"] == "sent"
    assert completion["p_attempted_organization_telegram"] is True
    assert completion["p_attempted_organization_sms"] is True


@pytest.mark.asyncio
async def test_outbox_retries_when_organization_provider_settings_cannot_be_loaded(
    monkeypatch,
):
    """Organization delivery stays pending while a settings read is unavailable."""
    row = _row()
    client = _FakeSupabase([row])
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.supabase_config",
        SimpleNamespace(service_client=client, client=client),
    )
    organization_service = SimpleNamespace(
        get_settings=AsyncMock(side_effect=RuntimeError("database unavailable"))
    )
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox."
        "organization_notification_settings_service",
        organization_service,
    )
    platform_service = SimpleNamespace(
        get_settings=AsyncMock(return_value=_settings()),
        get_telegram_credentials=AsyncMock(
            return_value=("bot-token", "-100platform", True)
        ),
    )
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox."
        "platform_notification_settings_service",
        platform_service,
    )
    telegram_send = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.telegram_service.send_message",
        telegram_send,
    )

    await OAuthAttentionOutbox().process_pending()

    telegram_send.assert_awaited_once()
    completion = client.rpc_calls[-1][1]
    assert completion["p_telegram_state"] == "sent"
    assert completion["p_organization_telegram_state"] == "pending"
    assert completion["p_organization_sms_state"] == "pending"
    assert completion["p_attempted_organization_telegram"] is True
    assert completion["p_attempted_organization_sms"] is True
    assert completion["p_error_code"] == "provider_delivery_failed"


@pytest.mark.asyncio
async def test_outbox_enqueue_is_idempotent_and_processes_immediately(monkeypatch):
    """An event is uniquely keyed and attempted as soon as it is queued."""
    client = _FakeSupabase([])
    monkeypatch.setattr(
        "src.notifications.oauth_attention_outbox.supabase_config",
        SimpleNamespace(service_client=client, client=client),
    )
    outbox = OAuthAttentionOutbox()
    await outbox.enqueue(
        event_key="oauth-attention:tool:v1:provider_invalid_grant:unknown",
        agent_tool_id=str(uuid4()),
        organization_id=str(uuid4()),
        payload={"tool_name": "Calendar"},
    )

    assert client.table_query.upsert_options == {
        "on_conflict": "event_key",
        "ignore_duplicates": True,
    }
    assert client.rpc_calls[0][0] == "claim_oauth_attention_outbox"
    assert (
        client.rpc_calls[0][1]["p_event_key"]
        == client.table_query.upsert_payload["event_key"]
    )
