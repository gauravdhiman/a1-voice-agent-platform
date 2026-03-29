"""Service layer for voice templates."""

import logging
from typing import Optional
from uuid import UUID

from shared.config import supabase_config
from src.voice_templates.models import VoiceTemplate

logger = logging.getLogger(__name__)


class VoiceTemplateService:
    @property
    def supabase(self):
        if not supabase_config.is_configured():
            raise ValueError("Supabase is not configured.")
        return supabase_config.client

    async def list_templates(self, industry: Optional[str] = None) -> tuple[list[VoiceTemplate], Optional[str]]:
        """List all active voice templates, optionally filtered by industry."""
        try:
            query = self.supabase.table("voice_templates").select("*").eq("is_active", True)
            if industry:
                query = query.eq("industry", industry)
            response = query.order("name").execute()
            templates = [VoiceTemplate(**row) for row in response.data]
            return templates, None
        except Exception as e:
            logger.error(f"Error listing voice templates: {e}", exc_info=True)
            return [], str(e)

    async def get_template_by_id(self, template_id: UUID) -> tuple[Optional[VoiceTemplate], Optional[str]]:
        """Get a voice template by ID."""
        try:
            response = (
                self.supabase.table("voice_templates")
                .select("*")
                .eq("id", str(template_id))
                .eq("is_active", True)
                .execute()
            )
            if not response.data:
                return None, "Voice template not found"
            return VoiceTemplate(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error getting voice template {template_id}: {e}", exc_info=True)
            return None, str(e)


voice_template_service = VoiceTemplateService()
