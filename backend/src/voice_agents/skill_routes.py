"""
Skill API routes for managing organization skills and agent skill assignments.

Skills are reusable knowledge/procedure packages (markdown) that can be
assigned to agents. They use progressive disclosure — only metadata is
loaded in the system prompt; full content is loaded on-demand via tool call.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from opentelemetry import trace
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.voice_agents.skill_models import (
    AgentSkillAssignment,
    AgentSkillResponse,
    OrganizationSkill,
    OrganizationSkillCreate,
    OrganizationSkillUpdate,
)
from shared.voice_agents.skill_service import skill_service
from shared.voice_agents.service import voice_agent_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

skill_router = APIRouter(prefix="/api/v1", tags=["Skills"])


# --- Organization-level skill management ---


@skill_router.get(
    "/organizations/{org_id}/skills",
    response_model=List[OrganizationSkill],
)
@tracer.start_as_current_span("skill.routes.get_org_skills")
async def get_organization_skills(
    org_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get all skills for an organization."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role(
            "org_admin", str(org_id)
        ) and not user_profile.has_role("regular_user", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view skills",
            )

    skills, error = await skill_service.get_organization_skills(org_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return skills


@skill_router.post(
    "/organizations/{org_id}/skills",
    response_model=OrganizationSkill,
    status_code=status.HTTP_201_CREATED,
)
@tracer.start_as_current_span("skill.routes.create_skill")
async def create_skill(
    org_id: UUID,
    skill_data: OrganizationSkillCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a new custom skill for an organization."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create skills",
            )

    # Ensure org_id matches
    skill_data.organization_id = org_id

    skill, error = await skill_service.create_skill(skill_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return skill


@skill_router.put(
    "/organizations/{org_id}/skills/{skill_id}",
    response_model=OrganizationSkill,
)
@tracer.start_as_current_span("skill.routes.update_skill")
async def update_skill(
    org_id: UUID,
    skill_id: UUID,
    skill_data: OrganizationSkillUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update a skill."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update skills",
            )

    # Verify skill belongs to this org
    existing, err = await skill_service.get_skill_by_id(skill_id)
    if err or not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if str(existing.organization_id) != str(org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    # Prevent editing built-in skills' content (only allow toggling is_active)
    if existing.category == "built_in":
        if skill_data.content is not None or skill_data.name is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Built-in skills cannot be edited. You can only enable or disable them.",
            )

    skill, error = await skill_service.update_skill(skill_id, skill_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return skill


@skill_router.delete(
    "/organizations/{org_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@tracer.start_as_current_span("skill.routes.delete_skill")
async def delete_skill(
    org_id: UUID,
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete a custom skill."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete skills",
            )

    # Verify skill belongs to this org and is not built-in
    existing, err = await skill_service.get_skill_by_id(skill_id)
    if err or not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if str(existing.organization_id) != str(org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if existing.category == "built_in":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Built-in skills cannot be deleted. Disable them instead.",
        )

    success, error = await skill_service.delete_skill(skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


# --- Agent skill assignments ---


@skill_router.get(
    "/agents/{agent_id}/skills",
    response_model=List[AgentSkillResponse],
)
@tracer.start_as_current_span("skill.routes.get_agent_skills")
async def get_agent_skills(
    agent_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get all skills assigned to an agent. Any org member can read."""
    current_user_id, user_profile = user_data

    # Any org member can view agent skills (read-only access)
    skills, error = await skill_service.get_agent_skills(agent_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return skills


@skill_router.post(
    "/agents/{agent_id}/skills",
    status_code=status.HTTP_201_CREATED,
)
@tracer.start_as_current_span("skill.routes.assign_skill")
async def assign_skill_to_agent(
    agent_id: UUID,
    assignment: AgentSkillAssignment,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Assign a skill to an agent. Only platform admin or org admin."""
    current_user_id, user_profile = user_data

    # Only admins can assign skills to agents
    agent, err = await voice_agent_service.get_agent_by_id(agent_id)
    if err or not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only platform admins or organization admins can assign skills to agents",
            )

    success, error = await skill_service.assign_skill(agent_id, assignment.skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {"success": True}


@skill_router.delete(
    "/agents/{agent_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@tracer.start_as_current_span("skill.routes.unassign_skill")
async def unassign_skill_from_agent(
    agent_id: UUID,
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Unassign a skill from an agent. Only platform admin or org admin."""
    current_user_id, user_profile = user_data

    # Only admins can unassign skills from agents
    agent, err = await voice_agent_service.get_agent_by_id(agent_id)
    if err or not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(agent.organization_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only platform admins or organization admins can unassign skills from agents",
            )

    success, error = await skill_service.unassign_skill(agent_id, skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


# --- Tool-facing: content retrieval for load_skill ---


@skill_router.get(
    "/skills/{org_id}/{slug}",
    response_model=str,
)
@tracer.start_as_current_span("skill.routes.get_skill_content")
async def get_skill_content(
    org_id: UUID,
    slug: str,
):
    """Get full skill content by org ID and slug.

    This endpoint is called by the worker's load_skill tool to retrieve
    skill content on-demand during a call. It uses agent API key auth
    (not user session auth) in production.
    """
    content, error = await skill_service.get_skill_content_by_slug(org_id, slug)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return content


# --- Seeding endpoint ---


@skill_router.post(
    "/organizations/{org_id}/skills/seed",
    status_code=status.HTTP_200_OK,
)
@tracer.start_as_current_span("skill.routes.seed_skills")
async def seed_organization_skills(
    org_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Seed built-in skills for an organization. Idempotent."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    count, error = await skill_service.seed_built_in_skills(org_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return {"seeded": count}


@skill_router.post(
    "/skills/sync-all",
    status_code=status.HTTP_200_OK,
)
@tracer.start_as_current_span("skill.routes.sync_all_orgs")
async def sync_built_in_skills_all_orgs(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Sync built-in skills across all organizations.

    Platform admin only. Uses content_hash to efficiently skip unchanged skills.
    Call this after adding or updating built-in skill definitions.
    """
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform admins can sync skills across all organizations",
        )

    total, error = await skill_service.sync_built_in_skills_all_orgs()
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return {"synced": total}
