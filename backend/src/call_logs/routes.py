"""API routes for call logs and analytics."""

import logging
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    if not user_profile.has_role(
        "org_admin", str(organization_id)
    ) and not user_profile.has_role("regular_user", str(organization_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this organization",
        )


@call_logs_router.get("/organization/{org_id}", response_model=CallLogsResponse)
async def list_call_logs(
    org_id: UUID,
    agent_id: Optional[UUID] = Query(None, description="Filter by agent"),
    call_status: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
    source_type: Optional[str] = Query(None, description="Filter by call source"),
    date_from: Optional[datetime] = Query(
        None, description="Filter start date (ISO 8601)"
    ),
    date_to: Optional[datetime] = Query(None, description="Filter end date (ISO 8601)"),
    date_to_exclusive: Optional[datetime] = Query(
        None, description="Exclusive filter end date (ISO 8601)"
    ),
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
    if date_to is not None and date_to_exclusive is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Specify either date_to or date_to_exclusive, not both",
        )

    result, error = await call_log_service.list_call_logs(
        organization_id=org_id,
        agent_id=agent_id,
        status=call_status,
        source_type=source_type,
        date_from=date_from,
        date_to=date_to,
        date_to_exclusive=date_to_exclusive,
        recording_only=recording_only,
        page=page,
        page_size=page_size,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return result


@call_logs_router.get("/organization/{org_id}/analytics", response_model=CallAnalytics)
async def get_call_analytics(
    org_id: UUID,
    period: Optional[Literal["today", "yesterday"]] = Query(None),
    period_days: Optional[int] = Query(None, ge=7, le=30),
    call_status: Optional[str] = Query(None, alias="status", max_length=30),
    timezone_name: str = Query("UTC", min_length=1, max_length=64),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return call analytics (totals, avg duration, by-agent/hour/status) for an organization."""
    _, user_profile = user_data
    _check_org_access(user_profile, org_id)

    if period is not None and period_days is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Specify either a calendar period or period_days, not both",
        )
    if period_days is not None and period_days not in {7, 15, 30}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reporting period must be 7, 15, or 30 days",
        )

    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=422, detail="Invalid organization timezone"
        ) from exc

    result, error = await call_log_service.get_analytics(
        organization_id=org_id,
        period_days=period_days or 30,
        calendar_period=period,
        call_status=call_status,
        timezone_name=timezone_name,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return result


@call_logs_router.get("/platform/analytics", response_model=CallAnalytics)
async def get_platform_call_analytics(
    period: Optional[Literal["today", "yesterday"]] = Query(None),
    period_days: Optional[int] = Query(None, ge=7, le=30),
    call_status: Optional[str] = Query(None, alias="status", max_length=30),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return filtered cross-organization call aggregates for platform admins."""
    _, user_profile = user_data
    if not user_profile.has_role("platform_admin"):
        raise HTTPException(status_code=403, detail="Platform admin access required")
    if period is not None and period_days is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Specify either a calendar period or period_days, not both",
        )
    if period_days is not None and period_days not in {7, 15, 30}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reporting period must be 7, 15, or 30 days",
        )
    result, error = await call_log_service.get_analytics(
        organization_id=None,
        period_days=period_days or 30,
        calendar_period=period,
        call_status=call_status,
        timezone_name="UTC",
    )
    if error:
        raise HTTPException(status_code=503, detail=error)
    return result
