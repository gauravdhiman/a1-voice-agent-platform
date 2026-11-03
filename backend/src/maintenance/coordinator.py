"""Postgres-backed, fail-closed maintenance run coordinator."""

import asyncio
import math
from typing import Awaitable, Callable
from uuid import uuid4

from .runner import MaintenanceNotDue


class PostgresRunCoordinator:
    """Use atomic service-role RPCs to exclude overlapping job executions.

    Claims do not automatically expire. An operator must reconcile a failed
    or interrupted run before removing its record and allowing a retry.
    """

    def __init__(
        self, client, interval_for: Callable[[str], Awaitable[float]] = None
    ) -> None:
        if client is None:
            raise ValueError("A service-role database client is required")
        self._client = client
        self._interval_for = interval_for

    async def acquire(self, job: str) -> str | None:
        """Claim the job atomically; return None when a run is held."""
        token = str(uuid4())
        interval = await self._interval_for(job) if self._interval_for else 0
        if not math.isfinite(interval) or interval < 0:
            raise ValueError("Maintenance interval must be finite and nonnegative")
        response = await asyncio.to_thread(
            lambda: self._client.rpc(
                "claim_maintenance_run",
                {"p_job": job, "p_claim": token, "p_interval_seconds": interval},
            ).execute()
        )
        if response.data == "claimed":
            return token
        if response.data == "running":
            return None
        if response.data == "blocked":
            raise RuntimeError("Maintenance job requires reconciliation")
        if response.data == "not_due":
            raise MaintenanceNotDue()
        raise RuntimeError("Unexpected maintenance claim response")

    async def complete(self, job: str, token: str, succeeded: bool) -> None:
        """Finish an owned run, retaining failed runs for reconciliation."""
        response = await asyncio.to_thread(
            lambda: self._client.rpc(
                "complete_maintenance_run",
                {"p_job": job, "p_claim": token, "p_succeeded": succeeded},
            ).execute()
        )
        if response.data is not True:
            raise RuntimeError("Maintenance ownership was not confirmed")

    async def retry(self, job: str, token: str) -> None:
        """Release an explicitly retry-safe failure without recording success."""
        response = await asyncio.to_thread(
            lambda: self._client.rpc(
                "retry_maintenance_run", {"p_job": job, "p_claim": token}
            ).execute()
        )
        if response.data is not True:
            raise RuntimeError("Maintenance ownership was not confirmed")

    async def status(self, jobs: tuple[str, ...]) -> list[dict]:
        """Read non-sensitive job state and timestamps for monitoring."""

        def load():
            response = (
                self._client.table("maintenance_runs")
                .select(
                    "job,state,started_at,finished_at,last_succeeded_at,"
                    "last_failed_at,last_reconciled_at"
                )
                .in_("job", list(jobs))
                .execute()
            )
            if not isinstance(response.data, list):
                raise RuntimeError("Unexpected maintenance status response")
            rows = response.data
            for state in ("failed", "running"):
                guards = (
                    self._client.table("maintenance_runs")
                    .select("state,started_at")
                    .like("job", "phone-org:%")
                    .eq("state", state)
                    .order("started_at")
                    .limit(1)
                    .execute()
                )
                if not isinstance(guards.data, list):
                    raise RuntimeError("Unexpected phone guard status response")
                if guards.data:
                    rows.append({"job": "phone-guard", **guards.data[0]})
            return rows

        return await asyncio.to_thread(load)

    async def release_guard(self, job: str, token: str) -> None:
        """Release an API-side guard without changing scheduled-run timestamps."""
        response = await asyncio.to_thread(
            lambda: self._client.rpc(
                "release_maintenance_guard", {"p_job": job, "p_claim": token}
            ).execute()
        )
        if response.data is not True:
            raise RuntimeError("Maintenance ownership was not confirmed")
