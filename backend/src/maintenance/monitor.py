"""Evaluate persisted worker state for external availability monitors."""

import math
from datetime import datetime, timedelta, timezone
from typing import Mapping


def _timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def unhealthy_jobs(
    expected: Mapping[str, float],
    rows: list[dict],
    *,
    now: datetime | None = None,
    max_run_seconds: int = 900,
) -> list[str]:
    """Return jobs whose claim, completion, or timestamps require attention.

    Missing records, failed jobs, stale completions, and runs older than the
    maximum are unhealthy. A first run is allowed while it is still in flight.
    """
    now = now or datetime.now(timezone.utc)
    by_name = {row.get("job"): row for row in rows}
    unhealthy = []
    for job, interval in expected.items():
        if not math.isfinite(interval) or interval < 0:
            unhealthy.append(job)
            continue
        row = by_name.get(job)
        if not row or row.get("state") not in {"idle", "running"}:
            unhealthy.append(job)
            continue
        succeeded = _timestamp(row.get("last_succeeded_at"))
        failed = _timestamp(row.get("last_failed_at"))
        if row["state"] == "running":
            started = _timestamp(row.get("started_at"))
            if (
                started is None
                or started > now
                or now - started > timedelta(seconds=max_run_seconds)
            ):
                unhealthy.append(job)
                continue
            if succeeded is None:
                continue
        if succeeded is None or succeeded > now:
            unhealthy.append(job)
            continue
        if failed and failed > succeeded:
            unhealthy.append(job)
            continue
        if now - succeeded > timedelta(seconds=max(300, interval * 2 + 60)):
            unhealthy.append(job)
    for row in rows:
        if row.get("job") != "phone-guard":
            continue
        started = _timestamp(row.get("started_at"))
        if (
            row.get("state") == "failed"
            or started is None
            or started > now
            or now - started > timedelta(seconds=max_run_seconds)
        ):
            if "phone-guard" not in unhealthy:
                unhealthy.append("phone-guard")
    return unhealthy
