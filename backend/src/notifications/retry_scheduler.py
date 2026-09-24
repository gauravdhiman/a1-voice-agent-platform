"""Background scheduler for retrying durable notification deliveries."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from shared.config import settings

from .service import notification_service

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_HOURS = 5 / 60


class NotificationRetryScheduler:
    """Loop that retries pending and failed provider deliveries."""

    def __init__(self, check_interval_hours: float = DEFAULT_CHECK_INTERVAL_HOURS):
        self.check_interval_hours = check_interval_hours
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the notification retry loop."""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the retry loop and await cancellation."""
        if not self.running:
            return
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        """Run notification retries until shutdown."""
        while self.running:
            try:
                await notification_service.retry_failed_notifications()
            except Exception:
                logger.exception("Notification retry scheduler iteration failed")
            try:
                # Import lazily to avoid a billing -> notification -> scheduler
                # import cycle during application startup.
                from src.billing.service import billing_service

                await billing_service.process_low_credit_notification_outbox()
            except Exception:
                logger.exception("Low-credit notification outbox iteration failed")
            try:
                from .oauth_attention_outbox import oauth_attention_outbox

                await oauth_attention_outbox.process_pending()
            except Exception:
                logger.exception("OAuth attention outbox iteration failed")
            try:
                await asyncio.sleep(self.check_interval_hours * 3600)
            except asyncio.CancelledError:
                break


_notification_retry_scheduler: Optional[NotificationRetryScheduler] = None


def _check_interval_hours() -> float:
    """Read the optional notification retry interval from application settings."""
    raw_minutes = getattr(settings, "notification_retry_check_interval_minutes", None)
    if raw_minutes is not None:
        return float(raw_minutes) / 60
    raw = getattr(settings, "notification_retry_check_interval_hours", None)
    return float(raw) if raw is not None else float(DEFAULT_CHECK_INTERVAL_HOURS)


async def start_notification_retry_scheduler() -> None:
    """Start the process-wide notification retry scheduler."""
    global _notification_retry_scheduler
    _notification_retry_scheduler = NotificationRetryScheduler(_check_interval_hours())
    await _notification_retry_scheduler.start()


async def stop_notification_retry_scheduler() -> None:
    """Stop the process-wide notification retry scheduler."""
    global _notification_retry_scheduler
    if _notification_retry_scheduler:
        await _notification_retry_scheduler.stop()
