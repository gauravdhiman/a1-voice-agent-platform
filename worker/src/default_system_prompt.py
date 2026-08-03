"""Backward-compatible worker export of the shared voice system prompt."""

from shared.voice_agents.default_voice_rules import DEFAULT_VOICE_SYSTEM_PROMPT

default_system_prompt = DEFAULT_VOICE_SYSTEM_PROMPT

__all__ = ["DEFAULT_VOICE_SYSTEM_PROMPT", "default_system_prompt"]
