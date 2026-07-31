"""STT (speech-to-text) pipeline providers.

Re-exports the per-provider STT builders. Phase 2 ships Deepgram (direct);
Phase 2b adds LiveKit Inference (single LiveKit Cloud auth, many models).
Additional providers (e.g. a local AssemblyAI/whisper adapter) are added as a
new module + a branch in :mod:`speech_providers.registry`.
"""

from speech_providers.stt.deepgram import build_deepgram_stt, build_deepgram_stt_config
from speech_providers.stt.livekit_inference import (
    build_livekit_inference_stt,
    build_livekit_inference_stt_config,
)

__all__ = [
    "build_deepgram_stt_config",
    "build_deepgram_stt",
    "build_livekit_inference_stt_config",
    "build_livekit_inference_stt",
]
