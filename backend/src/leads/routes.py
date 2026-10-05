"""Interest-lead routes: public submission + platform-admin follow-up."""

# NOTE: no `from __future__ import annotations` here on purpose. FastAPI
# inspects these annotations through decorator wrappers whose module
# globals cannot resolve stringified models, which silently demotes body
# models to query params (and breaks /openapi.json generation).

import logging
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from opentelemetry import trace
from pydantic import BaseModel, Field
from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.leads.models import InterestLead, InterestLeadAck, InterestLeadCreate
from src.leads.service import lead_service
from src.notifications.lead_notification_outbox import (
    interest_lead_notification_outbox,
)
from src.security.rate_limiter import limiter
from src.security.turnstile import is_turnstile_configured, verify_turnstile_token

from shared.voice_agents.demo_feedback_service import demo_feedback_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

public_leads_router = APIRouter(
    prefix="/api/v1/public/leads", tags=["Public Interest Leads"]
)
admin_leads_router = APIRouter(prefix="/api/v1/leads", tags=["Interest Leads"])


class LeadStatusUpdate(BaseModel):
    """Follow-up status transition for one lead."""

    status: str = Field(
        ...,
        pattern="^(new|contacted|invited|converted|dropped)$",
        description="Target follow-up status",
    )


class DemoFeedbackSummaryItem(BaseModel):
    """Aggregate rating counts for one demo slug."""

    demo_slug: str
    count: int
    average_rating: Optional[float] = None


class DemoFeedbackRecordItem(BaseModel):
    """One stored visitor rating, safe for platform admins."""

    id: str
    session_id: str
    agent_id: str
    organization_id: str
    demo_slug: str
    rating: int
    created_at: str


class DemoFeedbackOverview(BaseModel):
    """Per-demo aggregates plus the newest ratings."""

    summary: list[DemoFeedbackSummaryItem]
    recent: list[DemoFeedbackRecordItem]


@public_leads_router.post(
    "",
    response_model=InterestLeadAck,
    responses={
        429: {"description": "Too many requests"},
        500: {"description": "Could not record the request"},
    },
)
@limiter.limit("5/minute")
@tracer.start_as_current_span("leads.routes.submit_lead")
async def submit_interest_lead(
    request: Request,
    body: InterestLeadCreate,
    background_tasks: BackgroundTasks = None,
) -> InterestLeadAck:
    """Record visitor interest (no auth required).

    Always returns the same envelope so submitters cannot probe which
    emails already exist. Failures return 500 with a safe message and
    full context in server logs.
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("lead.source", body.source)
    if body.demo_slug:
        current_span.set_attribute("lead.demo_slug", body.demo_slug)

    if is_turnstile_configured():
        client_ip = request.client.host if request.client else None
        verified = await verify_turnstile_token(body.captcha_token, client_ip)
        if not verified:
            current_span.set_attribute("error.type", "invalid_captcha")
            current_span.set_status(
                trace.Status(trace.StatusCode.ERROR, "invalid_captcha")
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha verification failed. Please try again.",
            )

    lead, error = await lead_service.submit_lead(body)
    if error:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    if lead is not None:
        if background_tasks is not None:
            background_tasks.add_task(
                interest_lead_notification_outbox.process_pending,
                lead_id=lead.id,
                limit=1,
            )
        else:
            # The database trigger has already persisted the outbox row with
            # the lead; direct callers may attempt immediate delivery as well.
            try:
                await interest_lead_notification_outbox.process_pending(
                    lead_id=lead.id,
                    limit=1,
                )
            except Exception:
                logger.exception(
                    "Interest notification dispatch failed for persisted lead %s",
                    lead.id,
                )
        current_span.set_attribute("lead.notification_outbox_scheduled", True)
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return InterestLeadAck(received=True)


@admin_leads_router.get(
    "",
    response_model=list[InterestLead],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Platform admin only"},
    },
)
@tracer.start_as_current_span("leads.routes.list_leads")
async def list_interest_leads(
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        pattern="^(new|contacted|invited|converted|dropped)$",
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[InterestLead]:
    """List interest leads newest-first (platform admins only)."""
    del request
    _user_id, profile = user_data
    assert_platform_role(profile, "platform_admin")
    leads, error = await lead_service.list_leads(status=status_filter, limit=limit)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return leads


@admin_leads_router.patch(
    "/{lead_id}",
    response_model=InterestLead,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Platform admin only"},
        404: {"description": "Lead not found"},
    },
)
@tracer.start_as_current_span("leads.routes.mark_lead_status")
async def mark_interest_lead_status(
    lead_id: UUID,
    body: LeadStatusUpdate,
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> InterestLead:
    """Advance one lead's follow-up status (platform admins only)."""
    del request
    _user_id, profile = user_data
    assert_platform_role(profile, "platform_admin")
    lead, error = await lead_service.mark_status(lead_id, body.status)
    if error:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if error == "Lead not found."
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=error,
        )
    assert lead is not None
    return lead


@admin_leads_router.get(
    "/demo-feedback",
    response_model=DemoFeedbackOverview,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Platform admin only"},
    },
)
@tracer.start_as_current_span("leads.routes.list_demo_feedback")
async def list_demo_feedback(
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> DemoFeedbackOverview:
    """Aggregate demo ratings plus the newest rows (platform admins only)."""
    del request
    _user_id, profile = user_data
    assert_platform_role(profile, "platform_admin")
    summaries = await demo_feedback_service.summary()
    records = await demo_feedback_service.recent(limit=limit)
    return DemoFeedbackOverview(
        summary=[
            DemoFeedbackSummaryItem(
                demo_slug=item.demo_slug,
                count=item.count,
                average_rating=item.average_rating,
            )
            for item in summaries
        ],
        recent=[
            DemoFeedbackRecordItem(
                id=record.id,
                session_id=record.session_id,
                agent_id=record.agent_id,
                organization_id=record.organization_id,
                demo_slug=record.demo_slug,
                rating=record.rating,
                created_at=record.created_at,
            )
            for record in records
        ],
    )
