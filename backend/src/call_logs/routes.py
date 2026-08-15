"""API routes for call logs and analytics."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from .models import CallAnalytics, CallLogsResponse
from .service import call_log_service

logger = logging.getLogger(__name__)
call_logs_router = APIRouter(prefix="/api/v1/calls", tags=["Call Logs"])


def _check_org_access(user_profile: UserProfile, organization_id: UUID) -> None:
    """Raise 403 if user lacks access to the organization."""
    if user_profile.has_role("platform_admin"):
        return
    if not user_profile.has_role("org_admin", str(organization_id)) and not user_profile.has_role(
        "regular_user", str(organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization",
        )


@call_logs_router.get("/organization/{org_id}", response_model=CallLogsResponse)
async def list_call_logs(
    org_id: UUID,
    agent_id: Optional[UUID] = Query(None, description="Filter by agent"),
    call_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter start date (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Filter end date (ISO 8601)"),
    recording_only: bool = Query(
        False, description="Return only calls with completed recordings"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return paginated call logs for an organization with optional filters."""
    _, user_profile = user_data
    _check_org_access(user_profile, org_id)

    result, error = await call_log_service.list_call_logs(
        organization_id=org_id,
        agent_id=agent_id,
        status=call_status,
        date_from=date_from,
        date_to=date_to,
        recording_only=recording_only,
        page=page,
        page_size=page_size,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error)
    return result


@call_logs_router.get("/organization/{org_id}/analytics", response_model=CallAnalytics)
async def get_call_analytics(
    org_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return call analytics (totals, avg duration, by-agent/hour/status) for an organization."""
    _, user_profile = user_data
    _check_org_access(user_profile, org_id)

    result, error = await call_log_service.get_analytics(organization_id=org_id)
    if error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error)
    return result
