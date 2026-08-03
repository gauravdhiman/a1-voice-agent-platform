"""Resolve an agent's SpeechConfig from its preset (shared by worker + voice-ws).

Fallback chain (a misconfigured preset never breaks a live call):

1. Explicit ``preset_id``, loadable + parseable → that preset's config
2. Explicit ``preset_id`` missing/unparseable → hardcoded realtime default
3. No ``preset_id`` → system default preset (``is_default``), else realtime
"""

from __future__ import annotations

import logging
from typing import Any, Union
from uuid import UUID

from shared.voice_agents.preset_service import preset_service
from shared.voice_agents.speech_config import (
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    default_realtime_config,
    parse_speech_config,
)

logger = logging.getLogger(__name__)

SpeechConfigT = Union[RealtimeSpeechConfig, PipelineSpeechConfig]


async def resolve_speech_config_for_agent(
    voice_agent: Any,
    agent_id: str | UUID,
) -> SpeechConfigT:
    """Resolve the SpeechConfig for a call from the agent's preset.

    Args:
        voice_agent: Voice-agent row/model exposing optional ``preset_id``.
        agent_id: Agent id for log lines.

    Returns:
        A concrete SpeechConfig; always the hardcoded realtime default on any
        failure in the chain.
    """
    agent_id_str = str(agent_id)
    preset_id = getattr(voice_agent, "preset_id", None)

    if preset_id:
        preset, preset_error = await preset_service.get_preset_by_id(preset_id)
        if preset_error:
            logger.error(
                "Agent %s: error loading preset %s: %s; falling back to realtime default.",
                agent_id_str,
                preset_id,
                preset_error,
            )
            return default_realtime_config()
        if preset is None:
            logger.error(
                "Agent %s: preset %s not found (deleted?); falling back to realtime default.",
                agent_id_str,
                preset_id,
            )
            return default_realtime_config()
        try:
            return parse_speech_config(preset.config)
        except Exception as cfg_err:  # noqa: BLE001 — graceful degrade
            logger.error(
                "Agent %s: preset %s has an unparseable config (%s); "
                "falling back to realtime default.",
                agent_id_str,
                preset_id,
                cfg_err,
            )
            return default_realtime_config()

    default_preset, default_error = await preset_service.get_default_preset()
    if default_error:
        logger.error(
            "Agent %s: error loading the system default preset: %s; "
            "falling back to realtime default.",
            agent_id_str,
            default_error,
        )
        return default_realtime_config()
    if default_preset is None:
        return default_realtime_config()
    try:
        return parse_speech_config(default_preset.config)
    except Exception as cfg_err:  # noqa: BLE001
        logger.error(
            "Agent %s: system default preset has an unparseable config (%s); "
            "falling back to realtime default.",
            agent_id_str,
            cfg_err,
        )
        return default_realtime_config()
