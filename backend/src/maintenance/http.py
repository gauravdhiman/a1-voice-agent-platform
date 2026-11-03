"""HTTP adapter for a separately hosted maintenance runner.

The application is created explicitly so deployment config supplies both the
coordinator and authentication; importing this module starts no background work.
"""

import hmac
import logging
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .monitor import unhealthy_jobs
from .runner import MaintenanceRunner, UnknownJobError

logger = logging.getLogger(__name__)


class RunResponse(BaseModel):
    """Public, non-sensitive outcome of a maintenance invocation."""

    job: str
    status: str


def create_maintenance_app(
    runner: MaintenanceRunner,
    bearer_token: str,
    status_reader: Optional[Callable[[tuple[str, ...]], Awaitable[list[dict]]]] = None,
    interval_reader: Optional[Callable[[str], Awaitable[float]]] = None,
    heartbeat: Optional[Callable[[], Awaitable[None]]] = None,
) -> FastAPI:
    """Create a fail-closed worker API with a deployment-supplied secret.

    The secret must be a high-entropy, randomly generated value of at least 32
    characters. Scheduler retries must not be interpreted as new work unless
    the runner's coordinator has safely resolved the previous attempt.
    """
    if len(bearer_token) < 32 or not bearer_token.isascii():
        raise ValueError(
            "A nonempty ASCII maintenance secret of at least 32 characters is required"
        )
    if heartbeat is not None and (status_reader is None or interval_reader is None):
        raise ValueError("Heartbeat requires job status and interval readers")

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Report process liveness without exposing job or tenant data."""
        return {"status": "ok"}

    def authenticate(authorization: str, x_maintenance_key: str) -> None:
        # A dedicated header allows an infrastructure identity token in
        # Authorization when Cloud Run IAM authenticates the invocation.
        valid_header = x_maintenance_key.isascii() and hmac.compare_digest(
            x_maintenance_key, bearer_token
        )
        valid_bearer = authorization.isascii() and hmac.compare_digest(
            authorization, f"Bearer {bearer_token}"
        )
        if not (valid_header or valid_bearer):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )

    @app.post("/v1/jobs/{job}", response_model=RunResponse)
    async def run_job(
        job: str,
        authorization: str = Header(default=""),
        x_maintenance_key: str = Header(default=""),
    ) -> RunResponse:
        authenticate(authorization, x_maintenance_key)
        try:
            result = await runner.run(job)
        except UnknownJobError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job"
            )
        except Exception:
            # Avoid forwarding provider, database, or credential details.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Job unavailable",
            )
        if result.status == "already_running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Job already running"
            )
        if result.status not in {"succeeded", "not_due"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job failed"
            )
        return RunResponse(job=result.job, status=result.status)

    @app.post("/v1/tick")
    async def run_tick(
        authorization: str = Header(default=""),
        x_maintenance_key: str = Header(default=""),
    ) -> dict[str, str]:
        """Run due jobs once; a failure never prevents other jobs being attempted."""
        authenticate(authorization, x_maintenance_key)
        failed = False
        for job in runner.job_names:
            try:
                result = await runner.run(job)
                failed = failed or result.status not in {
                    "succeeded",
                    "not_due",
                    "already_running",
                }
            except Exception as exc:
                logger.error(
                    "Maintenance tick failed for %s (%s)", job, type(exc).__name__
                )
                failed = True
        if failed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="One or more jobs did not complete",
            )
        if heartbeat is not None:
            try:
                rows = await status_reader(runner.job_names)
                intervals = {
                    job: await interval_reader(job) for job in runner.job_names
                }
                if unhealthy_jobs(intervals, rows):
                    raise RuntimeError("Unhealthy maintenance state")
                await heartbeat()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Maintenance monitoring unavailable or unhealthy",
                ) from None
        return {"status": "ok"}

    @app.get("/v1/status")
    async def job_status(
        authorization: str = Header(default=""),
        x_maintenance_key: str = Header(default=""),
    ) -> dict:
        """Return authenticated job state without claim tokens or tenant data."""
        authenticate(authorization, x_maintenance_key)
        if status_reader is None:
            raise HTTPException(status_code=503, detail="Job status unavailable")
        try:
            rows = await status_reader(runner.job_names)
            intervals = (
                {job: await interval_reader(job) for job in runner.job_names}
                if interval_reader
                else None
            )
        except Exception:
            raise HTTPException(status_code=503, detail="Job status unavailable")
        fields = {
            "job",
            "state",
            "started_at",
            "finished_at",
            "last_succeeded_at",
            "last_failed_at",
            "last_reconciled_at",
        }
        response = {
            "expected_jobs": list(runner.job_names),
            "jobs": [{key: row[key] for key in fields if key in row} for row in rows],
        }
        if intervals is not None:
            unhealthy = unhealthy_jobs(intervals, rows)
            response["unhealthy_jobs"] = unhealthy
            if unhealthy:
                return JSONResponse(status_code=503, content=response)
        return response

    return app
