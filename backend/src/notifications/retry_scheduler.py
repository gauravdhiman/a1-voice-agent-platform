"""Background scheduler for retrying durable notification deliveries."""

from __future__ import annotations

import asyncio
import importlib
import logging
from typing import Optional

from shared.config import settings

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
            await self.run_once()
            try:
                await asyncio.sleep(self.check_interval_hours * 3600)
            except asyncio.CancelledError:
                break

    async def run_once(self, *, strict: bool = False) -> list[str]:
        """Process recovery queues once and report raised or summarized failures.

        A failure in one queue must not prevent the remaining queues from being
        attempted. Some services still suppress their own errors, so this is
        not yet a complete success signal for an external scheduler.
        """
        # Resolve each dependency independently, preserving isolation when an
        # import fails and avoiding the billing -> notification import cycle.
        operations = (
            (
                "notification_retry",
                "src.notifications.service",
                "notification_service.retry_failed_notifications",
            ),
            (
                "low_credit",
                "src.billing.service",
                "billing_service.process_low_credit_notification_outbox",
            ),
            (
                "oauth_attention",
                "src.notifications.oauth_attention_outbox",
                "oauth_attention_outbox.process_pending",
            ),
            (
                "interest_lead",
                "src.notifications.lead_notification_outbox",
                "interest_lead_notification_outbox.process_pending",
            ),
            (
                "legal_update",
                "src.legal.update_outbox",
                "legal_update_outbox.process_pending",
            ),
            (
                "recording_retention",
                "src.call_artifacts.retention",
                "remove_expired_recordings",
            ),
            (
                "voice_settlement",
                "src.billing.voice_settlement_retry",
                "retry_pending_voice_settlements",
            ),
        )
        failed = []
        for name, module_name, path in operations:
            try:
                operation = importlib.import_module(module_name)
                for part in path.split("."):
                    operation = getattr(operation, part)
                if strict and name in {
                    "oauth_attention",
                    "interest_lead",
                    "recording_retention",
                }:
                    outcome = await operation(strict=True)
                else:
                    outcome = await operation()
                # Some services report row-level failures instead of raising.
                # Preserve those signals for the external worker and monitors.
                if isinstance(outcome, dict):
                    errors = outcome.get("failed", 0) or outcome.get("errors", 0)
                else:
                    errors = getattr(outcome, "failed", 0) or getattr(
                        outcome, "errors", 0
                    )
                if isinstance(errors, int) and errors > 0:
                    failed.append(name)
            except Exception:
                failed.append(name)
                logger.exception("Maintenance operation %s failed", name)
        return failed


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
    if _notification_retry_scheduler:
        await _notification_retry_scheduler.stop()
