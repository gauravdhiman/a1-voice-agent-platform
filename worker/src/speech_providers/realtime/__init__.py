"""Realtime (end-to-end speech) engine provider.

Re-exports the realtime model builder. See :mod:`speech_providers.realtime.provider`
for the tuning rationale and the config-driven builder API.
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
