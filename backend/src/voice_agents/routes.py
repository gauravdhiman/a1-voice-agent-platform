"""
Voice Agent API routes for multi-tenant SaaS platform.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from opentelemetry import trace
from pydantic import BaseModel
from src.auth.dependencies import assert_has_permission, require_permission
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.billing.entitlement_models import EntitlementDenied
from src.billing.entitlement_service import entitlement_service
from src.organization.service import OrganizationService

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    assert_voice_session_allowed,
    is_demo_agent,
    reserve_demo_call_if_needed,
)
from shared.config.settings import settings
from shared.voice_agents.default_voice_rules import DEFAULT_VOICE_SYSTEM_PROMPT
from shared.voice_agents.models import VoiceAgent, VoiceAgentCreate, VoiceAgentUpdate
from shared.voice_agents.preset_service import preset_service
from shared.voice_agents.prompt_builder import PromptBuilder
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.voice_session_service import voice_session_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
agent_router = APIRouter(prefix="/api/v1/agents", tags=["Voice Agents"])


class TestTokenResponse(BaseModel):
    """Response for browser test-call bootstrap over Pipecat WebSocket."""

    transport: str = "pipecat"
    token: str
    wsUrl: str
    sessionId: str
    demo_calls_remaining: Optional[int] = None
    demo_max_call_duration_seconds: Optional[int] = None


def _voice_session_http_exception(exc: VoiceSessionEntitlementError) -> HTTPException:
    """Translate a voice-session entitlement denial into an API error.

    Browser callers should receive the same actionable billing or concurrency
    reason that the voice worker would use to reject the WebSocket. This avoids
    issuing a token that can only fail later as a generic browser close code.

    Args:
        exc: Shared entitlement error raised during the pre-check.

    Returns:
        HTTPException with a stable error code and user-facing message.
    """
    status_code = {
        "INSUFFICIENT_CREDITS": status.HTTP_402_PAYMENT_REQUIRED,
        "MAX_CONCURRENT_CALLS": status.HTTP_409_CONFLICT,
        "DEMO_CALL_LIMIT_REACHED": status.HTTP_429_TOO_MANY_REQUESTS,
        "DEMO_CALL_RESERVATION_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    }.get(exc.code, status.HTTP_403_FORBIDDEN)
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


async def _validate_preset_assignment(preset_id: Optional[UUID]) -> Optional[str]:
    """Validate that ``preset_id`` may be assigned to an agent.

    A preset referenced by an agent must exist and be **published** — assigning a
    draft would let an org admin pin an unfinished platform-admin authoring
    state. Returns an error string (suitable for a 400 response) on failure, or
    ``None`` if the assignment is valid. ``preset_id is None`` (clearing the
    preset / legacy agent) is always valid.

    Args:
        preset_id: The preset id to validate, or ``None``.

    Returns:
        ``None`` if valid, else an error message.
    """
    if preset_id is None:
        return None
    preset, err = await preset_service.get_preset_by_id(preset_id)
    if err:
        return f"Could not validate preset: {err}"
    if preset is None:
        return f"Preset {preset_id} not found"
    if not preset.is_published:
        return f"Preset '{preset.name}' is not published; only published presets can be assigned to agents"
    return None


@agent_router.post("/", response_model=VoiceAgent, status_code=status.HTTP_201_CREATED)
@tracer.start_as_current_span("voice_agent.routes.create_agent")
async def create_agent(
    agent_data: VoiceAgentCreate,
    request: Request,
    _auth: tuple[UUID, UserProfile] = Depends(
        require_permission(
            "agent",
            "create",
            org_id_source="body",
            body_field="organization_id",
        )
    ),
):
    """Create a new voice agent.

    Permission check is declarative via the `require_permission` factory
    (Task #22 — Phase 5). The factory reads `organization_id` from the
    request body and asserts the caller holds `agent:create` on that org
    (or is platform_admin).

    Args:
        agent_data: Pydantic body for the new agent. Must include
            `organization_id` (UUID).
        request: The raw Starlette Request, required by the
            `require_permission` factory to read the body for org scoping.
        _auth: Injected auth tuple (user_id, profile). The factory does
            the actual check; the handler doesn't need to inspect it.
    """
    current_user_id, user_profile = _auth

    # Demo status, presentation, and budgets are platform_admin-only (prevents
    # org_admins from self-exempting billing or publishing platform-owned demos).
    protected_demo_fields = {
        "is_demo",
        "demo_slug",
        "public_description",
        "demo_public_result_url",
        "demo_calls_remaining",
        "demo_max_call_duration_seconds",
    }
    if protected_demo_fields & agent_data.model_fields_set:
        if not user_profile.has_role("platform_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only platform administrators can create demo agents, set "
                    "demo slugs, demo descriptions, result URLs, or demo call limits"
                ),
            )

    # Validate the preset assignment (must exist + be published) before creating.
    preset_error = await _validate_preset_assignment(agent_data.preset_id)
    if preset_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=preset_error
        )

    try:
        await entitlement_service.assert_limit(
            agent_data.organization_id, "max_agents", increment=1
        )
    except EntitlementDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.to_detail(),
        ) from exc

    agent, error = await voice_agent_service.create_agent(agent_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return agent


@agent_router.get("/organization/{org_id}", response_model=List[VoiceAgent])
@tracer.start_as_current_span("voice_agent.routes.get_org_agents")
async def get_org_agents(
    org_id: UUID, user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user)
):
    """Get all agents for an organization."""
    current_user_id, user_profile = user_data

    # Permission: agent:read on the org (platform_admin short-circuits via
    # _check_access; the canonical matrix grants agent:read to every
    # org-scoped role so this covers org_admin, regular_user, and
    # platform_admin uniformly).
    assert_has_permission(
        user_profile,
        "agent",
        "read",
        org_id,
        error_message="Insufficient permissions to view agents for this organization",
    )

    agents, error = await voice_agent_service.get_agents_by_organization(org_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return agents


@agent_router.get("/my-agents", response_model=List[VoiceAgent])
@tracer.start_as_current_span("voice_agent.routes.get_user_agents")
async def get_user_agents(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user)
):
    """Get all agents for current user across all organizations."""
    current_user_id, user_profile = user_data

    logger.info(
        f"Fetching agents for user: {current_user_id}, is_platform_admin: {user_profile.has_role('platform_admin')}"
    )

    # If user is platform admin, get all agents
    if user_profile.has_role("platform_admin"):
        logger.info("User is platform admin, fetching all agents")
        try:
            response = (
                voice_agent_service.supabase.table("voice_agents").select("*").execute()
            )
            mapped_rows = voice_agent_service._with_phone_number_mappings(response.data)
            agents = [VoiceAgent(**item) for item in mapped_rows]
            logger.info(f"Found {len(agents)} agents (platform admin)")
            return agents
        except Exception as e:
            logger.error(
                f"Error fetching all agents for platform admin: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    # Otherwise, get agents for user's organizations
    agents, error = await voice_agent_service.get_agents_for_user(current_user_id)

    logger.info(f"Found {len(agents)} agents for user {current_user_id}")
    if error:
        logger.error(f"Error fetching agents: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return agents


@agent_router.get("/{agent_id}", response_model=VoiceAgent)
@tracer.start_as_current_span("voice_agent.routes.get_agent")
async def get_agent(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get a voice agent by ID."""
    current_user_id, user_profile = user_data

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission: agent:read on the agent's org. The org id is only
    # known after the agent is loaded, so this is the post-load pattern
    # (assert_has_permission) rather than the factory form.
    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions to view this agent",
    )

    return agent


