"""Speech provider factory registry.

Maps a :class:`shared.voice_agents.speech_config.SpeechConfig` to the concrete
LiveKit plugin instance(s) the session needs — the modular, swappable core of
the voice engine. Modeled on HuggingFace's ``speech-to-speech``
``get_stt_handler`` / ``get_llm_handler`` / ``get_tts_handler`` factory pattern,
but each builder returns a LiveKit plugin instance (not a custom handler), so
the session stays on LiveKit's asyncio runtime.

Two engine modes dispatch here:

- **realtime** — returns :class:`RealtimeComponents` carrying a single
  ``RealtimeModel`` (passed as ``llm=`` to ``AgentSession``). Wired in Phase 1.
- **pipeline** — returns :class:`PipelineComponents` carrying the STT/LLM/TTS/
  VAD/turn-detection plugins. Raises ``NotImplementedError`` in Phase 1; wired
  in Phase 2 when the per-stage factories (``stt/``, ``llm/``, ``tts/``, etc.)
  are added.

The api-key map (``api_keys``) is per-provider: ``{"google": ..., "openai": ...}``
etc. The realtime branch reads ``api_keys["google"]``; pipeline branches will
read the key matching each stage's provider. This is the seam Phase 3 formalizes
in a dedicated ``key_resolver``; for now the worker resolves the Google key and
passes it in.
"""

from dataclasses import dataclass
from typing import Any, Union

from speech_providers.realtime.provider import build_realtime_model

from shared.voice_agents.speech_config import PipelineSpeechConfig, RealtimeSpeechConfig


@dataclass
class RealtimeComponents:
    """Session components for the realtime (end-to-end) engine.

    A single RealtimeModel handles STT + LLM + TTS; it is passed as ``llm=`` to
    ``AgentSession``.

    Attributes:
        llm: The configured Gemini ``RealtimeModel`` (not yet connected — the
            WebSocket opens on session start).
    """

    llm: Any


@dataclass
class PipelineComponents:
    """Session components for the pipeline engine.

    Each stage is an independently-configured LiveKit plugin. ``vad`` and
    ``turn_detection`` may be ``None`` (LiveKit applies defaults).

    Attributes:
        stt: Speech-to-text plugin.
        llm: Language model plugin.
        tts: Text-to-speech plugin.
        vad: Voice-activity-detection plugin (optional).
        turn_detection: Turn-detection plugin (optional).
    """

    stt: Any
    llm: Any
    tts: Any
    vad: Any = None
    turn_detection: Any = None


SessionComponents = Union[RealtimeComponents, PipelineComponents]
"""Union of the two engine component bundles. ``session_builder`` dispatches on
the concrete type when constructing the ``AgentSession``."""


def build_session_components(
    speech_config: Union[RealtimeSpeechConfig, PipelineSpeechConfig],
    api_keys: dict[str, str],
) -> SessionComponents:
    """Build the LiveKit session components for a speech config.

    Args:
        speech_config: The agent's speech config (realtime or pipeline).
        api_keys: Per-provider API key map, e.g. ``{"google": "<key>"}``. The
            realtime branch requires a ``"google"`` entry.

    Returns:
        RealtimeComponents for a realtime config; PipelineComponents for a
        pipeline config (Phase 2).

    Raises:
        ValueError: If a realtime config is given but no ``"google"`` key is
            present in ``api_keys``.
        NotImplementedError: If a pipeline config is given (Phase 2 wires the
            pipeline factories).

    Example:
        ```python
        comps = build_session_components(
            default_realtime_config(), api_keys={"google": api_key}
        )
        # comps.llm is a RealtimeModel
        ```
    """
    if isinstance(speech_config, RealtimeSpeechConfig):
        api_key = api_keys.get("google")
        if not api_key:
            raise ValueError(
                "Realtime engine requires a 'google' API key in api_keys; "
                "got keys: " + ", ".join(sorted(api_keys.keys()))
                or "(none)"
            )
        return RealtimeComponents(llm=build_realtime_model(api_key, speech_config))

    if isinstance(speech_config, PipelineSpeechConfig):
        # Phase 2: dispatch to stt/llm/tts/vad/turn_detection factories and
        # assemble PipelineComponents. Raised now so a pipeline config cannot
        # silently fall through to realtime.
        raise NotImplementedError(
            "Pipeline engine components are not implemented yet (Phase 2). "
            "Config: stt=%s, llm=%s, tts=%s"
            % (
                speech_config.stt.provider,
                speech_config.llm.provider,
                speech_config.tts.provider,
            )
        )

    # Defensive: the union is closed, but a future variant would surface here.
    raise TypeError(f"Unsupported speech config type: {type(speech_config).__name__}")


__all__ = [
    "RealtimeComponents",
    "PipelineComponents",
    "SessionComponents",
    "build_session_components",
]
