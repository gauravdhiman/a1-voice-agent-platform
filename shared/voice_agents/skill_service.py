"""
Skill service for managing organization skills and agent skill assignments.

Skills are reusable knowledge/procedure packages (markdown) that can be
assigned to agents. They use progressive disclosure — only metadata is
loaded in the system prompt; full content is loaded on-demand via tool call.
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from opentelemetry import metrics, trace
from supabase import Client

from shared.config import supabase_config

from .skill_models import (
    AgentSkillResponse,
    OrganizationSkill,
    OrganizationSkillCreate,
    OrganizationSkillSummary,
    OrganizationSkillUpdate,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

skill_operations_counter = meter.create_counter(
    "skill.operations", description="Number of skill operations"
)


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class SkillService:
    """Service for managing organization skills and agent assignments."""

    def __init__(self) -> None:
        self.supabase_config = supabase_config

    @property
    def supabase(self) -> Optional[Client]:
        """Get Supabase client."""
        return self.supabase_config.client

    @tracer.start_as_current_span("skill.get_organization_skills")
    async def get_organization_skills(
        self, org_id: UUID
    ) -> tuple[List[OrganizationSkill], Optional[str]]:
        """Get all skills for an organization."""
        skill_operations_counter.add(1, {"operation": "get_organization_skills"})
        try:
            response = (
                self.supabase.table("organization_skills")
                .select("*")
                .eq("organization_id", str(org_id))
                .order("name")
                .execute()
            )
            skills = [OrganizationSkill(**item) for item in response.data]
            return skills, None
        except Exception as e:
            logger.error(f"Error getting skills for org {org_id}: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("skill.get_skill_by_id")
    async def get_skill_by_id(
        self, skill_id: UUID
    ) -> tuple[Optional[OrganizationSkill], Optional[str]]:
        """Get a skill by its ID."""
        try:
            response = (
                self.supabase.table("organization_skills")
                .select("*")
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return None, "Skill not found"
            return OrganizationSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error getting skill {skill_id}: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.get_skill_content_by_slug")
    async def get_skill_content_by_slug(
        self, org_id: UUID, slug: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Get full skill content by org ID and slug. Used by the load_skill tool."""
        skill_operations_counter.add(1, {"operation": "get_skill_content"})
        try:
            response = (
                self.supabase.table("organization_skills")
                .select("content")
                .eq("organization_id", str(org_id))
                .eq("slug", slug)
                .eq("is_active", True)
                .execute()
            )
            if not response.data:
                return None, f"Skill '{slug}' not found or inactive"
            return response.data[0]["content"], None
        except Exception as e:
            logger.error(f"Error getting skill content {slug}: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.create_skill")
    async def create_skill(
        self, skill_data: OrganizationSkillCreate
    ) -> tuple[Optional[OrganizationSkill], Optional[str]]:
        """Create a new organization skill."""
        skill_operations_counter.add(1, {"operation": "create_skill"})
        try:
            response = (
                self.supabase.table("organization_skills")
                .insert(
                    {
                        "organization_id": str(skill_data.organization_id),
                        "slug": skill_data.slug,
                        "name": skill_data.name,
                        "description": skill_data.description,
                        "content": skill_data.content,
                        "category": skill_data.category,
                        "is_active": skill_data.is_active,
                        "version": skill_data.version,
                        "author": skill_data.author,
                        "content_hash": _compute_content_hash(skill_data.content),
                        "source_url": skill_data.source_url,
                        "source_ref": skill_data.source_ref,
                    }
                )
                .execute()
            )
            if not response.data:
                return None, "Failed to create skill"
            return OrganizationSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error creating skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.update_skill")
    async def update_skill(
        self, skill_id: UUID, skill_data: OrganizationSkillUpdate
    ) -> tuple[Optional[OrganizationSkill], Optional[str]]:
        """Update an existing skill."""
        skill_operations_counter.add(1, {"operation": "update_skill"})
        try:
            update_data = skill_data.model_dump(exclude_unset=True)
            if not update_data:
                return await self.get_skill_by_id(skill_id)

            response = (
                self.supabase.table("organization_skills")
                .update(update_data)
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return None, "Skill not found or update failed"
            return OrganizationSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating skill {skill_id}: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.delete_skill")
    async def delete_skill(
        self, skill_id: UUID
    ) -> tuple[bool, Optional[str]]:
        """Delete a skill."""
        skill_operations_counter.add(1, {"operation": "delete_skill"})
        try:
            response = (
                self.supabase.table("organization_skills")
                .delete()
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return False, "Skill not found"
            return True, None
        except Exception as e:
            logger.error(f"Error deleting skill {skill_id}: {e}", exc_info=True)
            return False, str(e)

    # --- Agent skill assignments ---

    @tracer.start_as_current_span("skill.get_agent_skills")
    async def get_agent_skills(
        self, agent_id: UUID
    ) -> tuple[List[AgentSkillResponse], Optional[str]]:
        """Get all skills assigned to an agent with full skill data."""
        skill_operations_counter.add(1, {"operation": "get_agent_skills"})
        try:
            response = (
                self.supabase.table("agent_skills")
                .select("*, skill:organization_skills(*)")
                .eq("agent_id", str(agent_id))
                .eq("is_active", True)
                .execute()
            )
            results = []
            for item in response.data:
                if item.get("skill"):
                    results.append(
                        AgentSkillResponse(
                            id=item["id"],
                            agent_id=item["agent_id"],
                            skill_id=item["skill_id"],
                            skill=OrganizationSkill(**item["skill"]),
                            is_active=item["is_active"],
                            created_at=item["created_at"],
                        )
                    )
            return results, None
        except Exception as e:
            logger.error(f"Error getting agent skills {agent_id}: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("skill.get_agent_skill_summaries")
    async def get_agent_skill_summaries(
        self, agent_id: UUID
    ) -> tuple[List[OrganizationSkillSummary], Optional[str]]:
        """Get lightweight skill summaries for an agent (for prompt injection)."""
        skill_operations_counter.add(1, {"operation": "get_agent_skill_summaries"})
        try:
            response = (
                self.supabase.table("agent_skills")
                .select("skill:organization_skills(slug, name, description)")
                .eq("agent_id", str(agent_id))
                .eq("is_active", True)
                .execute()
            )
            summaries = []
            for item in response.data:
                if item.get("skill"):
                    summaries.append(
                        OrganizationSkillSummary(
                            slug=item["skill"]["slug"],
                            name=item["skill"]["name"],
                            description=item["skill"].get("description"),
                        )
                    )
            return summaries, None
        except Exception as e:
            logger.error(f"Error getting skill summaries {agent_id}: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("skill.assign_skill")
    async def assign_skill(
        self, agent_id: UUID, skill_id: UUID
    ) -> tuple[bool, Optional[str]]:
        """Assign a skill to an agent."""
        skill_operations_counter.add(1, {"operation": "assign_skill"})
        try:
            response = (
                self.supabase.table("agent_skills")
                .upsert(
                    {
                        "agent_id": str(agent_id),
                        "skill_id": str(skill_id),
                        "is_active": True,
                    },
                    on_conflict="agent_id,skill_id",
                )
                .execute()
            )
            return bool(response.data), None
        except Exception as e:
            logger.error(f"Error assigning skill: {e}", exc_info=True)
            return False, str(e)

    @tracer.start_as_current_span("skill.unassign_skill")
    async def unassign_skill(
        self, agent_id: UUID, skill_id: UUID
    ) -> tuple[bool, Optional[str]]:
        """Unassign a skill from an agent."""
        skill_operations_counter.add(1, {"operation": "unassign_skill"})
        try:
            response = (
                self.supabase.table("agent_skills")
                .delete()
                .eq("agent_id", str(agent_id))
                .eq("skill_id", str(skill_id))
                .execute()
            )
            return True, None
        except Exception as e:
            logger.error(f"Error unassigning skill: {e}", exc_info=True)
            return False, str(e)

    # --- Seeding ---

    @tracer.start_as_current_span("skill.seed_built_in_skills")
    async def seed_built_in_skills(
        self, org_id: UUID
    ) -> tuple[int, Optional[str]]:
        """Seed built-in skills for a new organization.

        Returns:
            Tuple of (count of skills created, error message or None).
        """
        skill_operations_counter.add(1, {"operation": "seed_built_in_skills"})
        try:
            from src.voice_agents.skill_seeds import BUILT_IN_SKILLS

            count = 0
            for seed in BUILT_IN_SKILLS:
                new_hash = _compute_content_hash(seed["content"])

                # Check if already exists
                existing = (
                    self.supabase.table("organization_skills")
                    .select("id, category, content_hash")
                    .eq("organization_id", str(org_id))
                    .eq("slug", seed["slug"])
                    .execute()
                )

                if existing.data:
                    row = existing.data[0]
                    # Only update built-in skills whose content has changed
                    if row.get("category") == "built_in" and row.get("content_hash") != new_hash:
                        self.supabase.table("organization_skills").update(
                            {
                                "name": seed["name"],
                                "description": seed["description"],
                                "content": seed["content"],
                                "content_hash": new_hash,
                                "version": "1.0.0",
                            }
                        ).eq("id", row["id"]).execute()
                        count += 1
                    continue

                self.supabase.table("organization_skills").insert(
                    {
                        "organization_id": str(org_id),
                        "slug": seed["slug"],
                        "name": seed["name"],
                        "description": seed["description"],
                        "content": seed["content"],
                        "content_hash": new_hash,
                        "category": "built_in",
                        "is_active": True,
                        "version": "1.0.0",
                        "author": "Platform",
                    }
                ).execute()
                count += 1

            logger.info(f"Seeded {count} built-in skills for org {org_id}")
            return count, None
        except Exception as e:
            logger.error(f"Error seeding skills for org {org_id}: {e}", exc_info=True)
            return 0, str(e)


    @tracer.start_as_current_span("skill.sync_built_in_skills_all_orgs")
    async def sync_built_in_skills_all_orgs(self) -> tuple[int, Optional[str]]:
        """Ensure all organizations have the latest built-in skills.

        Called on app startup or via admin endpoint. Idempotent.
        Uses content_hash to skip unchanged skills efficiently.

        Returns:
            Tuple of (total skills created/updated across all orgs, error or None).
        """
        skill_operations_counter.add(1, {"operation": "sync_all_orgs"})
        try:
            response = (
                self.supabase.table("organizations")
                .select("id")
                .eq("is_active", True)
                .execute()
            )
            total = 0
            for org in response.data:
                count, error = await self.seed_built_in_skills(org["id"])
                if error:
                    logger.warning(f"Failed to sync skills for org {org['id']}: {error}")
                else:
                    total += count
            logger.info(f"Synced built-in skills across {len(response.data)} orgs: {total} changes")
            return total, None
        except Exception as e:
            logger.error(f"Error syncing built-in skills: {e}", exc_info=True)
            return 0, str(e)


skill_service = SkillService()
