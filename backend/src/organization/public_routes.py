"""Unauthenticated public organization page API routes.

Visitors browse published agents at ``/o/{slug}`` and start voice calls without
logging in. Optional passphrase protection is configured by org admins.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from src.organization.service import organization_service
from src.voice_agents.public_voice_messages import get_public_voice_session_error

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    assert_voice_session_allowed,
    is_demo_agent,
    reserve_demo_call_if_needed,
)
from shared.organization.public_page_security import verify_public_page_passphrase
from shared.voice_agents.public_page_service import (
    PublicPageAccessError,
    public_page_service,
)
from shared.voice_agents.service import voice_agent_service

logger = logging.getLogger(__name__)

public_org_router = APIRouter(prefix="/api/v1/public/orgs", tags=["Public Org Page"])


class PublicOrgSummaryResponse(BaseModel):
    """Safe org metadata for the public showcase page."""

    id: UUID
    name: str
    description: Optional[str] = None
    slug: str
    passphrase_required: bool


class PublicAgentSummary(BaseModel):
    """Safe agent metadata exposed on the public org page."""

    id: UUID
    name: str
    persona: Optional[str] = None
    mission: Optional[str] = None
    is_demo: bool = False
    demo_calls_remaining: Optional[int] = None
    demo_max_call_duration_seconds: Optional[int] = None


class PublicOrgAgentsResponse(BaseModel):
    """Published agents available for visitor calls."""

    agents: list[PublicAgentSummary]


class PublicAccessRequest(BaseModel):
    """Passphrase submission for gated public pages."""

    passphrase: str = Field(..., min_length=1, max_length=200)


class PublicAccessResponse(BaseModel):
    """Short-lived access token for gated public pages."""

    access_token: str


class PublicCallTokenResponse(BaseModel):
    """Pipecat voice session credentials for a public-page visitor call."""

    token: str
    wsUrl: str
    sessionId: str
    demo_calls_remaining: Optional[int] = None
    demo_max_call_duration_seconds: Optional[int] = None


async def _load_public_org(url_slug: str) -> dict:
    response = (
        organization_service.supabase.table("organizations")
        .select(
            "id,name,description,slug,is_active,public_page_enabled,"
            "public_page_passphrase_enabled,public_page_passphrase_hash"
        )
        .eq("slug", url_slug)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    org = response.data[0]
    if not org.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    if not org.get("public_page_enabled"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public page is not available",
        )
    return org


def _require_access_token(
    org: dict,
    slug: str,
    access_token: Optional[str],
) -> None:
    if not org.get("public_page_passphrase_enabled"):
        return
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passphrase required",
        )
    try:
        public_page_service.validate_access_token(
            access_token,
            organization_id=str(org["id"]),
            slug=slug,
        )
    except PublicPageAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@public_org_router.get("/{slug}", response_model=PublicOrgSummaryResponse)
async def get_public_org_summary(slug: str) -> PublicOrgSummaryResponse:
    """Return public org metadata and whether a passphrase is required."""
    org = await _load_public_org(slug)
    return PublicOrgSummaryResponse(
        id=org["id"],
        name=org["name"],
        description=org.get("description"),
        slug=org["slug"],
        passphrase_required=bool(org.get("public_page_passphrase_enabled")),
    )


@public_org_router.post("/{slug}/access", response_model=PublicAccessResponse)
async def verify_public_org_access(
    slug: str,
    body: PublicAccessRequest,
) -> PublicAccessResponse:
    """Verify the org passphrase and return a short-lived access token."""
    org = await _load_public_org(slug)
    if not org.get("public_page_passphrase_enabled"):
        token = public_page_service.generate_access_token(
            organization_id=str(org["id"]),
            slug=slug,
        )
        return PublicAccessResponse(access_token=token)

    stored_hash = org.get("public_page_passphrase_hash")
    if not verify_public_page_passphrase(body.passphrase, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect passphrase",
        )

    token = public_page_service.generate_access_token(
        organization_id=str(org["id"]),
        slug=slug,
    )
    return PublicAccessResponse(access_token=token)


@public_org_router.get("/{slug}/agents", response_model=PublicOrgAgentsResponse)
async def list_public_org_agents(
    slug: str,
    x_public_access_token: Optional[str] = Header(default=None),
) -> PublicOrgAgentsResponse:
    """List agents published on the organization's public page."""
    org = await _load_public_org(slug)
    _require_access_token(org, slug, x_public_access_token)

    agents, error = await voice_agent_service.get_public_page_agents(
        UUID(str(org["id"]))
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error,
        )

    return PublicOrgAgentsResponse(
        agents=[
            PublicAgentSummary(
                id=agent.id,
                name=agent.name,
                persona=agent.persona,
                mission=agent.mission,
                is_demo=is_demo_agent(agent),
                demo_calls_remaining=(
                    getattr(agent, "demo_calls_remaining", None)
                    if is_demo_agent(agent)
                    else None
                ),
                demo_max_call_duration_seconds=(
                    getattr(agent, "demo_max_call_duration_seconds", None)
                    if is_demo_agent(agent)
                    else None
                ),
            )
            for agent in agents
        ]
    )


@public_org_router.post(
    "/{slug}/agents/{agent_id}/token",
    response_model=PublicCallTokenResponse,
)
async def generate_public_call_token(
    slug: str,
    agent_id: UUID,
    x_public_access_token: Optional[str] = Header(default=None),
) -> PublicCallTokenResponse:
    """Generate a Pipecat voice session token for a public-page visitor call."""
    org = await _load_public_org(slug)
    _require_access_token(org, slug, x_public_access_token)

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error or not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    if str(agent.organization_id) != str(org["id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    if not agent.is_active or not agent.is_published_on_public_page:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not available on the public page",
        )

    reservation = None
    try:
        reservation = await reserve_demo_call_if_needed(agent)
        await assert_voice_session_allowed(
            agent.organization_id, agent_is_demo=is_demo_agent(agent)
        )
    except VoiceSessionEntitlementError as exc:
        public_code, public_message = get_public_voice_session_error(exc.code)
        logger.info(
            "Public page voice session denied agent_id=%s code=%s",
            agent_id,
            exc.code,
        )
        raise HTTPException(
            status_code=(
                status.HTTP_429_TOO_MANY_REQUESTS
                if exc.code == "DEMO_CALL_LIMIT_REACHED"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail={"code": public_code, "message": public_message},
        ) from exc

    voice_token, ws_url, session_id = public_page_service.generate_call_token(
        agent_id=str(agent_id), demo_reservation=reservation
    )
    if not voice_token or not ws_url or not session_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate call token",
        )

    return PublicCallTokenResponse(
        token=voice_token,
        wsUrl=ws_url,
        sessionId=session_id,
        demo_calls_remaining=(reservation.calls_remaining if reservation else None),
        demo_max_call_duration_seconds=(
            reservation.max_call_duration_seconds if reservation else None
        ),
    )
