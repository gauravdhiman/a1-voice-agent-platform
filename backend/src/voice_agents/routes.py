"""
Voice Agent API routes for multi-tenant SaaS platform.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from opentelemetry import trace
from pydantic import BaseModel
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.voice_agents.models import VoiceAgent, VoiceAgentCreate, VoiceAgentUpdate
from shared.voice_agents.prompt_builder import PromptBuilder
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.livekit_service import livekit_service
from src.organization.service import OrganizationService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
agent_router = APIRouter(prefix="/api/v1/agents", tags=["Voice Agents"])


class TestTokenResponse(BaseModel):
    """Response model for test token generation."""

    token: str
    serverUrl: str
    roomName: str


@agent_router.post("/", response_model=VoiceAgent, status_code=status.HTTP_201_CREATED)
@tracer.start_as_current_span("voice_agent.routes.create_agent")
async def create_agent(
    agent_data: VoiceAgentCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a new voice agent."""
    current_user_id, user_profile = user_data

    # Check if user has permission for this organization
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent_data.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create agents for this organization",
            )

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

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(org_id)
        ) and not user_profile.has_role("regular_user", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view agents for this organization",
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
            agents = [VoiceAgent(**item) for item in response.data]
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

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(agent.organization_id)
        ) and not user_profile.has_role("regular_user", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view this agent",
            )

    return agent


@agent_router.post("/{agent_id}/test-token", response_model=TestTokenResponse)
@tracer.start_as_current_span("voice_agent.routes.get_test_token")
async def get_test_token(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Generate a LiveKit token for browser-based agent testing.

    This endpoint allows users to test voice agents directly from the browser
    without making a phone call. The user connects to a LiveKit room where
    the AI agent joins and responds to voice input.
    """
    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission check - user must have access to this organization
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(agent.organization_id)
        ) and not user_profile.has_role("regular_user", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to test this agent",
            )

    # Check if agent is active
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot test an inactive agent. Please activate the agent first.",
        )

    # Generate test token
    token, server_url, room_name = livekit_service.generate_test_token(
        agent_id=str(agent_id),
        user_id=str(current_user_id),
    )

    if not token or not server_url or not room_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured. Please contact the administrator.",
        )

    return TestTokenResponse(
        token=token,
        serverUrl=server_url,
        roomName=room_name,
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

    # Permission check - user must have access to this organization
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(agent.organization_id)
        ) and not user_profile.has_role("regular_user", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view this agent",
            )

    # Get organization data
    org_service = OrganizationService()
    org, org_error = await org_service.get_organization_by_id(agent.organization_id)
    
    if org_error or not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch organization data: {org_error}",
        )

    # Generate the system prompt using PromptBuilder
    # Use a default rules template (similar to worker)
    default_rules = """# OUTPUT RULES & GUARDRAILS
- Keep responses concise and conversational for voice
- Be helpful, accurate, and professional
- Ask clarifying questions if needed
- Use tools when appropriate to complete tasks
- Never share sensitive information
"""
    
    system_prompt = PromptBuilder.build_system_prompt(
        org=org,
        agent=agent,
        default_rules=default_rules
    )

    return system_prompt


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

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update this agent",
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
    livekit_token: str
    server_url: str
    room_name: str


@agent_router.get("/{agent_id}/embed-config", response_model=Optional[EmbedConfigResponse])
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
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(agent.organization_id)
        ) and not user_profile.has_role("regular_user", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view this agent",
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
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to modify embed configuration",
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
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete embed configuration",
            )

    try:
        result = (
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
    a time-limited token for connecting to a LiveKit room.
    """
    from shared.voice_agents.embed_service import embed_service

    current_user_id, user_profile = user_data

    # Get the agent
    agent, error = await voice_agent_service.get_agent_by_id(agent_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(agent.organization_id)
        ) and not user_profile.has_role("regular_user", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
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

    # Generate embed token
    domain = request.headers.get("origin", "")
    ip_address = request.client.host if request.client else None

    embed_token, livekit_token, server_url, room_name = (
        embed_service.generate_embed_token(
            agent_id=str(agent_id),
            embed_config_id=str(embed_config["id"]),
            domain=domain,
            ip_address=ip_address,
        )
    )

    if not embed_token or not livekit_token or not server_url or not room_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate embed token",
        )

    return EmbedTokenResponse(
        embed_token=embed_token,
        livekit_token=livekit_token,
        server_url=server_url,
        room_name=room_name,
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

    # Permission check
    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete this agent",
            )

    response, error = await voice_agent_service.delete_agent(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return response
