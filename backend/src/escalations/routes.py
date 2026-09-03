"""Callback escalation routes: org-scoped list, manual log, follow-up."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from opentelemetry import trace
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.escalations.models import (
    Escalation,
    EscalationCreate,
    EscalationStatusUpdate,
)
from src.escalations.service import escalation_service
from src.security.rate_limiter import limiter

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

escalations_router = APIRouter(
    prefix="/api/v1/organizations/{org_id}/escalations",
    tags=["Callback Escalations"],
)


def _check_org_access(user_profile: UserProfile, organization_id: UUID) -> None:
    """Raise 403 unless the caller belongs to the organization."""
    if user_profile.has_role("platform_admin"):
        return
    if not user_profile.has_role(
        "org_admin", str(organization_id)
    ) and not user_profile.has_role("regular_user", str(organization_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization",
        )


def _require_org_admin(user_profile: UserProfile, organization_id: UUID) -> None:
    """Raise 403 unless the caller administers the organization."""
    if user_profile.has_role("platform_admin"):
        return
    if not user_profile.has_role("org_admin", str(organization_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin role required",
        )


@escalations_router.get("", response_model=list[Escalation])
@tracer.start_as_current_span("escalations.routes.list_escalations")
async def list_escalations(
    org_id: UUID,
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        pattern="^(new|acknowledged|resolved)$",
    ),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[Escalation]:
    """List callback escalations newest-first (organization members)."""
    del request
    _, user_profile = user_data
    _check_org_access(user_profile, org_id)
    escalations, error = await escalation_service.list_escalations(
        org_id, status=status_filter, limit=limit
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return escalations


@escalations_router.post("", response_model=Escalation, status_code=201)
@limiter.limit("20/minute")
@tracer.start_as_current_span("escalations.routes.create_escalation")
async def create_escalation(
    org_id: UUID,
    body: EscalationCreate,
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Escalation:
    """Manually log one callback request (organization admins)."""
    _, user_profile = user_data
    _require_org_admin(user_profile, org_id)
    escalation, error = await escalation_service.create_escalation(org_id, body)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    assert escalation is not None
    return escalation


@escalations_router.patch("/{escalation_id}", response_model=Escalation)
@tracer.start_as_current_span("escalations.routes.mark_escalation_status")
async def mark_escalation_status(
    org_id: UUID,
    escalation_id: UUID,
    body: EscalationStatusUpdate,
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Escalation:
    """Advance one escalation's follow-up status (organization admins)."""
    del request
    _, user_profile = user_data
    _require_org_admin(user_profile, org_id)
    escalation, error = await escalation_service.mark_status(
        org_id, escalation_id, body.status
    )
    if error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if error == "Callback request not found."
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=error,
        )
    assert escalation is not None
    return escalation
