"""Serialize phone lifecycle API mutations with the external rental worker."""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import HTTPException, status
from src.maintenance.coordinator import PostgresRunCoordinator

from shared.config import settings, supabase_config


@asynccontextmanager
async def phone_mutation_guard(organization_id: UUID, *, force: bool = False):
    """Hold one organization's phone lifecycle claim across a mutation.

    Interrupted or unexpected failures retain ownership for reconciliation.
    The in-process deployment retains its existing behavior until cutover.
    """
    if settings.maintenance_mode != "external" and not force:
        yield
        return
    try:
        coordinator = PostgresRunCoordinator(supabase_config.service_client)
        job = f"phone-org:{organization_id}"
        claim = await coordinator.acquire(job)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Phone number operations are temporarily unavailable",
        )
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A phone number operation is already in progress. "
                "Please retry shortly."
            ),
        )
    try:
        yield
    except BaseException:
        # Do not release an operation with an unknown provider outcome.
        raise
    else:
        try:
            await coordinator.release_guard(job, claim)
        except Exception:
            raise HTTPException(
                status_code=503, detail="Phone number operation could not be confirmed"
            )
