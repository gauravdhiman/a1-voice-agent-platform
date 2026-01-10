"""
Voice Agent API routes for multi-tenant SaaS platform.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from opentelemetry import trace
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.voice_agents.models import VoiceAgent, VoiceAgentCreate, VoiceAgentUpdate
from shared.voice_agents.service import voice_agent_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
agent_router = APIRouter(prefix="/api/v1/agents", tags=["Voice Agents"])


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


@agent_router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
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

    success, error = await voice_agent_service.delete_agent(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return None
