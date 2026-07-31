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

from shared.organization.public_page_security import verify_public_page_passphrase
from shared.voice_agents.public_page_service import (
    PublicPageAccessError,
    public_page_service,
)
from shared.voice_agents.service import voice_agent_service
from src.organization.service import organization_service

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
    """LiveKit credentials for a public-page voice call."""

    livekit_token: str
    server_url: str
    room_name: str


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

    agents, error = await voice_agent_service.get_public_page_agents(UUID(str(org["id"])))
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
    """Generate a LiveKit token for a public-page visitor call."""
    org = await _load_public_org(slug)
    _require_access_token(org, slug, x_public_access_token)

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error or not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if str(agent.organization_id) != str(org["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.is_active or not agent.is_published_on_public_page:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not available on the public page",
        )

    livekit_token, server_url, room_name = public_page_service.generate_call_token(
        agent_id=str(agent_id)
    )
    if not livekit_token or not server_url or not room_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate call token",
        )

    return PublicCallTokenResponse(
        livekit_token=livekit_token,
        server_url=server_url,
        room_name=room_name,
    )
