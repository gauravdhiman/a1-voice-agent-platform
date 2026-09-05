"""Public demo-agent page routes.

Unauthenticated visitors browse a demo agent at ``/demo/{demo_slug}``
and start voice calls without logging in. Only agents marked
``is_demo = true`` with a unique ``demo_slug`` are exposed here.
Demo agents bypass credit and concurrency checks so showcase calls
never block on billing, but can be bounded by platform-admin-configured demo
call budgets.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from src.security.rate_limiter import limiter
from src.voice_agents.public_voice_messages import get_public_voice_session_error

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    assert_voice_session_allowed,
    is_demo_agent,
    reserve_demo_call_if_needed,
)
from shared.voice_agents.demo_outcome_service import (
    create_demo_outcome_token,
    demo_outcome_service,
    verify_demo_outcome_token,
)
from shared.voice_agents.models import normalize_demo_public_result_url
from shared.voice_agents.public_page_service import public_page_service
from shared.voice_agents.service import voice_agent_service

logger = logging.getLogger(__name__)
_PRIMARY_DEMO_ACTION_TYPES = {"lead_capture", "appointment_booking"}
# Public demos remain free to use, but token issuance is bounded per source so
# one visitor cannot turn an unlimited demo into an unattended spend loop.
DEMO_CALL_TOKEN_RATE_LIMIT = "5/hour"
DEMO_CALL_TOKEN_RATE_LIMIT_SCOPE = "public-demo-call-token"

demo_public_router = APIRouter(
    prefix="/api/v1/public/demo", tags=["Public Demo Agents"]
)


class DemoAgentPublicResponse(BaseModel):
    """Safe demo-agent metadata exposed on the dedicated public page."""

    id: UUID
    name: str
    demo_slug: str
    persona: str | None = None
    mission: str | None = None
    tone: str | None = None
    public_description: str | None = None
    organization_id: UUID
    organization_name: str | None = None
    demo_calls_remaining: int = -1
    demo_max_call_duration_seconds: int = -1


class DemoCallTokenResponse(BaseModel):
    """Pipecat voice session credentials for a demo-agent visitor call."""

    token: str
    wsUrl: str
    sessionId: str
    receiptToken: str
    demo_calls_remaining: int | None = None
    demo_max_call_duration_seconds: int | None = None


class DemoOutcomeActionResponse(BaseModel):
    """One visitor-visible side effect from a demo workflow."""

    id: UUID
    action_type: Literal["lead_capture", "appointment_booking", "email_delivery"]
    provider: str
    status: Literal["succeeded", "failed", "pending"]
    error_code: str | None = None
    captured_fields: dict[str, Any]
    provider_result: dict[str, Any]
    public_result_url: str | None = None
    created_at: datetime
    expires_at: datetime


class DemoOutcomeResponse(BaseModel):
    """Signed-session receipt shown after a visitor ends a demo call."""

    demo_slug: str
    agent_name: str
    organization_name: str | None = None
    status: Literal["completed", "needs_attention", "no_action"]
    actions: list[DemoOutcomeActionResponse]
    expires_at: datetime | None = None


@demo_public_router.get("/{demo_slug}", response_model=DemoAgentPublicResponse)
async def get_demo_agent_public(demo_slug: str) -> DemoAgentPublicResponse:
    """Return public metadata for a demo agent by its unique slug."""
    normalized = demo_slug.strip().lower()
    agent, error = await voice_agent_service.get_demo_agent_by_slug(normalized)
    if error or not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demo agent not found"
        )
    # Resolve organization name for display (best-effort, not required for auth)
    org_name = None
    try:
        from shared.organization.service import BaseOrganizationService

        svc = BaseOrganizationService()
        org, _ = await svc.get_organization_by_id(agent.organization_id)
        if org:
            org_name = org.name
    except Exception:
        pass
    return DemoAgentPublicResponse(
        id=agent.id,
        name=agent.name,
        demo_slug=agent.demo_slug or normalized,
        persona=agent.persona,
        mission=agent.mission,
        tone=agent.tone,
        public_description=getattr(agent, "public_description", None),
        organization_id=agent.organization_id,
        organization_name=org_name,
        demo_calls_remaining=getattr(agent, "demo_calls_remaining", -1),
        demo_max_call_duration_seconds=getattr(
            agent, "demo_max_call_duration_seconds", -1
        ),
    )


@demo_public_router.get("/{demo_slug}/outcome", response_model=DemoOutcomeResponse)
async def get_demo_outcome_public(
    demo_slug: str,
    response: Response,
    token: str = Query(..., min_length=20, max_length=4096),
) -> DemoOutcomeResponse:
    """Return only the verified visitor's non-expired demo outcome receipt."""
    normalized = demo_slug.strip().lower()
    claims = verify_demo_outcome_token(token)
    if not claims or claims.demo_slug != normalized:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demo outcome not found"
        )

    agent, error = await voice_agent_service.get_demo_agent_by_slug(normalized)
    if error or not agent or str(agent.id) != claims.agent_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demo outcome not found"
        )

    try:
        rows = await demo_outcome_service.list_for_session(
            session_id=claims.session_id,
            agent_id=claims.agent_id,
            demo_slug=normalized,
        )
    except Exception:
        logger.exception("Unable to load demo outcome receipt")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo outcome is temporarily unavailable",
        ) from None

    try:
        configured_result_url = normalize_demo_public_result_url(
            getattr(agent, "demo_public_result_url", None)
        )
    except ValueError:
        # Fail closed if a historical or manually edited row contains an
        # invalid URL; the receipt remains usable without the optional CTA.
        configured_result_url = None

    actions = []
    for row in rows:
        action = DemoOutcomeActionResponse(**row)
        if (
            action.action_type in _PRIMARY_DEMO_ACTION_TYPES
            and action.status == "succeeded"
            and configured_result_url
        ):
            action = action.model_copy(
                update={"public_result_url": configured_result_url}
            )
        actions.append(action)
    if actions and all(action.status == "succeeded" for action in actions):
        outcome_status = "completed"
    elif any(action.status in {"failed", "pending"} for action in actions):
        outcome_status = "needs_attention"
    else:
        outcome_status = "no_action"
    expires_at = max((action.expires_at for action in actions), default=None)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    org_name = None
    try:
        from shared.organization.service import BaseOrganizationService

        org, _ = await BaseOrganizationService().get_organization_by_id(
            agent.organization_id
        )
        if org:
            org_name = org.name
    except Exception:
        pass
    return DemoOutcomeResponse(
        demo_slug=normalized,
        agent_name=agent.name,
        organization_name=org_name,
        status=outcome_status,
        actions=actions,
        expires_at=expires_at,
    )


