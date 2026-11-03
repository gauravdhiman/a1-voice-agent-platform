"""Tests for notification and low-credit outbox scheduling."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from src.notifications.retry_scheduler import NotificationRetryScheduler


@pytest.mark.asyncio
async def test_retry_scheduler_processes_all_durable_notification_queues():
    """One scheduler tick services durable email, billing, OAuth, and lead queues."""
    scheduler = NotificationRetryScheduler(check_interval_hours=1)
    scheduler.running = True

    with (
        patch(
            "src.notifications.service.notification_service.retry_failed_notifications",
            new=AsyncMock(),
        ) as retry_failed,
        patch(
            "src.billing.service.billing_service."
            "process_low_credit_notification_outbox",
            new=AsyncMock(),
        ) as process_outbox,
        patch(
            "src.notifications.lead_notification_outbox."
            "interest_lead_notification_outbox.process_pending",
            new=AsyncMock(),
        ) as process_leads,
        patch(
            "src.notifications.retry_scheduler.asyncio.sleep",
            new=AsyncMock(side_effect=asyncio.CancelledError),
        ),
    ):
        await scheduler._run_loop()

    retry_failed.assert_awaited_once()
    process_outbox.assert_awaited_once()
    process_leads.assert_awaited_once()


@pytest.mark.asyncio
async def test_one_pass_continues_after_a_queue_fails():
    """A queue failure is reported without skipping later recovery work."""
    scheduler = NotificationRetryScheduler()
    with (
        patch(
            "src.notifications.service.notification_service.retry_failed_notifications",
            new=AsyncMock(side_effect=RuntimeError("unavailable")),
        ),
        patch(
            "src.billing.service.billing_service."
            "process_low_credit_notification_outbox",
            new=AsyncMock(),
        ) as low_credit,
        patch(
            "src.notifications.oauth_attention_outbox."
            "oauth_attention_outbox.process_pending",
            new=AsyncMock(),
        ),
        patch(
            "src.notifications.lead_notification_outbox."
            "interest_lead_notification_outbox.process_pending",
            new=AsyncMock(),
        ),
        patch(
            "src.legal.update_outbox.legal_update_outbox.process_pending",
            new=AsyncMock(),
        ),
        patch(
            "src.call_artifacts.retention.remove_expired_recordings", new=AsyncMock()
        ),
        patch(
            "src.billing.voice_settlement_retry.retry_pending_voice_settlements",
            new=AsyncMock(),
        ) as settlement,
    ):
        failed = await scheduler.run_once()
    assert failed == ["notification_retry"]
    low_credit.assert_awaited_once()
    settlement.assert_awaited_once()


@pytest.mark.asyncio
async def test_one_pass_reports_failures_returned_in_summary():
    """Per-row failures are not mistaken for a fully successful pass."""
    scheduler = NotificationRetryScheduler()
    with (
        patch(
            "src.notifications.service.notification_service.retry_failed_notifications",
            new=AsyncMock(return_value={"failed": 2}),
        ),
        patch(
            "src.billing.service.billing_service."
            "process_low_credit_notification_outbox",
            new=AsyncMock(return_value={"failed": 0}),
        ),
        patch(
            "src.notifications.oauth_attention_outbox.oauth_attention_outbox.process_pending",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.notifications.lead_notification_outbox.interest_lead_notification_outbox.process_pending",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.legal.update_outbox.legal_update_outbox.process_pending",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.call_artifacts.retention.remove_expired_recordings",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "src.billing.voice_settlement_retry.retry_pending_voice_settlements",
            new=AsyncMock(return_value=0),
        ),
    ):
        assert await scheduler.run_once() == ["notification_retry"]
