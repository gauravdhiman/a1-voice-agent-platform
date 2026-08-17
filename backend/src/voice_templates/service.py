"""Service layer for voice templates."""

import logging
from typing import Optional
from uuid import UUID

from shared.config import supabase_config
from src.voice_templates.models import (
    VoiceTemplate,
    VoiceTemplateCreate,
    VoiceTemplateUpdate,
)

logger = logging.getLogger(__name__)


class VoiceTemplateService:
    @property
    def supabase(self):
        if not supabase_config.is_configured():
            raise ValueError("Supabase is not configured.")
        return supabase_config.client

    async def list_templates(
        self,
        industry: Optional[str] = None,
        include_inactive: bool = False,
    ) -> tuple[list[VoiceTemplate], Optional[str]]:
        """List voice templates, optionally including inactive admin rows.

        Args:
            industry: Optional industry filter used by the agent template picker.
            include_inactive: Whether to include inactive rows for admins.

        Returns:
            A tuple containing templates and an optional error message.
        """
        try:
            query = self.supabase.table("voice_templates").select("*")
            if not include_inactive:
                query = query.eq("is_active", True)
            if industry:
                query = query.eq("industry", industry)
            response = query.order("name").execute()
            templates = [VoiceTemplate(**row) for row in response.data]
            return templates, None
        except Exception as e:
            logger.error(f"Error listing voice templates: {e}", exc_info=True)
            return [], str(e)

    async def get_template_by_id(
        self,
        template_id: UUID,
        include_inactive: bool = False,
    ) -> tuple[Optional[VoiceTemplate], Optional[str]]:
        """Get a voice template by ID, hiding inactive rows from public users."""
        try:
            query = (
                self.supabase.table("voice_templates")
                .select("*")
                .eq("id", str(template_id))
            )
            if not include_inactive:
                query = query.eq("is_active", True)
            response = query.execute()
            if not response.data:
                return None, "Voice template not found"
            return VoiceTemplate(**response.data[0]), None
        except Exception as e:
            logger.error(
                f"Error getting voice template {template_id}: {e}", exc_info=True
            )
            return None, str(e)

    async def create_template(
        self,
        data: VoiceTemplateCreate,
    ) -> tuple[Optional[VoiceTemplate], Optional[str]]:
        """Create a platform-managed voice template.

        Args:
            data: Validated template metadata and markdown-capable text fields.

        Returns:
            The created template or an error message.
        """
        try:
            response = (
                self.supabase.table("voice_templates")
                .insert(data.model_dump(mode="json"))
                .execute()
            )
            if not response.data:
                return None, "Failed to create voice template"
            return VoiceTemplate(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error creating voice template: {e}", exc_info=True)
            return None, str(e)

    async def update_template(
        self,
        template_id: UUID,
        data: VoiceTemplateUpdate,
    ) -> tuple[Optional[VoiceTemplate], Optional[str]]:
        """Update a platform-managed voice template by ID."""
        try:
            response = (
                self.supabase.table("voice_templates")
                .update(data.model_dump(exclude_unset=True, mode="json"))
                .eq("id", str(template_id))
                .execute()
            )
            if not response.data:
                return None, "Voice template not found"
            return VoiceTemplate(**response.data[0]), None
        except Exception as e:
            logger.error(
                f"Error updating voice template {template_id}: {e}", exc_info=True
            )
            return None, str(e)

    async def delete_template(
        self,
        template_id: UUID,
    ) -> tuple[Optional[bool], Optional[str]]:
        """Permanently delete a platform-managed voice template by ID."""
        try:
            exists = (
                self.supabase.table("voice_templates")
                .select("id")
                .eq("id", str(template_id))
                .execute()
            )
            if not exists.data:
                return None, "Voice template not found"
            self.supabase.table("voice_templates").delete().eq(
                "id", str(template_id)
            ).execute()
            return True, None
        except Exception as e:
            logger.error(
                f"Error deleting voice template {template_id}: {e}", exc_info=True
            )
            return None, str(e)


voice_template_service = VoiceTemplateService()
