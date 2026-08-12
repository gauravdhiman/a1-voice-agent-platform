"""Background scheduler for monthly phone-number rental billing."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from shared.config import settings

from .service import phone_number_service

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
                await phone_number_service.process_due_rentals()
            except Exception:
                logger.exception("Phone-rental scheduler iteration failed")
            try:
                await asyncio.sleep(self.check_interval_hours * 3600)
            except asyncio.CancelledError:
                break


_phone_number_rental_scheduler: Optional[PhoneNumberRentalScheduler] = None


def _check_interval_hours() -> float:
    """Read the optional scheduler interval from application settings."""
    raw = getattr(settings, "phone_number_billing_check_interval_hours", None)
    return float(raw) if raw is not None else float(DEFAULT_CHECK_INTERVAL_HOURS)


async def start_phone_number_rental_scheduler() -> None:
    """Start the process-wide phone-rental scheduler."""
    global _phone_number_rental_scheduler
    _phone_number_rental_scheduler = PhoneNumberRentalScheduler(_check_interval_hours())
    await _phone_number_rental_scheduler.start()


async def stop_phone_number_rental_scheduler() -> None:
    """Stop the process-wide phone-rental scheduler."""
    global _phone_number_rental_scheduler
    if _phone_number_rental_scheduler:
        await _phone_number_rental_scheduler.stop()
