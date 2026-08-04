"""TTS (text-to-speech) pipeline providers.

Re-exports the per-provider TTS builders. Phase 2 ships Cartesia (direct).
Additional providers (ElevenLabs, OpenAI TTS, a local piper adapter) are added
as a new module + a branch in :mod:`speech_providers.registry`.
"""

from speech_providers.tts.cartesia import build_cartesia_tts, build_cartesia_tts_config

__all__ = [
    "build_cartesia_tts_config",
    "build_cartesia_tts",
]