@demo_public_router.post(
    "/{demo_slug}/call-token", response_model=DemoCallTokenResponse
)
@limiter.shared_limit(
    DEMO_CALL_TOKEN_RATE_LIMIT,
    scope=DEMO_CALL_TOKEN_RATE_LIMIT_SCOPE,
)
async def generate_demo_call_token(
    demo_slug: str,
    request: Request,
    source_url: Optional[str] = Query(
        None,
        max_length=2048,
        description="Page URL that initiated the demo call",
    ),
) -> DemoCallTokenResponse:
    """Generate a Pipecat voice session token for a demo-agent visitor call.

    Demo agents bypass the normal credit/concurrency gate, while their
    configured demo call budget is reserved atomically before a token is issued.
    Token issuance is limited to five attempts per source IP per hour across
    all public demo slugs. Non-demo slugs are treated as not found.
    """
    normalized = demo_slug.strip().lower()
    agent, error = await voice_agent_service.get_demo_agent_by_slug(normalized)
    if error or not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demo agent not found"
        )

    reservation = None
    try:
        reservation = await reserve_demo_call_if_needed(agent)
        await assert_voice_session_allowed(
            agent.organization_id,
            agent_is_demo=is_demo_agent(agent),
        )
    except VoiceSessionEntitlementError as exc:
        public_code, public_message = get_public_voice_session_error(exc.code)
        logger.info(
            "Demo voice session denied demo_slug=%s code=%s", demo_slug, exc.code
        )
        raise HTTPException(
            status_code=(
                status.HTTP_429_TOO_MANY_REQUESTS
                if exc.code == "DEMO_CALL_LIMIT_REACHED"
                else {
                    "INSUFFICIENT_CREDITS": status.HTTP_402_PAYMENT_REQUIRED,
                    "MAX_CONCURRENT_CALLS": status.HTTP_409_CONFLICT,
                }.get(exc.code, status.HTTP_503_SERVICE_UNAVAILABLE)
            ),
            detail={"code": public_code, "message": public_message},
        ) from exc

    token, ws_url, session_id = public_page_service.generate_call_token(
        agent_id=str(agent.id),
        demo_reservation=reservation,
        source_type="web_demo",
        source_url=source_url,
    )
    if not token or not ws_url or not session_id:
        logger.error(
            "Failed to generate demo call token demo_slug=%s agent_id=%s",
            demo_slug,
            agent.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate call token",
        )

    try:
        receipt_token = create_demo_outcome_token(
            session_id=session_id,
            agent_id=str(agent.id),
            demo_slug=normalized,
        )
    except ValueError as exc:
        logger.error("Failed to generate demo outcome token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate demo outcome token",
        ) from exc

    logger.info(
        "Demo call token issued demo_slug=%s agent_id=%s session_id=%s",
        demo_slug,
        agent.id,
        session_id,
    )
    return DemoCallTokenResponse(
        token=token,
        wsUrl=ws_url,
        sessionId=session_id,
        receiptToken=receipt_token,
        demo_calls_remaining=(reservation.calls_remaining if reservation else None),
        demo_max_call_duration_seconds=(
            reservation.max_call_duration_seconds if reservation else None
        ),
    )
