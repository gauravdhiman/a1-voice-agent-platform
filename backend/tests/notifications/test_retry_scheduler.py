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
            "src.notifications.retry_scheduler.notification_service.retry_failed_notifications",
            new=AsyncMock(),
        ) as retry_failed,
        patch(
            "src.billing.service.billing_service.process_low_credit_notification_outbox",
            new=AsyncMock(),
        ) as process_outbox,
        patch(
            "src.notifications.lead_notification_outbox.interest_lead_notification_outbox.process_pending",
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
