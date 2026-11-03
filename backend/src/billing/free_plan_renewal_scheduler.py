"""Background renewal loop for free plans with recurring credit grants."""

from __future__ import annotations

import asyncio
import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from shared.config import settings, supabase_config

from .credit_grant_service import credit_grant_service

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_HOURS = 24


@dataclass
class FreeRenewalRunResult:
    """Counters emitted by one free-plan renewal pass."""

    processed: int = 0
    grants: int = 0
    skipped: int = 0
    errors: int = 0


class FreePlanRenewalService:
    """Renew due recurring free subscriptions without using Stripe."""

    def __init__(self) -> None:
        """Initialize the service with the configured database client."""
        self.supabase = supabase_config.client
        self.credit_grant_service = credit_grant_service

    async def process_due_renewals(
        self, now: Optional[datetime] = None
    ) -> FreeRenewalRunResult:
        """Grant due free-plan periods and advance their subscription windows.

        The grant is written before the period row advances. Grant keys make a
        retry safe if the process stops between those two operations.

        Args:
            now: UTC time used for deterministic tests; defaults to current UTC.

        Returns:
            Counts for processed, granted, skipped, and failed subscriptions.
        """
        now = now or datetime.now(timezone.utc)
        result = (
            self.supabase.table("organization_subscriptions")
            .select("*")
            .eq("status", "active")
            .execute()
        )
        summary = FreeRenewalRunResult()

        for subscription in result.data or []:
            metadata = subscription.get("metadata") or {}
            if (
                metadata.get("billing_mode") != "free"
                or metadata.get("credit_grant_policy") != "recurring"
            ):
                summary.skipped += 1
                continue

            period_end = _parse_datetime(subscription.get("current_period_end"))
            if period_end is None or period_end > now:
                summary.skipped += 1
                continue

            try:
                period_start = period_end
                next_period_end = _next_period_end(
                    period_start, metadata.get("billing_interval", "monthly")
                )
                while next_period_end <= now:
                    period_start = next_period_end
                    next_period_end = _next_period_end(
                        period_start, metadata.get("billing_interval", "monthly")
                    )

                grant_key = (
                    f"free-subscription:{subscription['id']}:"
                    f"{period_start.isoformat()}"
                )
                grant = await self.credit_grant_service.grant_for_subscription(
                    subscription,
                    grant_reason="free_renewal",
                    period_start=period_start,
                    period_end=next_period_end,
                    grant_key=grant_key,
                )
                if grant is not None:
                    summary.grants += 1

                self.supabase.table("organization_subscriptions").update(
                    {
                        "current_period_start": period_start.isoformat(),
                        "current_period_end": next_period_end.isoformat(),
                    }
                ).eq("id", subscription["id"]).execute()
                summary.processed += 1
            except Exception:
                summary.errors += 1
                logger.exception(
                    "Free-plan renewal failed for subscription %s",
                    subscription.get("id"),
                )

        return summary


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse a database timestamp and normalize it to UTC."""
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _next_period_end(start: datetime, billing_interval: str) -> datetime:
    """Calculate the next supported monthly or annual period boundary."""
    if billing_interval == "annual":
        try:
            return start.replace(year=start.year + 1)
        except ValueError:
            return start.replace(year=start.year + 1, day=28)

    next_month = start.month + 1
    next_year = start.year
    if next_month == 13:
        next_month = 1
        next_year += 1
    next_day = min(start.day, calendar.monthrange(next_year, next_month)[1])
    return start.replace(year=next_year, month=next_month, day=next_day)


class FreePlanRenewalScheduler:
    """Asyncio loop that invokes the free-plan renewal service."""

    def __init__(self, check_interval_hours: float = DEFAULT_CHECK_INTERVAL_HOURS):
        self.check_interval_hours = check_interval_hours
        self.service = FreePlanRenewalService()
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the recurring free-plan renewal task."""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the renewal task and await cancellation."""
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
        """Run renewal processing until shutdown."""
        while self.running:
            try:
                await self.run_once()
            except Exception:
                logger.exception("Free-plan renewal scheduler iteration failed")
            try:
                await asyncio.sleep(self.check_interval_hours * 3600)
            except asyncio.CancelledError:
                break

    async def run_once(self) -> FreeRenewalRunResult:
        """Run one renewal pass and return its per-row outcome counters."""
        return await self.service.process_due_renewals()


_free_plan_scheduler: Optional[FreePlanRenewalScheduler] = None


def _check_interval_hours() -> float:
    """Read the optional scheduler interval from application settings."""
    raw = getattr(settings, "free_plan_renewal_check_interval_hours", None)
    return float(raw) if raw is not None else float(DEFAULT_CHECK_INTERVAL_HOURS)


async def start_free_plan_renewal_scheduler() -> None:
    """Start the process-wide free-plan renewal scheduler."""
    global _free_plan_scheduler
    _free_plan_scheduler = FreePlanRenewalScheduler(_check_interval_hours())
    await _free_plan_scheduler.start()


async def stop_free_plan_renewal_scheduler() -> None:
    """Stop the process-wide free-plan renewal scheduler."""
    if _free_plan_scheduler:
        await _free_plan_scheduler.stop()
