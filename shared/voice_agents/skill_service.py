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

from shared.config import supabase_config
from supabase import Client

from .skill_models import (
    AgentSkillResponse,
    OrganizationSkill,
    OrganizationSkillCreate,
    OrganizationSkillSummary,
    OrganizationSkillUpdate,
    PlatformSkill,
    PlatformSkillCreate,
    PlatformSkillFile,
    PlatformSkillFileCreate,
    PlatformSkillFileSummary,
    PlatformSkillStatus,
    PlatformSkillSummary,
    PlatformSkillUpdate,
    SkillFile,
    SkillFileCreate,
    SkillFileSummary,
    SkillFileUpdate,
    SkillForkRequest,
    SkillRefreshRequest,
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
            # Check for duplicate slug within the same organization
            existing = (
                self.supabase.table("organization_skills")
                .select("id, name")
                .eq("organization_id", str(skill_data.organization_id))
                .eq("slug", skill_data.slug)
                .execute()
            )
            if existing.data:
                return None, (
                    f"A skill with slug '{skill_data.slug}' already exists in this organization "
                    f"('{existing.data[0]['name']}'). Delete the existing skill first or use a different slug."
                )

            # Org skills are always category='custom' under the platform fork
            # model. OrganizationSkillCreate no longer exposes category /
            # source_url / source_ref — those were removed with Phase 2c.
            response = (
                self.supabase.table("organization_skills")
                .insert(
                    {
                        "organization_id": str(skill_data.organization_id),
                        "slug": skill_data.slug,
                        "name": skill_data.name,
                        "description": skill_data.description,
                        "content": skill_data.content,
                        "category": "custom",
                        "is_active": skill_data.is_active,
                        "version": skill_data.version,
                        "author": skill_data.author,
                        "content_hash": _compute_content_hash(skill_data.content),
                        "source_skill_id": (
                            str(skill_data.source_skill_id)
                            if skill_data.source_skill_id
                            else None
                        ),
                        "source_version": skill_data.source_version,
                        "is_visible": skill_data.is_visible,
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
    async def delete_skill(self, skill_id: UUID) -> tuple[bool, Optional[str]]:
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
            logger.error(
                f"Error getting skill summaries {agent_id}: {e}", exc_info=True
            )
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

    @tracer.start_as_current_span("skill.get_agents_using_skill")
    async def get_agents_using_skill(
        self, skill_id: UUID
    ) -> tuple[List[dict], Optional[str]]:
        """Get agents that have this skill assigned (for deletion warnings).

        Returns a list of {id, name, is_active} dicts.
        """
        try:
            response = (
                self.supabase.table("agent_skills")
                .select("agent:voice_agents(id, name, is_active)")
                .eq("skill_id", str(skill_id))
                .execute()
            )
            agents = []
            for item in response.data:
                if item.get("agent"):
                    agents.append(item["agent"])
            return agents, None
        except Exception as e:
            logger.error(
                f"Error getting agents for skill {skill_id}: {e}", exc_info=True
            )
            return [], str(e)

    # --- Skill file CRUD ---

    @tracer.start_as_current_span("skill.get_skill_files")
    async def get_skill_files(
        self, skill_id: UUID
    ) -> tuple[List[SkillFileSummary], Optional[str]]:
        """Get all files for a skill (summaries without content, for file tree)."""
        skill_operations_counter.add(1, {"operation": "get_skill_files"})
        try:
            response = (
                self.supabase.table("organization_skill_files")
                .select("id, file_path, file_kind, content_hash")
                .eq("skill_id", str(skill_id))
                .order("file_path")
                .execute()
            )
            files = [SkillFileSummary(**item) for item in response.data]
            return files, None
        except Exception as e:
            logger.error(f"Error getting skill files {skill_id}: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("skill.get_skill_file_content")
    async def get_skill_file_content(
        self, skill_id: UUID, file_path: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Get a specific file's content by skill_id and file_path.

        Used by the load_skill_reference tool for progressive disclosure.
        """
        skill_operations_counter.add(1, {"operation": "get_skill_file_content"})
        try:
            response = (
                self.supabase.table("organization_skill_files")
                .select("content")
                .eq("skill_id", str(skill_id))
                .eq("file_path", file_path)
                .execute()
            )
            if not response.data:
                return None, f"File '{file_path}' not found in skill"
            return response.data[0]["content"], None
        except Exception as e:
            logger.error(f"Error getting skill file content: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.get_skill_file_content_by_slug")
    async def get_skill_file_content_by_slug(
        self, org_id: UUID, slug: str, file_path: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Get file content by org_id, skill slug, and file path.

        Used by the load_skill_reference worker tool.
        """
        skill_operations_counter.add(1, {"operation": "get_skill_file_content_by_slug"})
        try:
            # First get the skill ID
            skill_response = (
                self.supabase.table("organization_skills")
                .select("id")
                .eq("organization_id", str(org_id))
                .eq("slug", slug)
                .eq("is_active", True)
                .execute()
            )
            if not skill_response.data:
                return None, f"Skill '{slug}' not found or inactive"

            skill_id = skill_response.data[0]["id"]
            return await self.get_skill_file_content(skill_id, file_path)
        except Exception as e:
            logger.error(f"Error getting skill file by slug: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.create_skill_file")
    async def create_skill_file(
        self, skill_id: UUID, file_data: SkillFileCreate
    ) -> tuple[Optional[SkillFile], Optional[str]]:
        """Create a reference file within a skill."""
        skill_operations_counter.add(1, {"operation": "create_skill_file"})
        try:
            content_hash = _compute_content_hash(file_data.content)
            response = (
                self.supabase.table("organization_skill_files")
                .insert(
                    {
                        "skill_id": str(skill_id),
                        "file_path": file_data.file_path,
                        "content": file_data.content,
                        "file_kind": file_data.file_kind,
                        "content_hash": content_hash,
                    }
                )
                .execute()
            )
            if not response.data:
                return None, "Failed to create skill file"
            return SkillFile(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error creating skill file: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.update_skill_file")
    async def update_skill_file(
        self, file_id: UUID, file_data: SkillFileUpdate
    ) -> tuple[Optional[SkillFile], Optional[str]]:
        """Update a reference file's content and/or path."""
        skill_operations_counter.add(1, {"operation": "update_skill_file"})
        try:
            update_dict = {}
            if file_data.file_path is not None:
                update_dict["file_path"] = file_data.file_path
            if file_data.content is not None:
                update_dict["content"] = file_data.content
                update_dict["content_hash"] = _compute_content_hash(file_data.content)

            if not update_dict:
                return None, "No fields to update"

            response = (
                self.supabase.table("organization_skill_files")
                .update(update_dict)
                .eq("id", str(file_id))
                .execute()
            )
            if not response.data:
                return None, "File not found or update failed"
            return SkillFile(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating skill file: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.delete_skill_file")
    async def delete_skill_file(self, file_id: UUID) -> tuple[bool, Optional[str]]:
        """Delete a reference file."""
        skill_operations_counter.add(1, {"operation": "delete_skill_file"})
        try:
            response = (
                self.supabase.table("organization_skill_files")
                .delete()
                .eq("id", str(file_id))
                .execute()
            )
            if not response.data:
                return False, "File not found"
            return True, None
        except Exception as e:
            logger.error(f"Error deleting skill file: {e}", exc_info=True)
            return False, str(e)

    @tracer.start_as_current_span("skill.bulk_create_skill_files")
    async def bulk_create_skill_files(
        self, skill_id: UUID, files: List[SkillFileCreate]
    ) -> tuple[int, Optional[str]]:
        """Create multiple files for a skill (used during import)."""
        skill_operations_counter.add(1, {"operation": "bulk_create_skill_files"})
        try:
            rows = []
            for f in files:
                rows.append(
                    {
                        "skill_id": str(skill_id),
                        "file_path": f.file_path,
                        "content": f.content,
                        "file_kind": f.file_kind,
                        "content_hash": _compute_content_hash(f.content),
                    }
                )

            if not rows:
                return 0, None

            response = (
                self.supabase.table("organization_skill_files").insert(rows).execute()
            )
            return len(response.data), None
        except Exception as e:
            logger.error(f"Error bulk creating skill files: {e}", exc_info=True)
            return 0, str(e)

    # --- Seeding ---

    # ═════════════════════════════════════════════════════════════════════════
    # PLATFORM SKILL SEEDING (New)
    # ═════════════════════════════════════════════════════════════════════════

    @tracer.start_as_current_span("skill.seed_platform_skills")
    async def seed_platform_skills(
        self, *, prune_orphans: bool = False
    ) -> tuple[int, Optional[str]]:
        """Seed platform_skills table from code-defined templates.

        Uses content_hash to skip unchanged skills. No per-org seeding — orgs
        fork what they need. Normal runs never delete rows; callers must
        explicitly request orphan pruning.

        Args:
            prune_orphans: Delete platform-only rows whose slugs are absent
                from the source catalog. This is intended for an explicit,
                reviewed reset in non-production environments.

        Returns:
            Tuple of (skills created/updated count, error or None).
        """
        from src.voice_agents.skill_seeds import PLATFORM_SKILL_TEMPLATES

        skill_operations_counter.add(1, {"operation": "seed_platform_skills"})
        try:
            count = 0
            for seed in PLATFORM_SKILL_TEMPLATES:
                new_hash = _compute_content_hash(seed["content"])

                # Check if already exists by slug
                existing = (
                    self.supabase.table("platform_skills")
                    .select("id, content_hash, version")
                    .eq("slug", seed["slug"])
                    .execute()
                )

                if existing.data:
                    row = existing.data[0]
                    # Only update if content changed
                    if row.get("content_hash") != new_hash:
                        from datetime import date

                        today = date.today().strftime("%Y.%m.%d")
                        current_version = row.get("version") or "1970.01.01_0"
                        base, suffix = current_version.rsplit("_", 1)
                        if base == today:
                            new_version = f"{today}_{int(suffix) + 1}"
                        else:
                            new_version = f"{today}_1"

                        self.supabase.table("platform_skills").update(
                            {
                                "name": seed["name"],
                                "description": seed.get("description"),
                                "content": seed["content"],
                                "content_hash": new_hash,
                                "version": new_version,
                            }
                        ).eq("id", row["id"]).execute()
                        count += 1

                        # Update default files (delete old, insert new)
                        self.supabase.table("platform_skill_files").delete().eq(
                            "skill_id", row["id"]
                        ).execute()
                        for file_def in seed.get("default_files", []):
                            self.supabase.table("platform_skill_files").insert(
                                {
                                    "skill_id": row["id"],
                                    "file_path": file_def["file_path"],
                                    "content": file_def["content"],
                                    "file_kind": file_def.get("file_kind", "reference"),
                                    "content_hash": _compute_content_hash(
                                        file_def["content"]
                                    ),
                                }
                            ).execute()
                    continue

                # Create new platform skill
                from datetime import date

                today = date.today().strftime("%Y.%m.%d")
                version = f"{today}_1"

                # status defaults to 'active' in the DB; we do not pass it
                # explicitly so the seeder keeps working regardless of which
                # platform-skill status columns exist.
                response = (
                    self.supabase.table("platform_skills")
                    .insert(
                        {
                            "slug": seed["slug"],
                            "name": seed["name"],
                            "description": seed.get("description"),
                            "content": seed["content"],
                            "version": version,
                            "content_hash": new_hash,
                            "author": "Platform",
                        }
                    )
                    .execute()
                )

                if response.data:
                    skill_id = response.data[0]["id"]
                    for file_def in seed.get("default_files", []):
                        self.supabase.table("platform_skill_files").insert(
                            {
                                "skill_id": skill_id,
                                "file_path": file_def["file_path"],
                                "content": file_def["content"],
                                "file_kind": file_def.get("file_kind", "reference"),
                                "content_hash": _compute_content_hash(
                                    file_def["content"]
                                ),
                            }
                        ).execute()
                    count += 1

            orphan_count = 0
            if prune_orphans:
                orphan_count = await self._prune_orphan_platform_skills()

            logger.info(
                f"Seeded {count} platform skills; removed {orphan_count} orphan(s)"
            )
            return count, None
        except Exception as e:
            logger.error(f"Error seeding platform skills: {e}", exc_info=True)
            return 0, str(e)

    @tracer.start_as_current_span("skill.prune_orphan_platform_skills")
    async def _prune_orphan_platform_skills(self) -> int:
        """Delete platform_skills rows whose slugs aren't in PLATFORM_SKILL_TEMPLATES.

        Called only by an explicit, reviewed reset. Removing a slug from the
        seed list is treated as a deliberate removal from the platform
        library only when that reset is requested.

        Existing org forks are unaffected — they own their own content +
        files. The fork's ``source_skill_id`` becomes a dangling pointer,
        which the ``refresh_forked_skill`` and ``check_update_available``
        paths handle gracefully with a user-friendly message.

        Returns:
            Number of orphan rows deleted.
        """
        from src.voice_agents.skill_seeds import PLATFORM_SKILL_TEMPLATES

        seeded_slugs = {s["slug"] for s in PLATFORM_SKILL_TEMPLATES}
        existing_rows = (
            self.supabase.table("platform_skills").select("id, slug").execute()
        ).data or []
        orphan_count = 0
        for row in existing_rows:
            if row["slug"] not in seeded_slugs:
                self.supabase.table("platform_skills").delete().eq(
                    "id", row["id"]
                ).execute()
                orphan_count += 1
                logger.info(
                    f"Removed orphan platform skill '{row['slug']}' "
                    f"(no longer in PLATFORM_SKILL_TEMPLATES)"
                )
        return orphan_count

    # ═════════════════════════════════════════════════════════════════════════
    # PLATFORM SKILL CRUD (New)
    # ═════════════════════════════════════════════════════════════════════════

    @tracer.start_as_current_span("skill.list_platform_skills")
    async def list_platform_skills(
        self,
        statuses: Optional[List[PlatformSkillStatus]] = None,
    ) -> tuple[List[PlatformSkillSummary], Optional[str]]:
        """List platform skills filtered by status.

        Args:
            statuses: List of statuses to include. Defaults to ``[ACTIVE]``
                so org admins browsing/forking only see forkable skills.
                Platform admins may pass e.g.
                ``[ACTIVE, DEPRECATED]`` or ``[DELETED]`` (trash bin).

                An empty list is rejected — callers must explicitly opt-in
                to a non-default status set, which catches accidental
                "show nothing" calls. Unknown statuses are rejected.

        Returns:
            Tuple of (list of PlatformSkillSummary, error). Each summary
            includes ``status`` so admins can distinguish active/deprecated/
            deleted skills in the UI.
        """
        if statuses is None:
            statuses = [PlatformSkillStatus.ACTIVE]

        if not statuses:
            return [], "statuses must be a non-empty list"

        # Validate all values are known enum members
        invalid = [s for s in statuses if not isinstance(s, PlatformSkillStatus)]
        if invalid:
            valid = ", ".join(s.value for s in PlatformSkillStatus)
            return [], (f"Invalid status value(s): {invalid}. Must be one of: {valid}")

        try:
            status_values = [s.value for s in statuses]
            query = (
                self.supabase.table("platform_skills")
                .select("id, slug, name, description, version, status")
                .order("name")
                .in_("status", status_values)
            )
            response = query.execute()
            skills = [PlatformSkillSummary(**row) for row in response.data or []]
            return skills, None
        except Exception as e:
            logger.error(f"Error listing platform skills: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("skill.get_platform_skill_by_id")
    async def get_platform_skill_by_id(
        self, skill_id: UUID
    ) -> tuple[Optional[PlatformSkill], Optional[str]]:
        """Get a platform skill by ID with its files."""
        try:
            response = (
                self.supabase.table("platform_skills")
                .select("*, platform_skill_files(*)")
                .eq("id", str(skill_id))
                .single()
                .execute()
            )
            if not response.data:
                return None, "Platform skill not found"
            return PlatformSkill(**response.data), None
        except Exception as e:
            logger.error(f"Error getting platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.create_platform_skill")
    async def create_platform_skill(
        self, skill_data: PlatformSkillCreate
    ) -> tuple[Optional[PlatformSkill], Optional[str]]:
        """Create a new platform skill. Version auto-set to current date."""
        try:
            from datetime import date

            today = date.today().strftime("%Y.%m.%d")
            version = f"{today}_1"

            content_hash = _compute_content_hash(skill_data.content)
            # status defaults to 'active' in the DB; we deliberately do not
            # accept a status on create — DRAFT/publish will get a dedicated
            # endpoint when we add the draft UI.
            response = (
                self.supabase.table("platform_skills")
                .insert(
                    {
                        "slug": skill_data.slug,
                        "name": skill_data.name,
                        "description": skill_data.description,
                        "content": skill_data.content,
                        "version": version,
                        "content_hash": content_hash,
                        "author": skill_data.author,
                    }
                )
                .execute()
            )

            if not response.data:
                return None, "Failed to create platform skill"
            return PlatformSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error creating platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.update_platform_skill")
    async def update_platform_skill(
        self, skill_id: UUID, skill_data: PlatformSkillUpdate
    ) -> tuple[Optional[PlatformSkill], Optional[str]]:
        """Update a platform skill and bump version."""
        try:
            existing, err = await self.get_platform_skill_by_id(skill_id)
            if err or not existing:
                return None, err or "Skill not found"

            update_dict = {}
            if skill_data.name is not None:
                update_dict["name"] = skill_data.name
            if skill_data.description is not None:
                update_dict["description"] = skill_data.description
            if skill_data.content is not None:
                update_dict["content"] = skill_data.content
                update_dict["content_hash"] = _compute_content_hash(skill_data.content)
            # Status changes are NOT part of update_platform_skill — use the
            # dedicated transition endpoints (deprecate/reactivate/delete/restore).
            # This keeps the state machine explicit and prevents accidental
            # visibility flips during a content edit.

            # Auto-bump version on any content change
            if "content" in update_dict:
                from datetime import date

                today = date.today().strftime("%Y.%m.%d")
                current_version = existing.version or "1970.01.01_0"
                base, suffix = current_version.rsplit("_", 1)
                if base == today:
                    new_version = f"{today}_{int(suffix) + 1}"
                else:
                    new_version = f"{today}_1"
                update_dict["version"] = new_version

            if not update_dict:
                return existing, None

            response = (
                self.supabase.table("platform_skills")
                .update(update_dict)
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return None, "Update failed"
            return PlatformSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.delete_platform_skill")
    async def delete_platform_skill(self, skill_id: UUID) -> tuple[bool, Optional[str]]:
        """Soft-delete a platform skill (transition to DELETED).

        Allowed transitions: ACTIVE / DEPRECATED / DRAFT → DELETED.
        Already-DELETED skills return an error so accidental double-delete
        is impossible. Existing org forks keep working.

        Returns:
            Tuple of (success, error). ``success=False`` and ``error`` set
            when the skill is missing or already deleted.
        """
        try:
            existing, err = await self.get_platform_skill_by_id(skill_id)
            if err or not existing:
                return False, err or "Skill not found"
            if existing.status == PlatformSkillStatus.DELETED:
                return False, "Skill is already deleted"
            self.supabase.table("platform_skills").update(
                {"status": PlatformSkillStatus.DELETED.value}
            ).eq("id", str(skill_id)).execute()
            return True, None
        except Exception as e:
            logger.error(f"Error soft-deleting platform skill: {e}", exc_info=True)
            return False, str(e)

    @tracer.start_as_current_span("skill.restore_platform_skill")
    async def restore_platform_skill(
        self, skill_id: UUID
    ) -> tuple[Optional[PlatformSkill], Optional[str]]:
        """Restore a soft-deleted platform skill (DELETED → ACTIVE).

        Only skills in DELETED state can be restored. Restored skills always
        land on ACTIVE — admins can re-deprecate via the deprecate endpoint
        if desired. Restoring an already-active/deprecated/draft skill
        returns an error to keep the state machine explicit.
        """
        try:
            existing, err = await self.get_platform_skill_by_id(skill_id)
            if err or not existing:
                return None, err or "Platform skill not found"
            if existing.status != PlatformSkillStatus.DELETED:
                return None, (
                    f"Cannot restore skill in state '{existing.status.value}': "
                    "only deleted skills can be restored"
                )
            response = (
                self.supabase.table("platform_skills")
                .update({"status": PlatformSkillStatus.ACTIVE.value})
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return None, "Platform skill not found"
            return PlatformSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error restoring platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.deprecate_platform_skill")
    async def deprecate_platform_skill(
        self, skill_id: UUID
    ) -> tuple[Optional[PlatformSkill], Optional[str]]:
        """Deprecate a platform skill (ACTIVE → DEPRECATED).

        Only ACTIVE skills can be deprecated; DRAFT/DEPRECATED/DELETED
        states return an error so admins use the explicit right endpoint
        (publish for draft, restore for deleted). Deprecated skills are
        hidden from org admins in the default list but remain visible to
        platform admins and keep all existing org forks working.
        """
        try:
            existing, err = await self.get_platform_skill_by_id(skill_id)
            if err or not existing:
                return None, err or "Skill not found"
            if existing.status != PlatformSkillStatus.ACTIVE:
                return None, (
                    f"Cannot deprecate skill in state '{existing.status.value}': "
                    "only active skills can be deprecated"
                )
            response = (
                self.supabase.table("platform_skills")
                .update({"status": PlatformSkillStatus.DEPRECATED.value})
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return None, "Platform skill not found"
            return PlatformSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error deprecating platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.reactivate_platform_skill")
    async def reactivate_platform_skill(
        self, skill_id: UUID
    ) -> tuple[Optional[PlatformSkill], Optional[str]]:
        """Reactivate a deprecated platform skill (DEPRECATED → ACTIVE).

        Only DEPRECATED skills can be reactivated; ACTIVE/DRAFT/DELETED
        states return an error so admins use the explicit right endpoint.
        """
        try:
            existing, err = await self.get_platform_skill_by_id(skill_id)
            if err or not existing:
                return None, err or "Skill not found"
            if existing.status != PlatformSkillStatus.DEPRECATED:
                return None, (
                    f"Cannot reactivate skill in state '{existing.status.value}': "
                    "only deprecated skills can be reactivated"
                )
            response = (
                self.supabase.table("platform_skills")
                .update({"status": PlatformSkillStatus.ACTIVE.value})
                .eq("id", str(skill_id))
                .execute()
            )
            if not response.data:
                return None, "Platform skill not found"
            return PlatformSkill(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error reactivating platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.list_platform_skill_files")
    async def list_platform_skill_files(
        self, skill_id: UUID
    ) -> tuple[List[PlatformSkillFileSummary], Optional[str]]:
        """List files for a platform skill."""
        try:
            response = (
                self.supabase.table("platform_skill_files")
                .select("id, file_path, file_kind, content_hash")
                .eq("skill_id", str(skill_id))
                .execute()
            )
            files = [PlatformSkillFileSummary(**row) for row in response.data or []]
            return files, None
        except Exception as e:
            logger.error(f"Error listing platform skill files: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("skill.get_platform_skill_file")
    async def get_platform_skill_file(
        self, file_id: UUID
    ) -> tuple[Optional[PlatformSkillFile], Optional[str]]:
        """Get a platform skill file by ID."""
        try:
            response = (
                self.supabase.table("platform_skill_files")
                .select("*")
                .eq("id", str(file_id))
                .single()
                .execute()
            )
            if not response.data:
                return None, "File not found"
            return PlatformSkillFile(**response.data), None
        except Exception as e:
            logger.error(f"Error getting platform skill file: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.create_platform_skill_file")
    async def create_platform_skill_file(
        self, skill_id: UUID, file_data: PlatformSkillFileCreate
    ) -> tuple[Optional[PlatformSkillFile], Optional[str]]:
        """Create a file for a platform skill."""
        try:
            content_hash = _compute_content_hash(file_data.content)
            response = (
                self.supabase.table("platform_skill_files")
                .insert(
                    {
                        "skill_id": str(skill_id),
                        "file_path": file_data.file_path,
                        "content": file_data.content,
                        "file_kind": file_data.file_kind,
                        "content_hash": content_hash,
                    }
                )
                .execute()
            )
            if not response.data:
                return None, "Failed to create file"
            return PlatformSkillFile(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error creating platform skill file: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.update_platform_skill_file")
    async def update_platform_skill_file(
        self, file_id: UUID, file_data: PlatformSkillFileCreate
    ) -> tuple[Optional[PlatformSkillFile], Optional[str]]:
        """Update a platform skill file."""
        try:
            update_dict = {
                "file_path": file_data.file_path,
                "content": file_data.content,
                "file_kind": file_data.file_kind,
                "content_hash": _compute_content_hash(file_data.content),
            }
            response = (
                self.supabase.table("platform_skill_files")
                .update(update_dict)
                .eq("id", str(file_id))
                .execute()
            )
            if not response.data:
                return None, "File not found or update failed"
            return PlatformSkillFile(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating platform skill file: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.delete_platform_skill_file")
    async def delete_platform_skill_file(
        self, file_id: UUID
    ) -> tuple[bool, Optional[str]]:
        """Delete a platform skill file."""
        try:
            self.supabase.table("platform_skill_files").delete().eq(
                "id", str(file_id)
            ).execute()
            return True, None
        except Exception as e:
            logger.error(f"Error deleting platform skill file: {e}", exc_info=True)
            return False, str(e)

    # ═════════════════════════════════════════════════════════════════════════
    # FORK / REFRESH (New)
    # ═════════════════════════════════════════════════════════════════════════

    @tracer.start_as_current_span("skill.fork_platform_skill")
    async def fork_platform_skill(
        self,
        org_id: UUID,
        platform_skill_id: UUID,
        custom_name: Optional[str] = None,
        custom_slug: Optional[str] = None,
    ) -> tuple[Optional[OrganizationSkill], Optional[str]]:
        """Fork a platform skill into an org's library. Copies all files."""
        try:
            # Get platform skill with files
            response = (
                self.supabase.table("platform_skills")
                .select("*, platform_skill_files(*)")
                .eq("id", str(platform_skill_id))
                .single()
                .execute()
            )
            if not response.data:
                return None, "Platform skill not found"

            platform_skill = response.data
            name = custom_name or f"{platform_skill['name']} (Copy)"
            slug = custom_slug or f"{platform_skill['slug']}-copy"

            # Create org skill record
            org_skill = {
                "organization_id": str(org_id),
                "slug": slug,
                "name": name,
                "description": platform_skill.get("description"),
                "content": platform_skill["content"],
                "category": "custom",
                "is_active": True,
                "version": platform_skill.get("version"),
                "author": platform_skill.get("author"),
                "content_hash": platform_skill.get("content_hash"),
                "source_skill_id": str(platform_skill_id),
                "source_version": platform_skill.get("version"),
                "is_visible": True,
            }

            skill_resp = (
                self.supabase.table("organization_skills").insert(org_skill).execute()
            )
            if not skill_resp.data:
                return None, "Failed to create forked skill"

            new_skill_id = skill_resp.data[0]["id"]

            # Copy all files
            files = platform_skill.get("platform_skill_files", [])
            for file in files:
                self.supabase.table("organization_skill_files").insert(
                    {
                        "skill_id": new_skill_id,
                        "file_path": file["file_path"],
                        "content": file["content"],
                        "file_kind": file["file_kind"],
                        "content_hash": file.get("content_hash"),
                    }
                ).execute()

            return OrganizationSkill(**skill_resp.data[0]), None
        except Exception as e:
            logger.error(f"Error forking platform skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.refresh_forked_skill")
    async def refresh_forked_skill(
        self, org_skill_id: UUID, user_id: UUID
    ) -> tuple[Optional[OrganizationSkill], Optional[str]]:
        """Refresh a forked skill from its platform source. Replaces ALL files."""
        try:
            # Get org skill
            org_skill_resp = (
                self.supabase.table("organization_skills")
                .select("*, organization_skill_files(*)")
                .eq("id", str(org_skill_id))
                .single()
                .execute()
            )
            if not org_skill_resp.data:
                return None, "Org skill not found"

            org_skill = org_skill_resp.data
            source_skill_id = org_skill.get("source_skill_id")
            if not source_skill_id:
                return None, "This skill was not forked from a platform skill"

            # Get current platform skill. If it's gone (e.g. removed from
            # PLATFORM_SKILL_TEMPLATES and cleaned up by the seeder), we
            # surface a clear, actionable message rather than a generic
            # 404 — the fork itself is fine, only the refresh target is
            # unavailable.
            platform_resp = (
                self.supabase.table("platform_skills")
                .select("*, platform_skill_files(*)")
                .eq("id", source_skill_id)
                .single()
                .execute()
            )
            if not platform_resp.data:
                return None, (
                    "The base skill this fork was created from is no longer "
                    "available. Your fork is unaffected — you can keep using "
                    "it as-is. To get updates from a current platform skill, "
                    "fork the new version from the Platform Skills library."
                )

            platform_skill = platform_resp.data
            old_version = org_skill.get("source_version")
            new_version = platform_skill.get("version")

            if old_version == new_version:
                return None, f"Already up to date ({old_version})"

            # Replace ALL content
            self.supabase.table("organization_skills").update(
                {
                    "content": platform_skill["content"],
                    "content_hash": platform_skill.get("content_hash"),
                    "source_version": new_version,
                    "name": platform_skill[
                        "name"
                    ],  # Also update name in case it changed
                    "description": platform_skill.get("description"),
                }
            ).eq("id", str(org_skill_id)).execute()

            # Delete ALL existing org files and replace with platform's latest
            self.supabase.table("organization_skill_files").delete().eq(
                "skill_id", str(org_skill_id)
            ).execute()

            files = platform_skill.get("platform_skill_files", [])
            for file in files:
                self.supabase.table("organization_skill_files").insert(
                    {
                        "skill_id": str(org_skill_id),
                        "file_path": file["file_path"],
                        "content": file["content"],
                        "file_kind": file["file_kind"],
                        "content_hash": file.get("content_hash"),
                    }
                ).execute()

            # Log the update
            self.supabase.table("skill_update_logs").insert(
                {
                    "org_skill_id": str(org_skill_id),
                    "old_source_version": old_version,
                    "new_source_version": new_version,
                    "performed_by": str(user_id),
                }
            ).execute()

            # Return updated skill
            updated_resp = (
                self.supabase.table("organization_skills")
                .select("*")
                .eq("id", str(org_skill_id))
                .single()
                .execute()
            )
            return OrganizationSkill(**updated_resp.data), None
        except Exception as e:
            logger.error(f"Error refreshing forked skill: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("skill.check_update_available")
    async def check_update_available(
        self, org_skill_id: UUID
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Check if a forked skill has an update available.

        Returns:
            Tuple of (update_available: bool, latest_version: str or None, error: str or None)
        """
        try:
            org_skill_resp = (
                self.supabase.table("organization_skills")
                .select("source_skill_id, source_version")
                .eq("id", str(org_skill_id))
                .single()
                .execute()
            )
            if not org_skill_resp.data:
                return False, None, "Org skill not found"

            org_skill = org_skill_resp.data
            source_skill_id = org_skill.get("source_skill_id")
            if not source_skill_id:
                return False, None, None  # Not forked

            platform_resp = (
                self.supabase.table("platform_skills")
                .select("version")
                .eq("id", source_skill_id)
                .single()
                .execute()
            )
            if not platform_resp.data:
                return (
                    False,
                    None,
                    (
                        "The base skill this fork was created from is no longer "
                        "available. Updates cannot be checked."
                    ),
                )

            latest_version = platform_resp.data.get("version")
            current_version = org_skill.get("source_version")

            return latest_version != current_version, latest_version, None
        except Exception as e:
            logger.error(f"Error checking update: {e}", exc_info=True)
            return False, None, str(e)


skill_service = SkillService()
