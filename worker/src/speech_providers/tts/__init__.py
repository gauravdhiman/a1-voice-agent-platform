"""TTS (text-to-speech) pipeline providers.

Re-exports the per-provider TTS builders. Phase 2 ships Cartesia (direct);
Phase 2b adds LiveKit Inference (single LiveKit Cloud auth, many models).
Additional providers (ElevenLabs, OpenAI TTS, a local piper adapter) are added
as a new module + a branch in :mod:`speech_providers.registry`.
"""

from speech_providers.tts.cartesia import build_cartesia_tts, build_cartesia_tts_config
from speech_providers.tts.livekit_inference import (
    build_livekit_inference_tts,
    build_livekit_inference_tts_config,
)

__all__ = [
    "build_cartesia_tts_config",
    "build_cartesia_tts",
    "build_livekit_inference_tts_config",
    "build_livekit_inference_tts",
]