@agent_router.post("/{agent_id}/test-token", response_model=TestTokenResponse)
@tracer.start_as_current_span("voice_agent.routes.get_test_token")
async def get_test_token(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Bootstrap a browser test call via Pipecat WebSocket."""
    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission: agent:read on the agent's org. The test token is a
    # read-equivalent op (join a voice session to hear the agent), so the
    # same gate as `get_agent` applies.
    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions to test this agent",
    )

    reservation = None
    try:
        reservation = await reserve_demo_call_if_needed(agent)
        if is_demo_agent(agent):
            await assert_voice_session_allowed(
                agent.organization_id, agent_is_demo=True
            )
        else:
            await assert_voice_session_allowed(agent.organization_id)
    except VoiceSessionEntitlementError as exc:
        logger.info(
            "Browser voice session denied before token creation agent_id=%s "
            "organization_id=%s code=%s",
            agent_id,
            agent.organization_id,
            exc.code,
        )
        raise _voice_session_http_exception(exc) from exc
    try:
        token, session_id = voice_session_service.create_session_token(
            agent_id=str(agent_id),
            user_id=str(current_user_id),
            purpose="test_call",
            session_id=(reservation.session_id if reservation else None),
            demo_reservation_id=(reservation.reservation_id if reservation else None),
            demo_max_call_duration_seconds=(
                reservation.max_call_duration_seconds if reservation else None
            ),
        )
    except ValueError as exc:
        logger.error("Failed to create voice_ws session token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice session service is not configured. Set JWT_SECRET_KEY.",
        ) from exc

    base = settings.voice_ws_public_url.rstrip("/")
    ws_url = f"{base}/ws"
    return TestTokenResponse(
        transport="pipecat",
        token=token,
        wsUrl=ws_url,
        sessionId=session_id,
        demo_calls_remaining=(reservation.calls_remaining if reservation else None),
        demo_max_call_duration_seconds=(
            reservation.max_call_duration_seconds if reservation else None
        ),
    )


@agent_router.get("/{agent_id}/system-prompt", response_model=str)
@tracer.start_as_current_span("voice_agent.routes.get_system_prompt")
async def get_agent_system_prompt(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get the generated system prompt for an agent.

    This endpoint generates the system prompt on-demand by combining
    organization context and agent configuration. The prompt is not stored
    but derived from the current state of the agent and organization.
    """
    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission: agent:read on the agent's org (the system prompt is a
    # derived view of the agent's config).
    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions to view this agent",
    )

    # Get organization data
    org_service = OrganizationService()
    org, org_error = await org_service.get_organization_by_id(agent.organization_id)

    if org_error or not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch organization data: {org_error}",
        )

    # Use the same voice defaults as the runtime so the preview does not drift.
    system_prompt = PromptBuilder.build(
        org=org, agent=agent, default_rules=DEFAULT_VOICE_SYSTEM_PROMPT
    )

    return system_prompt


