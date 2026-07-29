"""Backward-compat shim for the Gemini realtime model configuration.

The implementation has moved to
:mod:`speech_providers.realtime.provider` (parameterized by
:class:`shared.voice_agents.speech_config.RealtimeSpeechConfig`) as part of the
Phase 1 refactor that introduced the modular speech-engine seam. This module
re-exports the public functions and constants under their old names so existing
importers — notably the legacy test suite
``worker/tests/test_realtime_config.py`` — keep working unchanged.

New code should import from :mod:`speech_providers.realtime` (builders) and
:mod:`shared.voice_agents.speech_config` (config models) directly.
"""

from speech_providers.realtime.provider import (
    ENDPOINTING_PREFIX_PADDING_MS,
    ENDPOINTING_SILENCE_DURATION_MS,
    GEMINI_REALTIME_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_VOICE,
    build_realtime_model,
    build_realtime_model_config,
)

__all__ = [
    "GEMINI_REALTIME_MODEL",
    "GEMINI_TEMPERATURE",
    "GEMINI_VOICE",
    "ENDPOINTING_SILENCE_DURATION_MS",
    "ENDPOINTING_PREFIX_PADDING_MS",
    "build_realtime_model_config",
    "build_realtime_model",
]
