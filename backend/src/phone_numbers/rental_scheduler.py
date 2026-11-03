"""Background scheduler for monthly phone-number rental billing."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from shared.config import settings

from .platform_settings_service import platform_phone_number_settings_service
from .service import PhoneNumberRentalRunResult, phone_number_service

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_HOURS = 24


class PhoneNumberRentalScheduler:
    """Daily loop that charges due rentals and releases expired past-due numbers."""

    def __init__(self, check_interval_hours: float = DEFAULT_CHECK_INTERVAL_HOURS):
        self.check_interval_hours = check_interval_hours
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the recurring phone-rental billing loop."""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the billing loop and await cancellation."""
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
        """Run due-rental processing until shutdown."""
        while self.running:
            try:
                await self.run_once()
            except Exception:
                logger.exception("Phone-rental scheduler iteration failed")
            try:
                interval_hours = await self._get_runtime_interval_hours()
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break

    async def run_once(self, *, guarded: bool = False) -> PhoneNumberRentalRunResult:
        """Run one phone-number lifecycle pass and return its outcome counters."""
        if guarded:
            return await phone_number_service.process_due_rentals(guarded=True)
        return await phone_number_service.process_due_rentals()

    async def _get_runtime_interval_hours(self) -> float:
        """Read the admin-configured cadence, with the startup value as fallback."""
        try:
            lifecycle_settings = (
                await platform_phone_number_settings_service.get_settings()
            )
            return min(
                lifecycle_settings.billing_check_interval_hours,
                lifecycle_settings.release_retry_interval_hours,
            )
        except Exception:
            logger.exception("Could not load runtime phone-rental interval")
            return self.check_interval_hours


_phone_number_rental_scheduler: Optional[PhoneNumberRentalScheduler] = None


def _check_interval_hours() -> float:
    """Run often enough to satisfy both billing and release retry cadences."""
    billing = getattr(settings, "phone_number_billing_check_interval_hours", None)
    release = getattr(settings, "phone_number_release_retry_interval_hours", None)
    intervals = [float(value) for value in (billing, release) if value is not None]
    return min(intervals) if intervals else float(DEFAULT_CHECK_INTERVAL_HOURS)


async def start_phone_number_rental_scheduler() -> None:
    """Start the process-wide phone-rental scheduler."""
    global _phone_number_rental_scheduler
    _phone_number_rental_scheduler = PhoneNumberRentalScheduler(_check_interval_hours())
    await _phone_number_rental_scheduler.start()


async def stop_phone_number_rental_scheduler() -> None:
    """Stop the process-wide phone-rental scheduler."""
    if _phone_number_rental_scheduler:
        await _phone_number_rental_scheduler.stop()
