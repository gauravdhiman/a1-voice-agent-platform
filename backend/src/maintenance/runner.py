"""Bounded maintenance execution with explicit failures and coordination.

The caller supplies the scheduler, job implementations and coordination store.
This module has no cloud-provider or HTTP dependencies.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping, Protocol

logger = logging.getLogger(__name__)


class UnknownJobError(ValueError):
    """The caller requested a job not registered in this worker."""


class RetryableMaintenanceError(RuntimeError):
    """A job proved that a subsequent run can safely retry its work."""


class MaintenanceNotDue(Exception):
    """A job has completed recently enough to skip this scheduler tick."""


class RunCoordinator(Protocol):
    """Coordinate runs across processes without automatic unsafe takeover."""

    async def acquire(self, job: str) -> str | None:
        """Return an ownership token, or None if the job is already held."""
        ...

    async def complete(self, job: str, token: str, succeeded: bool) -> None:
        """Record an outcome, retaining failed work until it is safe to retry.

        Implementations must reject stale tokens and must not automatically
        transfer ownership of interrupted or failed provider mutations.
        """
        ...

    async def retry(self, job: str, token: str) -> None:
        """Record a known-safe failure and allow a subsequent scheduled run."""
        ...


@dataclass(frozen=True)
class JobResult:
    """Outcome of a single requested maintenance job."""

    job: str
    status: str


class MaintenanceRunner:
    """Run named maintenance jobs while excluding concurrent executions."""

    def __init__(
        self,
        jobs: Mapping[str, Callable[[], Awaitable[None]]],
        coordinator: RunCoordinator,
    ) -> None:
        self._jobs = dict(jobs)
        self._coordinator = coordinator

    @property
    def job_names(self) -> tuple[str, ...]:
        """Return the registered, fixed list of job names."""
        return tuple(self._jobs)

    async def run(self, job: str) -> JobResult:
        """Run one known job, returning success, failure, or already-running.

        A failed coordination operation propagates rather than running unlocked.
        Cancellation is propagated and does not mark a potentially interrupted
        operation complete; the coordinator must support safe recovery.
        """
        operation = self._jobs.get(job)
        if operation is None:
            raise UnknownJobError("Unknown maintenance job")
        try:
            token = await self._coordinator.acquire(job)
        except MaintenanceNotDue:
            return JobResult(job, "not_due")
        if token is None:
            return JobResult(job, "already_running")
        try:
            await operation()
        except asyncio.CancelledError:
            raise
        except RetryableMaintenanceError:
            # Only a job with an explicit idempotency/reconciliation guarantee
            # may signal this classification. The scheduler may retry it.
            await self._coordinator.retry(job, token)
            return JobResult(job, "failed")
        except Exception as exc:
            # Provider exceptions may include credentials or customer data.
            logger.error("Maintenance job %s failed (%s)", job, type(exc).__name__)
            await self._coordinator.complete(job, token, False)
            return JobResult(job, "failed")
        await self._coordinator.complete(job, token, True)
        return JobResult(job, "succeeded")
