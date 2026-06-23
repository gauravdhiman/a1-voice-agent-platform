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
    SkillFile,
    SkillFileCreate,
    SkillFileSummary,
    SkillFileUpdate,
    SkillForkRequest,
    SkillImportRequest,
    SkillImportResult,
    SkillRefreshRequest,
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

    # Verify skill belongs to this org
    existing, err = await skill_service.get_skill_by_id(skill_id)
    if err or not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if str(existing.organization_id) != str(org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

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
    "/skills/seed-platform",
    status_code=status.HTTP_200_OK,
)
@tracer.start_as_current_span("skill.routes.seed_platform")
async def seed_platform_skills(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Manually re-seed platform skills from code templates.

    Platform admin only. Idempotent — uses content_hash to skip unchanged skills.
    Call this after updating built-in skill definitions in the codebase.
    """
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform admins can seed platform skills",
        )

    count, error = await skill_service.seed_platform_skills()
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return {"seeded": count}


@skill_router.post(
    "/skills/sync-platform",
    status_code=status.HTTP_200_OK,
)
@tracer.start_as_current_span("skill.routes.sync_platform")
async def sync_platform_skills(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Sync platform skills across all organizations.

    Platform admin only. Ensures all orgs have the latest built-in skill templates
    available in the platform library. Uses content_hash to efficiently skip
    unchanged skills. Call this after adding or updating built-in skill definitions.
    """
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform admins can sync platform skills",
        )

    total, error = await skill_service.sync_built_in_skills_all_orgs()
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return {"synced": total}


