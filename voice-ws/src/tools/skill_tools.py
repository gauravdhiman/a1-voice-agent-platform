"""Pipecat handlers for progressively disclosing agent skill content.

Only skill summaries are included in the system instruction. Gemini can call
these handlers when it needs a full skill or a referenced file, keeping normal
voice-session prompts compact while retaining detailed procedures on demand.
"""

from __future__ import annotations

import logging
from typing import Any, Callable
from uuid import UUID

logger = logging.getLogger(__name__)


def create_load_skill_function(org_id: str, skill_service: Any) -> Callable[..., Any]:
    """Create a Pipecat-compatible handler that fetches one full skill.

    Args:
        org_id: Organization UUID used to scope every skill lookup.
        skill_service: Service exposing ``get_skill_content_by_slug``.

    Returns:
        An async callable accepting ``skill_slug`` and returning markdown skill
        content or a model-safe explanatory message.
    """

    async def load_skill(skill_slug: str) -> str:
        """Load a skill's complete procedures for the current organization."""
        try:
            content, error = await skill_service.get_skill_content_by_slug(
                UUID(org_id), skill_slug
            )
            if error or content is None:
                logger.warning("Skill '%s' is unavailable: %s", skill_slug, error)
                return f"Skill '{skill_slug}' is not available. Please continue without it."
            return content
        except Exception as exc:  # noqa: BLE001 - tool errors must reach the model safely
            logger.exception("Failed to load skill '%s': %s", skill_slug, exc)
            return f"Unable to load skill '{skill_slug}' at this time. Please continue without it."

    return load_skill


def create_load_skill_reference_function(
    org_id: str, skill_service: Any
) -> Callable[..., Any]:
    """Create a Pipecat-compatible handler that fetches a skill reference file.

    Args:
        org_id: Organization UUID used to scope every skill lookup.
        skill_service: Service exposing ``get_skill_file_content_by_slug``.

    Returns:
        An async callable accepting ``skill_slug`` and ``file_path`` and
        returning the file content or a model-safe explanatory message.
    """

    async def load_skill_reference(skill_slug: str, file_path: str) -> str:
        """Load a reference file owned by an already available skill."""
        try:
            content, error = await skill_service.get_skill_file_content_by_slug(
                UUID(org_id), skill_slug, file_path
            )
            if error or content is None:
                logger.warning(
                    "Skill file '%s' in '%s' is unavailable: %s",
                    file_path,
                    skill_slug,
                    error,
                )
                return (
                    f"File '{file_path}' is not available in skill '{skill_slug}'. "
                    "Please continue without it."
                )
            return content
        except Exception as exc:  # noqa: BLE001 - tool errors must reach the model safely
            logger.exception(
                "Failed to load skill reference '%s/%s': %s",
                skill_slug,
                file_path,
                exc,
            )
            return (
                f"Unable to load file '{file_path}' from skill '{skill_slug}' "
                "at this time. Please continue without it."
            )

    return load_skill_reference
