"""Durable platform-admin lead alert delivery and retry behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.notifications.lead_notification_outbox import (
    InterestLeadNotificationOutbox,
)


def _outbox_row():
    return {
        "id": str(uuid4()),
        "lead_id": str(uuid4()),
        "email_state": "pending",
        "telegram_state": "pending",
        "whatsapp_state": "pending",
        "email_attempts": 0,
        "telegram_attempts": 0,
        "whatsapp_attempts": 0,
    }


def _outbox(*, row=None, settings=None, notifier=None):
    row = row or _outbox_row()
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=[row])
    platform_settings = settings or SimpleNamespace(
        telegram_notifications_enabled=True,
        platform_admin_whatsapp_notifications_enabled=True,
        platform_admin_whatsapp_phone="+15551234567",
    )
    settings_service = SimpleNamespace(
        get_settings=AsyncMock(return_value=platform_settings)
    )
    lead = SimpleNamespace(id=row["lead_id"])
    leads = SimpleNamespace(get_lead=AsyncMock(return_value=(lead, None)))
    if notifier is None:
        notifier = MagicMock()
        notifier._email_is_configured.return_value = True
        notifier._send_email = AsyncMock()
        notifier._send_telegram = AsyncMock()
        notifier._send_whatsapp = AsyncMock()
    config = SimpleNamespace(service_client=supabase, client=supabase)
    return (
        InterestLeadNotificationOutbox(
            notifier=notifier,
            lead_service_override=leads,
            platform_settings_service=settings_service,
            supabase_config_override=config,
        ),
        supabase,
        notifier,
        row,
    )


@pytest.mark.asyncio
async def test_outbox_sends_and_acknowledges_all_configured_admin_channels():
    outbox, supabase, notifier, row = _outbox()

    with patch(
        "src.notifications.lead_notification_outbox.whatsapp_service.is_configured",
        return_value=True,
    ):
        processed = await outbox.process_pending()

    assert processed == 1
    notifier._send_email.assert_awaited_once()
    notifier._send_telegram.assert_awaited_once()
    notifier._send_whatsapp.assert_awaited_once()
    rpc_name, payload = supabase.rpc.call_args_list[1].args
    assert rpc_name == "complete_interest_lead_notification_outbox"
    assert payload["p_id"] == row["id"]
    assert payload["p_email_state"] == "sent"
    assert payload["p_telegram_state"] == "sent"
    assert payload["p_whatsapp_state"] == "sent"
    assert payload["p_attempted_email"] is True
    assert payload["p_attempted_telegram"] is True
    assert payload["p_attempted_whatsapp"] is True
    assert payload["p_error_code"] is None


@pytest.mark.asyncio
async def test_outbox_retries_only_the_channel_that_failed():
    notifier = MagicMock()
    notifier._email_is_configured.return_value = True
    notifier._send_email = AsyncMock()
    notifier._send_telegram = AsyncMock(side_effect=RuntimeError("provider error"))
    notifier._send_whatsapp = AsyncMock()
    outbox, supabase, _notifier, _row = _outbox(notifier=notifier)

    with patch(
        "src.notifications.lead_notification_outbox.whatsapp_service.is_configured",
        return_value=True,
    ):
        await outbox.process_pending()

    _rpc_name, payload = supabase.rpc.call_args_list[1].args
    assert payload["p_email_state"] == "sent"
    assert payload["p_telegram_state"] == "pending"
    assert payload["p_whatsapp_state"] == "sent"
    assert payload["p_error_code"] == "telegram_delivery_failed"
    assert payload["p_retry_seconds"] >= 300
    assert payload["p_attempted_email"] is True
    assert payload["p_attempted_telegram"] is True
    assert payload["p_attempted_whatsapp"] is True


@pytest.mark.asyncio
async def test_missing_email_configuration_stays_retryable():
    settings = SimpleNamespace(
        telegram_notifications_enabled=False,
        platform_admin_whatsapp_notifications_enabled=False,
        platform_admin_whatsapp_phone=None,
    )
    notifier = MagicMock()
    notifier._email_is_configured.return_value = False
    notifier._send_email = AsyncMock()
    notifier._send_telegram = AsyncMock()
    notifier._send_whatsapp = AsyncMock()
    outbox, supabase, _notifier, _row = _outbox(
        settings=settings, notifier=notifier
    )

    await outbox.process_pending()

    _rpc_name, payload = supabase.rpc.call_args_list[1].args
    assert payload["p_email_state"] == "pending"
    assert payload["p_telegram_state"] == "skipped"
    assert payload["p_whatsapp_state"] == "skipped"
    assert payload["p_error_code"] == "email_configuration_missing"
    notifier._send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_strict_pass_reports_delivery_failure_after_attempting_all_rows():
    outbox, supabase, _, row = _outbox()
    supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=[row, row])
    outbox._deliver_claimed = AsyncMock(side_effect=[False, True])

    with pytest.raises(RuntimeError, match="delivery failed"):
        await outbox.process_pending(strict=True)
    assert outbox._deliver_claimed.await_count == 2
