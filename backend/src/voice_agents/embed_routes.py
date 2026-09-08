"""
Public embed API routes for external website integration.

These endpoints are designed to be called from external websites
and do not require authentication. They use embed tokens for
security and rate limiting.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from src.voice_agents.public_voice_messages import get_public_voice_session_error

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    assert_voice_session_allowed,
    is_demo_agent,
    reserve_demo_call_if_needed,
)
from shared.voice_agents.embed_service import embed_service
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.source_metadata import normalize_domain

logger = logging.getLogger(__name__)

# Create router without auth dependency
embed_router = APIRouter(prefix="/api/v1/embed", tags=["Embed"])


def _set_embed_cors_headers(response: Response, request: Request) -> None:
    """Allow the requesting page to read a successful public embed response."""
    origin = request.headers.get("origin")
    if not origin:
        return
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "content-type"
    response.headers["Vary"] = "Origin"


class PublicEmbedTokenResponse(BaseModel):
    """Response model for public embed token generation."""

    token: str
    wsUrl: str
    sessionId: str
    demo_calls_remaining: Optional[int] = None
    demo_max_call_duration_seconds: Optional[int] = None


class AgentInfoResponse(BaseModel):
    """Response model for agent information."""

    id: UUID
    name: str
    is_active: bool
    is_demo: bool = False
    demo_calls_remaining: Optional[int] = None
    demo_max_call_duration_seconds: Optional[int] = None


@embed_router.get("/agent/{agent_id}/info", response_model=AgentInfoResponse)
async def get_agent_info(
    agent_id: UUID,
    request: Request,
):
    """Get public information about an agent.

    This endpoint returns basic agent information for embed purposes.
    It validates domain restrictions if configured.
    """
    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Check if agent is active
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active",
        )

    # Get embed config for domain validation
    try:
        config_response = (
            voice_agent_service.supabase.table("agent_embed_configs")
            .select("*")
            .eq("agent_id", str(agent_id))
            .execute()
        )

        if not config_response.data or len(config_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embed configuration not found",
            )

        embed_config = config_response.data[0]

        if not embed_config.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Embed is not active",
            )

        # Validate domain if restrictions are set
        allowed_domains = embed_config.get("allowed_domains")
        if allowed_domains:
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            request_domain = origin or referer or ""

            if not embed_service.validate_domain(allowed_domains, request_domain):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Domain not authorized",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching embed config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch embed configuration",
        )

    return AgentInfoResponse(
        id=agent.id,
        name=agent.name,
        is_active=agent.is_active,
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


@embed_router.post("/agent/{agent_id}/token", response_model=PublicEmbedTokenResponse)
async def generate_public_embed_token(
    agent_id: UUID,
    request: Request,
    response: Response,
    source_url: Optional[str] = Query(
        None,
        max_length=2048,
        description="Page URL that initiated the embedded call",
    ),
):
    """Generate a Pipecat voice session token for embed calls.

    This endpoint is called from the embeddable call button on external websites.
    It validates domain restrictions and rate limits before generating a token.
    """
    _set_embed_cors_headers(response, request)
    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Check if agent is active
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active",
        )

    # Get embed config
    try:
        config_response = (
            voice_agent_service.supabase.table("agent_embed_configs")
            .select("*")
            .eq("agent_id", str(agent_id))
            .execute()
        )

        if not config_response.data or len(config_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embed configuration not found",
            )

        embed_config = config_response.data[0]

        if not embed_config.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Embed is not active",
            )

        # Validate the browser request origin if restrictions are set. The
        # embeddable script makes this request from the host page, so Origin is
        # the authoritative value used for allowlisting.
        allowed_domains = embed_config.get("allowed_domains")
        if allowed_domains:
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            request_domain = origin or referer or ""

            if not embed_service.validate_domain(allowed_domains, request_domain):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Domain not authorized",
                )

        # Check rate limits
        daily_limit = embed_config.get("daily_call_limit", 100)

        # Count calls in last 24 hours
        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        calls_response = (
            voice_agent_service.supabase.table("embed_call_logs")
            .select("id", count="exact")
            .eq("embed_config_id", embed_config["id"])
            .gte("started_at", since)
            .execute()
        )

        current_usage = calls_response.count or 0

        if not embed_service.check_rate_limit(
            str(embed_config["id"]), daily_limit, current_usage
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily call limit exceeded. Please try again tomorrow.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking rate limits: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check rate limits",
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
            "Public embed voice session denied agent_id=%s code=%s",
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

    # Generate embed token
    domain = request.headers.get("origin", "") or request.headers.get("referer", "")
    source_domain = normalize_domain(domain)
    ip_address = request.client.host if request.client else None

    embed_token, voice_token, ws_url, session_id = embed_service.generate_embed_token(
        agent_id=str(agent_id),
        embed_config_id=str(embed_config["id"]),
        domain=source_domain or domain,
        ip_address=ip_address,
        demo_reservation=reservation,
        source_url=source_url,
    )

    if not embed_token or not voice_token or not ws_url or not session_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate embed token",
        )

    # Log the call
    try:
        user_agent = request.headers.get("user-agent", "")
        voice_agent_service.supabase.table("embed_call_logs").insert(
            {
                "embed_config_id": str(embed_config["id"]),
                "domain": source_domain,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": "started",
            }
        ).execute()
    except Exception as e:
        logger.error(f"Failed to log embed call: {e}", exc_info=True)
        # Don't fail the request if logging fails

    return PublicEmbedTokenResponse(
        token=voice_token,
        wsUrl=ws_url,
        sessionId=session_id,
        demo_calls_remaining=(reservation.calls_remaining if reservation else None),
        demo_max_call_duration_seconds=(
            reservation.max_call_duration_seconds if reservation else None
        ),
    )


@embed_router.options("/agent/{agent_id}/token")
async def handle_embed_token_options(request: Request, response: Response) -> Response:
    """Handle browser preflight requests for the public embed token endpoint."""
    response.status_code = status.HTTP_204_NO_CONTENT
    _set_embed_cors_headers(response, request)
    return response
