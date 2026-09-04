"""Attachment configuration health for org-facing tool surfaces.

Mirrors the preset ``is_preset_ready`` idea for native tools: the same
check the voice runtime would fail on is computed up front, so agent
tool cards render red/yellow *before* a call exposes the gap.
Authentication state stays separate (see ``validate_token_status``);
this module only answers "is the stored configuration complete?".
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def check_tool_configuration(tool_name: Optional[str], config: Any | None) -> list[str]:
    """List missing configuration pieces for one attached tool.

    Args:
        tool_name: Registry key (``platform_tools.name``).
        config: Stored public attachment config (dict, model, or None).

    Returns:
        Human-readable issue strings, empty when complete, unknown, or
        when the stored payload cannot even be validated (an invalid
        stored payload is itself reported as one issue).
    """
    from shared.voice_agents.tools.base.platform_tool_registry import (
        platform_tool_registry,
    )

    if not tool_name:
        return []
    if platform_tool_registry.get_tool_class(tool_name) is None:
        platform_tool_registry.register_tools_from_package(
            "shared.voice_agents.tools.implementations"
        )
    tool_class = platform_tool_registry.get_tool_class(tool_name)
    if tool_class is None:
        return []
    payload = config if isinstance(config, dict) else {}
    try:
        tool = tool_class(config=payload, sensitive_config={})
    except Exception as exc:  # noqa: BLE001 - values stay out of logs
        logger.warning(
            "Stored configuration failed validation tool=%s error_type=%s",
            tool_name,
            type(exc).__name__,
        )
        return ["stored configuration is invalid and must be re-saved"]
    try:
        return list(tool.check_configuration())
    except Exception:  # noqa: BLE001 - a broken hook must not break listing
        logger.exception("Configuration check failed tool=%s", tool_name)
        return []