@agent_router.post("/{agent_id}/generate-markdown", response_model=str)
@tracer.start_as_current_span("voice_agent.routes.generate_markdown")
async def generate_markdown_from_fields(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Generate markdown instructions from existing field-based agent config.

    This helper converts the agent's current field-based configuration
    (persona, tone, mission, custom_instructions) plus organization context
    into a single markdown document that the user can edit.
    """
    current_user_id, user_profile = user_data

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions to view this agent",
    )

    org_service = OrganizationService()
    org, org_error = await org_service.get_organization_by_id(agent.organization_id)

    if org_error or not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch organization data: {org_error}",
        )

    # Build the field-based prompt (without guardrails/tool sections)
    # so the user gets a clean starting point for markdown editing
    sections = []

    role = agent.persona or "a helpful AI voice assistant"
    identity = role if role.lower().startswith("you are") else f"You are {role}"
    if org.name:
        identity += f" representing {org.name}"
    if agent.tone:
        identity += f". Your communication style is {agent.tone}."
    sections.append(f"# Identity and Persona\n\n{identity}")

    if agent.mission:
        sections.append(f"# Mission\n\n{agent.mission}")

    business_info = []
    if org.industry:
        business_info.append(f"- **Industry:** {org.industry}")
    if org.location:
        business_info.append(f"- **Location:** {org.location}")
    if org.business_details:
        business_info.append(f"\n{org.business_details}")
    if business_info:
        sections.append("# Business Context\n\n" + "\n".join(business_info))

    if agent.custom_instructions:
        sections.append(f"# Additional Instructions\n\n{agent.custom_instructions}")

    return "\n\n".join(sections)


@agent_router.put("/{agent_id}", response_model=VoiceAgent)
@tracer.start_as_current_span("voice_agent.routes.update_agent")
async def update_agent(
    agent_id: UUID,
    agent_data: VoiceAgentUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update a voice agent."""
    current_user_id, user_profile = user_data

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission: agent:update on the agent's org (platform_admin short-circuits).
    assert_has_permission(
        user_profile,
        "agent",
        "update",
        agent.organization_id,
        error_message="Insufficient permissions to update this agent",
    )

    # Demo status, slug, and public copy are platform_admin-only (even org_admins
    # cannot self-exempt or modify platform-owned public demo presentation).
    if {
        "is_demo",
        "demo_slug",
        "public_description",
        "demo_public_result_url",
        "demo_calls_remaining",
        "demo_max_call_duration_seconds",
    } & agent_data.model_fields_set:
        if not user_profile.has_role("platform_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only platform administrators can change demo status, demo "
                    "slugs, descriptions, result URLs, or demo call limits"
                ),
            )

    # Validate the preset assignment when it is being changed. ``preset_id`` is
    # Optional on VoiceAgentUpdate; only validate when explicitly supplied
    # (exclude_unset semantics) so omitting the field never trips validation.
    if "preset_id" in agent_data.model_fields_set:
        preset_error = await _validate_preset_assignment(agent_data.preset_id)
        if preset_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=preset_error
            )

    updated_agent, error = await voice_agent_service.update_agent(agent_id, agent_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return updated_agent


class EmbedConfigCreate(BaseModel):
    """Request model for creating/updating embed configuration."""

    button_text: str = "Call Us"
    button_color: str = "#3b82f6"
    button_text_color: str = "#ffffff"
    button_border_radius: int = 8
    button_size: str = "medium"
    button_position: str = "bottom-right"
    button_style: str = "filled"
    allowed_domains: Optional[List[str]] = None
    custom_css: Optional[str] = None
    is_active: bool = True
    daily_call_limit: int = 100


class EmbedConfigResponse(BaseModel):
    """Response model for embed configuration."""

    id: UUID
    agent_id: UUID
    button_text: str
    button_color: str
    button_text_color: str
    button_border_radius: int
    button_size: str
    button_position: str
    button_style: str
    allowed_domains: Optional[List[str]]
    custom_css: Optional[str]
    is_active: bool
    daily_call_limit: int
    created_at: str
    updated_at: str


class EmbedTokenResponse(BaseModel):
    """Response model for embed token generation."""

    embed_token: str
    token: str
    wsUrl: str
    sessionId: str
    demo_calls_remaining: Optional[int] = None
    demo_max_call_duration_seconds: Optional[int] = None


@agent_router.get(
    "/{agent_id}/embed-config", response_model=Optional[EmbedConfigResponse]
)
@tracer.start_as_current_span("voice_agent.routes.get_embed_config")
async def get_embed_config(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get embed configuration for an agent."""
    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission check
    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions to view this agent",
    )

    # Get embed config from database
    try:
        response = (
            voice_agent_service.supabase.table("agent_embed_configs")
            .select("*")
            .eq("agent_id", str(agent_id))
            .execute()
        )

        # Check if we got any data back
        if response.data and len(response.data) > 0:
            return EmbedConfigResponse(**response.data[0])
        return None

    except Exception as e:
        logger.error(f"Error fetching embed config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch embed configuration",
        )


@agent_router.post("/{agent_id}/embed-config", response_model=EmbedConfigResponse)
@tracer.start_as_current_span("voice_agent.routes.create_embed_config")
async def create_embed_config(
    agent_id: UUID,
    config_data: EmbedConfigCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create or update embed configuration for an agent."""
    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission check - only org_admin or platform_admin can modify
    assert_has_permission(
        user_profile,
        "agent",
        "update",
        agent.organization_id,
        error_message="Insufficient permissions to modify embed configuration",
    )

    # Check if config already exists
    try:
        existing = (
            voice_agent_service.supabase.table("agent_embed_configs")
            .select("id")
            .eq("agent_id", str(agent_id))
            .execute()
        )

        config_dict = config_data.model_dump()
        config_dict["agent_id"] = str(agent_id)

        if existing.data:
            # Update existing config
            config_id = existing.data[0]["id"]
            result = (
                voice_agent_service.supabase.table("agent_embed_configs")
                .update(config_dict)
                .eq("id", config_id)
                .execute()
            )
        else:
            # Create new config
            result = (
                voice_agent_service.supabase.table("agent_embed_configs")
                .insert(config_dict)
                .execute()
            )

        if result.data:
            return EmbedConfigResponse(**result.data[0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save embed configuration",
            )

    except Exception as e:
        logger.error(f"Error saving embed config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save embed configuration",
        )


@agent_router.delete("/{agent_id}/embed-config")
@tracer.start_as_current_span("voice_agent.routes.delete_embed_config")
async def delete_embed_config(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete embed configuration for an agent."""
    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission check
    assert_has_permission(
        user_profile,
        "agent",
        "update",
        agent.organization_id,
        error_message="Insufficient permissions to delete embed configuration",
    )

    try:
        (
            voice_agent_service.supabase.table("agent_embed_configs")
            .delete()
            .eq("agent_id", str(agent_id))
            .execute()
        )

        return {"message": "Embed configuration deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting embed config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete embed configuration",
        )


@agent_router.post("/{agent_id}/embed-token", response_model=EmbedTokenResponse)
@tracer.start_as_current_span("voice_agent.routes.get_embed_token")
async def get_embed_token(
    agent_id: UUID,
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Generate an embed token for browser-based agent calls.

    This endpoint is called from the embeddable call interface to obtain
    a time-limited token for connecting to a voice-ws WebSocket session.
    """
    from shared.voice_agents.embed_service import embed_service

    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission check
    assert_has_permission(
        user_profile,
        "agent",
        "read",
        agent.organization_id,
        error_message="Insufficient permissions",
    )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching embed config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch embed configuration",
        )

    reservation = None
    try:
        reservation = await reserve_demo_call_if_needed(agent)
        await assert_voice_session_allowed(
            agent.organization_id,
            agent_is_demo=is_demo_agent(agent),
        )
    except VoiceSessionEntitlementError as exc:
        logger.info(
            "Authenticated embed voice session denied agent_id=%s code=%s",
            agent_id,
            exc.code,
        )
        raise _voice_session_http_exception(exc) from exc

    # Generate embed token
    domain = request.headers.get("origin", "")
    ip_address = request.client.host if request.client else None

    embed_token, voice_token, ws_url, session_id = embed_service.generate_embed_token(
        agent_id=str(agent_id),
        embed_config_id=str(embed_config["id"]),
        domain=domain,
        ip_address=ip_address,
        demo_reservation=reservation,
    )

    if not embed_token or not voice_token or not ws_url or not session_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate embed token",
        )

    return EmbedTokenResponse(
        embed_token=embed_token,
        token=voice_token,
        wsUrl=ws_url,
        sessionId=session_id,
        demo_calls_remaining=(reservation.calls_remaining if reservation else None),
        demo_max_call_duration_seconds=(
            reservation.max_call_duration_seconds if reservation else None
        ),
    )


@agent_router.delete("/{agent_id}")
@tracer.start_as_current_span("voice_agent.routes.delete_agent")
async def delete_agent(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete a voice agent."""
    current_user_id, user_profile = user_data

    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission: agent:delete on the agent's org (platform_admin short-circuits).
    assert_has_permission(
        user_profile,
        "agent",
        "delete",
        agent.organization_id,
        error_message="Insufficient permissions to delete this agent",
    )

    response, error = await voice_agent_service.delete_agent(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return response
