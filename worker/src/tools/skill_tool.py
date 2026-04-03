"""
Skill loading tool for progressive skill disclosure.

This tool is registered with the LLM and allows it to load full skill
content on-demand during a conversation. Only skill metadata (name +
description) is in the system prompt; the LLM calls this tool when it
needs the actual procedures.

NOTE: This tool lives in worker/src/tools/ (not shared/voice_agents/tools/)
because it's a platform-native tool that is automatically registered when
an agent has skills — unlike Gmail/Calendar tools which are user-configurable
via OAuth and live in the shared tools layer. This tool has no user config;
it's tightly coupled to the worker's execution context (org_id, skill_service).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_load_skill_function(org_id: str, skill_service):
    """Create a load_skill function bound to a specific org and skill service.

    Args:
        org_id: Organization ID for scoping skill lookup.
        skill_service: SkillService instance for fetching content.

    Returns:
        An async function suitable for use as a LiveKit function_tool.
    """

    async def load_skill(skill_slug: str) -> str:
        """Load a skill's full procedures and knowledge.

        Call this tool when the conversation requires a specific procedure
        from your available skills. The skill content will be loaded and
        returned so you can follow its instructions.

        Args:
            skill_slug: The slug identifier of the skill to load
                        (from the Available Skills list in your instructions).

        Returns:
            The full skill content in markdown format with detailed procedures.
        """
        try:
            from uuid import UUID

            content, error = await skill_service.get_skill_content_by_slug(
                UUID(org_id), skill_slug
            )
            if error:
                logger.warning(f"Skill '{skill_slug}' not found: {error}")
                return f"Skill '{skill_slug}' is not available. Please continue without it."
            logger.info(f"Loaded skill '{skill_slug}' for org {org_id}")
            return content
        except Exception as e:
            logger.error(f"Error loading skill '{skill_slug}': {e}", exc_info=True)
            return f"Unable to load skill '{skill_slug}' at this time. Please continue without it."

    return load_skill