@skill_router.get(
    "/organizations/{org_id}/skills/{skill_id}/agents",
)
@tracer.start_as_current_span("skill.routes.get_agents_using_skill")
async def get_agents_using_skill(
    org_id: UUID,
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get agents that have this skill assigned. Used for deletion warnings."""
    agents, error = await skill_service.get_agents_using_skill(skill_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return agents


# --- Skill reference files ---


@skill_router.get(
    "/organizations/{org_id}/skills/{skill_id}/files",
    response_model=List[SkillFileSummary],
)
@tracer.start_as_current_span("skill.routes.get_skill_files")
async def get_skill_files(
    org_id: UUID,
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get all files for a skill (summaries without content, for file tree)."""
    files, error = await skill_service.get_skill_files(skill_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return files


@skill_router.post(
    "/organizations/{org_id}/skills/{skill_id}/files",
    response_model=SkillFile,
    status_code=status.HTTP_201_CREATED,
)
@tracer.start_as_current_span("skill.routes.create_skill_file")
async def create_skill_file(
    org_id: UUID,
    skill_id: UUID,
    file_data: SkillFileCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a reference file within a skill. Admin only."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create skill files",
            )

    # Verify skill exists and belongs to this org
    existing, err = await skill_service.get_skill_by_id(skill_id)
    if err or not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if str(existing.organization_id) != str(org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    file, error = await skill_service.create_skill_file(skill_id, file_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return file


@skill_router.put(
    "/organizations/{org_id}/skills/{skill_id}/files/{file_id}",
    response_model=SkillFile,
)
@tracer.start_as_current_span("skill.routes.update_skill_file")
async def update_skill_file(
    org_id: UUID,
    skill_id: UUID,
    file_id: UUID,
    file_data: SkillFileUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update a reference file. Admin only."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update skill files",
            )

    file, error = await skill_service.update_skill_file(file_id, file_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return file


@skill_router.delete(
    "/organizations/{org_id}/skills/{skill_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@tracer.start_as_current_span("skill.routes.delete_skill_file")
async def delete_skill_file(
    org_id: UUID,
    skill_id: UUID,
    file_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Delete a reference file. Admin only."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete skill files",
            )

    success, error = await skill_service.delete_skill_file(file_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


# --- Tool-facing: reference file content retrieval ---


@skill_router.get(
    "/skills/{org_id}/{slug}/files/{file_path:path}",
    response_model=str,
)
@tracer.start_as_current_span("skill.routes.get_skill_file_content")
async def get_skill_file_content(
    org_id: UUID,
    slug: str,
    file_path: str,
):
    """Get a skill reference file's content by org_id, slug, and file path.

    Called by the worker's load_skill_reference tool for progressive disclosure.
    """
    content, error = await skill_service.get_skill_file_content_by_slug(
        org_id, slug, file_path
    )
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return content


# --- Skill import ---


@skill_router.post(
    "/organizations/{org_id}/skills/import",
    response_model=List[SkillImportResult],
)
@tracer.start_as_current_span("skill.routes.import_skill")
async def import_skill_from_url(
    org_id: UUID,
    request: SkillImportRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Import a skill from a GitHub URL or skills.sh URL.

    Fetches the entire skill package (SKILL.md + all reference files)
    via GitHub REST API. Admin only.
    """
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to import skills",
            )

    try:
        from src.voice_agents.skill_import import SkillImporter

        importer = SkillImporter()
        packages = await importer.fetch_skill_packages(request.url)

        results = []
        for pkg in packages:
            # Create the skill
            from shared.voice_agents.skill_models import OrganizationSkillCreate

            skill_data = OrganizationSkillCreate(
                organization_id=org_id,
                slug=pkg.slug,
                name=pkg.name,
                description=pkg.description,
                content=pkg.content,
                category="custom",
            )

            skill, error = await skill_service.create_skill(skill_data)
            if error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create skill '{pkg.slug}': {error}",
                )

            # Create reference files
            files_count = 0
            if pkg.files and skill:
                from shared.voice_agents.skill_models import SkillFileCreate

                file_creates = [
                    SkillFileCreate(
                        file_path=f.file_path,
                        content=f.content,
                        file_kind=f.file_kind,
                    )
                    for f in pkg.files
                ]
                files_count, file_error = await skill_service.bulk_create_skill_files(
                    skill.id, file_creates
                )
                if file_error:
                    logger.warning(
                        f"Failed to create some files for '{pkg.slug}': {file_error}"
                    )

            results.append(
                SkillImportResult(
                    skill=skill,
                    files_imported=files_count,
                    source_url=pkg.source_url,
                )
            )

        return results

    except HTTPException:
        raise  # Re-raise HTTP exceptions (e.g., duplicate skill) directly
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing skill: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fork / Refresh (Platform Skill → Org Skill)
# ─────────────────────────────────────────────────────────────────────────────


@skill_router.post(
    "/organizations/{org_id}/skills/fork",
    response_model=OrganizationSkill,
    status_code=status.HTTP_201_CREATED,
)
@tracer.start_as_current_span("skill.routes.fork_skill")
async def fork_platform_skill(
    org_id: UUID,
    request: SkillForkRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Fork a platform skill into the org's library.

    Creates an independent copy with all files. Org admin can edit freely.
    """
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to fork skills",
            )

    skill, error = await skill_service.fork_platform_skill(
        org_id=org_id,
        platform_skill_id=request.platform_skill_id,
        custom_name=request.custom_name,
        custom_slug=request.custom_slug,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return skill


@skill_router.get(
    "/organizations/{org_id}/skills/{skill_id}/update-check",
)
@tracer.start_as_current_span("skill.routes.check_update")
async def check_skill_update(
    org_id: UUID,
    skill_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Check if a forked skill has an update available from its platform source."""
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    has_update, latest_version, error = await skill_service.check_update_available(skill_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {
        "update_available": has_update,
        "latest_version": latest_version,
        "current_version": None,  # Frontend has this from skill object
    }


@skill_router.post(
    "/organizations/{org_id}/skills/{skill_id}/refresh",
    response_model=OrganizationSkill,
)
@tracer.start_as_current_span("skill.routes.refresh_skill")
async def refresh_forked_skill(
    org_id: UUID,
    skill_id: UUID,
    request: SkillRefreshRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Refresh a forked skill from its platform source.

    Replaces ALL content and files with the platform's latest version.
    Requires explicit confirmation (confirm_overwrite=true).
    """
    current_user_id, user_profile = user_data

    if not user_profile.has_role("platform_admin"):
        if not user_profile.has_role("org_admin", str(org_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to refresh skills",
            )

    if not request.confirm_overwrite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirm_overwrite must be true to accept full bundle replacement",
        )

    skill, error = await skill_service.refresh_forked_skill(skill_id, current_user_id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return skill
