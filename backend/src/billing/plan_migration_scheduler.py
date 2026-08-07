"""
Background scheduler for plan-version grace-period migrations.

Runs on a configurable interval (default: daily) and auto-migrates subscribers
when grace periods expire and the publish event has ``auto_migrate_on_expiry``.

Lifecycle mirrors :mod:`src.services.token_refresh_service` — started from
``main.lifespan`` on backend startup.
"""

import asyncio
import logging
from typing import Optional

from shared.config import settings

from .plan_migration_service import plan_migration_service

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_HOURS = 24


class PlanMigrationSchedulerService:
    """Daily loop that processes expired grace-period plan migrations."""

    def __init__(self, check_interval_hours: float = DEFAULT_CHECK_INTERVAL_HOURS) -> None:
        self.check_interval_hours = check_interval_hours
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background migration check loop."""
        if self.running:
            logger.warning("Plan migration scheduler is already running")
            return
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info(
            "Plan migration scheduler started (interval=%sh)",
            self.check_interval_hours,
        )

    async def stop(self) -> None:
        """Stop the background migration check loop."""
        if not self.running:
            return
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Plan migration scheduler stopped")

    async def _run_loop(self) -> None:
        """Run migration processing on interval until cancelled."""
        interval_seconds = self.check_interval_hours * 3600
        while self.running:
            try:
                await plan_migration_service.process_due_migrations()
            except Exception as exc:
                logger.error(
                    "Plan migration scheduler iteration failed: %s",
                    exc,
                    exc_info=True,
                )
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break


_plan_migration_scheduler: Optional[PlanMigrationSchedulerService] = None


def _check_interval_hours() -> float:
    """Read scheduler interval from settings or use default."""
    raw = getattr(settings, "plan_migration_check_interval_hours", None)
    if raw is None:
        return float(DEFAULT_CHECK_INTERVAL_HOURS)
    return float(raw)


async def start_plan_migration_scheduler() -> None:
    """Start the global plan migration scheduler."""
    global _plan_migration_scheduler
    _plan_migration_scheduler = PlanMigrationSchedulerService(
        check_interval_hours=_check_interval_hours()
    )
    await _plan_migration_scheduler.start()


async def stop_plan_migration_scheduler() -> None:
    """Stop the global plan migration scheduler."""
    global _plan_migration_scheduler
    if _plan_migration_scheduler:
        await _plan_migration_scheduler.stop()
