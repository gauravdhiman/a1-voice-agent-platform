"""
Platform admin API routes for managing platform-level skill templates.

These routes are restricted to platform admins only. Platform skills are
immutable templates that org admins can fork into their own libraries.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from opentelemetry import trace
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.voice_agents.skill_models import (
    PlatformSkill,
    PlatformSkillCreate,
    PlatformSkillFile,
    PlatformSkillFileCreate,
    PlatformSkillFileSummary,
    PlatformSkillSummary,
    PlatformSkillUpdate,
)
from shared.voice_agents.skill_service import skill_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

platform_skill_router = APIRouter(prefix="/api/v1", tags=["Platform Skills"])


def _require_platform_admin(user_profile: UserProfile) -> None:
    """Raise 403 if user is not a platform admin."""
    if not user_profile.has_role("platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Platform Skill CRUD
# ─────────────────────────────────────────────────────────────────────────────


@platform_skill_router.get(
    "/platform/skills",
    response_model=List[PlatformSkillSummary],
)
@tracer.start_as_current_span("skill.platform.list")
async def list_platform_skills(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> List[PlatformSkillSummary]:
    """List all active platform skills.

    Available to any authenticated user so org admins can browse and fork
    skills into their organization's library.
    """
    skills, error = await skill_service.list_platform_skills()
    if error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error)
    return skills


@platform_skill_router.get(
    "/platform/skills/{skill_id}",
    response_model=PlatformSkill,
)
@tracer.start_as_current_span("skill.platform.get")
async def get_platform_skill(
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformSkill:
    """Get a single platform skill with full content and files (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    skill, error = await skill_service.get_platform_skill_by_id(skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return skill


@platform_skill_router.post(
    "/platform/skills",
    response_model=PlatformSkill,
    status_code=status.HTTP_201_CREATED,
)
@tracer.start_as_current_span("skill.platform.create")
async def create_platform_skill(
    skill_data: PlatformSkillCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformSkill:
    """Create a new platform skill template (platform admin only).

    Version is automatically set to current date format YYYY.MM.DD_1.
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    skill, error = await skill_service.create_platform_skill(skill_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return skill


@platform_skill_router.put(
    "/platform/skills/{skill_id}",
    response_model=PlatformSkill,
)
@tracer.start_as_current_span("skill.platform.update")
async def update_platform_skill(
    skill_id: UUID,
    skill_data: PlatformSkillUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformSkill:
    """Update a platform skill. Bumps version automatically (platform admin only).

    Updating a platform skill does NOT affect existing org forks.
    Org admins must opt-in to refresh their forks.
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    skill, error = await skill_service.update_platform_skill(skill_id, skill_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return skill


@platform_skill_router.delete(
    "/platform/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@tracer.start_as_current_span("skill.platform.delete")
async def delete_platform_skill(
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> None:
    """Deprecate a platform skill (platform admin only).

    This sets is_active=false. Existing forks in orgs continue to work,
    but new forks are blocked.
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    success, error = await skill_service.delete_platform_skill(skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


# ─────────────────────────────────────────────────────────────────────────────
# Platform Skill Files
# ─────────────────────────────────────────────────────────────────────────────


@platform_skill_router.get(
    "/platform/skills/{skill_id}/files",
    response_model=List[PlatformSkillFileSummary],
)
@tracer.start_as_current_span("skill.platform.list_files")
async def list_platform_skill_files(
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> List[PlatformSkillFileSummary]:
    """List reference files for a platform skill (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    files, error = await skill_service.list_platform_skill_files(skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return files


@platform_skill_router.get(
    "/platform/skills/{skill_id}/files/{file_id}",
    response_model=PlatformSkillFile,
)
@tracer.start_as_current_span("skill.platform.get_file")
async def get_platform_skill_file(
    skill_id: UUID,
    file_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformSkillFile:
    """Get a single platform skill file with full content (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    file, error = await skill_service.get_platform_skill_file(file_id)
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return file


@platform_skill_router.post(
    "/platform/skills/{skill_id}/files",
    response_model=PlatformSkillFile,
    status_code=status.HTTP_201_CREATED,
)
@tracer.start_as_current_span("skill.platform.create_file")
async def create_platform_skill_file(
    skill_id: UUID,
    file_data: PlatformSkillFileCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformSkillFile:
    """Add a reference file to a platform skill (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    file, error = await skill_service.create_platform_skill_file(skill_id, file_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return file


@platform_skill_router.put(
    "/platform/skills/{skill_id}/files/{file_id}",
    response_model=PlatformSkillFile,
)
@tracer.start_as_current_span("skill.platform.update_file")
async def update_platform_skill_file(
    skill_id: UUID,
    file_id: UUID,
    file_data: PlatformSkillFileCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformSkillFile:
    """Update a platform skill file (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    file, error = await skill_service.update_platform_skill_file(file_id, file_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return file


@platform_skill_router.delete(
    "/platform/skills/{skill_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@tracer.start_as_current_span("skill.platform.delete_file")
async def delete_platform_skill_file(
    skill_id: UUID,
    file_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> None:
    """Delete a platform skill file (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    success, error = await skill_service.delete_platform_skill_file(file_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
