"""VAD (voice-activity-detection) pipeline providers.

Re-exports the per-provider VAD builders. Phase 2 ships Silero (local, CPU,
offline ONNX). Additional providers (e.g. a WebRTC VAD adapter) are added as a
new module + a branch in :mod:`speech_providers.registry`.
"""

from speech_providers.vad.silero import build_silero_vad, build_silero_vad_config

__all__ = ["build_silero_vad_config", "build_silero_vad"]
