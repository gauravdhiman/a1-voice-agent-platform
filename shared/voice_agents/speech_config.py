"""Per-agent speech engine configuration models.

This module defines the typed contract between three layers:

1. **Storage** — the ``voice_agents.speech_config`` JSONB column (added in the
   Phase 3 Alembic migration). Storing the whole config as one validated JSON
   blob means adding a provider or a tunable does NOT require a schema
   migration — only a change here.
2. **Backend CRUD** — the voice-agent API reads/writes this column and
   validates it through :func:`parse_speech_config`.
3. **Worker session builder** — :mod:`worker.src.session_builder` dispatches on
   ``engine_mode`` to construct the LiveKit ``AgentSession`` either as an
   end-to-end realtime model or as a modular STT -> LLM -> TTS pipeline.

Two engine modes are supported via a discriminated union on ``engine_mode``:

- ``realtime`` — a single end-to-end speech model (Google Gemini native-audio)
  that handles STT + LLM + TTS together. This is the existing behavior.
- ``pipeline`` — a modular cascade where each stage (STT, LLM, TTS, VAD, turn
  detection) can use a different provider/model, independently configurable.

Design notes:

- ``RealtimeSpeechConfig`` defaults **exactly reproduce** the constants
  previously hardcoded in ``worker/src/realtime_config.py`` (model, voice,
  temperature, endpointing). This is what makes ``default_realtime_config()``
  behavior-neutral: an agent with no ``speech_config`` set gets the same
  realtime tuning it gets today.
- The pipeline stage configs (``STTStageConfig`` etc.) carry a ``provider``
  dispatch key, an optional provider-specific ``model`` id, and an open
  ``params`` dict for provider-specific kwargs — so the factory can swap a
  provider without a schema change.
- ``parse_speech_config(None)`` falls back to the default realtime config so
  legacy agents (no column set) keep working unchanged.
"""

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ---------------------------------------------------------------------------
# Engine mode
# ---------------------------------------------------------------------------


class EngineMode(str, Enum):
    """The conversation engine strategy for a voice agent.

    Attributes:
        REALTIME: End-to-end speech model — one model does STT+LLM+TTS
            (e.g. Google Gemini native-audio). Lowest component count, single
            provider.
        PIPELINE: Modular STT -> LLM -> TTS cascade, each stage independently
            configurable with a different provider/model. Maximum flexibility.
    """

    REALTIME = "realtime"
    PIPELINE = "pipeline"


# ---------------------------------------------------------------------------
# Pipeline stage configs
# ---------------------------------------------------------------------------


class StageConfig(BaseModel):
    """Base config for a single pipeline stage's provider selection.

    Every pipeline stage (STT, LLM, TTS, VAD, turn detection) is configured by
    picking a ``provider`` (the factory dispatch key), an optional
    provider-specific ``model`` id, and an open ``params`` dict for any other
    provider-specific kwargs. Keeping ``params`` open means adding a provider
    or a tunable never requires a schema migration.

    Attributes:
        provider: The provider dispatch key, e.g. ``"deepgram"``, ``"openai"``,
            ``"cartesia"``. The factory maps this to a LiveKit plugin builder.
        model: Provider-specific model id (e.g. ``"nova-3"``, ``"gpt-4o-mini"``).
            ``None`` means "use the provider's default".
        params: Extra provider-specific kwargs forwarded to the plugin builder.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., description="Provider dispatch key for the factory.")
    model: Optional[str] = Field(
        None, description="Provider-specific model id; None = provider default."
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="Extra provider-specific kwargs."
    )


class STTStageConfig(StageConfig):
    """Speech-to-text stage config (e.g. Deepgram, OpenAI, AssemblyAI)."""


class LLMStageConfig(StageConfig):
    """Language model stage config (e.g. OpenAI, Anthropic, Google, Groq)."""


class TTSStageConfig(StageConfig):
    """Text-to-speech stage config (e.g. Cartesia, ElevenLabs, OpenAI).

    Attributes:
        voice: Optional TTS voice id, name, or UUID (provider-specific). When
            set, forwarded as a top-level plugin kwarg and takes precedence over
            ``params["voice"]`` for backward compatibility with configs that
            stored voice inside ``params``.
    """

    voice: Optional[str] = Field(
        None,
        description=(
            "TTS voice id, name, or UUID (provider-specific). Omitted when "
            "blank so the provider default applies."
        ),
    )


class VADConfig(StageConfig):
    """Voice-activity-detection config (e.g. Silero). Optional in a pipeline —
    LiveKit applies a sensible default when ``None``."""


class TurnDetectionConfig(StageConfig):
    """Turn-detection / endpointing config. Optional — LiveKit applies a
    default turn detector when ``None``."""


# ---------------------------------------------------------------------------
# Engine configs
# ---------------------------------------------------------------------------


# The Gemini native-audio realtime model id. Duplicated from
# worker/src/realtime_config.py (kept there as the runtime source of truth for
# the realtime provider) so this module can default to it without importing the
# worker package (which would create a shared->worker dependency). The two must
# stay in sync; test_speech_config asserts the equality.
DEFAULT_REALTIME_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_REALTIME_VOICE = "Puck"
DEFAULT_REALTIME_TEMPERATURE = 0.7
DEFAULT_ENDPOINTING_SILENCE_DURATION_MS = 500
DEFAULT_ENDPOINTING_PREFIX_PADDING_MS = 200


class RealtimeSpeechConfig(BaseModel):
    """Config for the end-to-end realtime engine (Google Gemini native-audio).

    A single model handles STT + LLM + TTS. The non-tunable parts of the
    realtime tuning (thinking disabled, barge-in enabled) are fixed in the
    realtime provider builder — only the user-facing knobs are exposed here.

    Attributes:
        engine_mode: Always ``realtime`` (discriminator).
        provider: Always ``google`` (the only supported realtime provider).
        model: The Gemini native-audio model id.
        voice: The Gemini voice name.
        temperature: Sampling temperature.
        silence_duration_ms: Trailing silence before end-of-turn (endpointing).
        prefix_padding_ms: Pre-speech audio kept to avoid clipping.
        params: Reserved for future provider-specific kwargs.
    """

    model_config = ConfigDict(extra="forbid")

    engine_mode: Literal[EngineMode.REALTIME] = EngineMode.REALTIME
    provider: Literal["google"] = "google"
    model: str = DEFAULT_REALTIME_MODEL
    voice: str = DEFAULT_REALTIME_VOICE
    temperature: float = DEFAULT_REALTIME_TEMPERATURE
    silence_duration_ms: int = DEFAULT_ENDPOINTING_SILENCE_DURATION_MS
    prefix_padding_ms: int = DEFAULT_ENDPOINTING_PREFIX_PADDING_MS
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineSpeechConfig(BaseModel):
    """Config for the modular pipeline engine (STT -> LLM -> TTS).

    Each core stage is independently configurable. ``vad`` and
    ``turn_detection`` are optional — LiveKit applies defaults when ``None``.

    Attributes:
        engine_mode: Always ``pipeline`` (discriminator).
        stt: Speech-to-text stage config (required).
        llm: Language model stage config (required).
        tts: Text-to-speech stage config (required).
        vad: Voice-activity-detection config (optional).
        turn_detection: Turn-detection / endpointing config (optional).
    """

    model_config = ConfigDict(extra="forbid")

    engine_mode: Literal[EngineMode.PIPELINE] = EngineMode.PIPELINE
    stt: STTStageConfig
    llm: LLMStageConfig
    tts: TTSStageConfig
    vad: Optional[VADConfig] = None
    turn_detection: Optional[TurnDetectionConfig] = None


# Discriminated union on engine_mode. Used as the field type wherever a
# speech config is stored/parsed (the JSONB column hydration, API request
# bodies). Annotated with Field(discriminator=...) so Pydantic picks the right
# concrete class from the engine_mode tag without guessing.
SpeechConfig = Annotated[
    Union[RealtimeSpeechConfig, PipelineSpeechConfig],
    Field(discriminator="engine_mode"),
]


def default_realtime_config() -> RealtimeSpeechConfig:
    """Return the default realtime config (today's behavior).

    Used for legacy agents that have no ``speech_config`` set, so they get
    exactly the same realtime tuning as before the pipeline feature.

    Returns:
        RealtimeSpeechConfig with all defaults (Google native-audio model,
        Puck voice, temperature 0.7, endpointing 500/200ms).
    """
    return RealtimeSpeechConfig()


def parse_speech_config(
    data: Union[dict[str, Any], None],
) -> Union[RealtimeSpeechConfig, PipelineSpeechConfig]:
    """Parse a raw dict (from the JSONB column or an API body) into a typed
    speech config, dispatching on ``engine_mode``.

    ``None`` (a legacy agent with no ``speech_config`` column set) falls back to
    :func:`default_realtime_config` so existing agents keep working unchanged.

    Args:
        data: Raw dict with an ``engine_mode`` tag, or ``None`` for the default
            realtime config.

    Returns:
        The concrete config instance (RealtimeSpeechConfig or
        PipelineSpeechConfig).

    Raises:
        ValidationError: If ``data`` is not ``None`` and is missing/has an
            unknown ``engine_mode``, or fails the concrete config's validation.

    Example:
        ```python
        cfg = parse_speech_config({"engine_mode": "pipeline",
        ...   "stt": {"provider": "deepgram"},
        ...   "llm": {"provider": "openai", "model": "gpt-4o-mini"},
        ...   "tts": {"provider": "cartesia"}})
        assert cfg.engine_mode == EngineMode.PIPELINE
        ```
    """
    if data is None:
        return default_realtime_config()
    # Validate through the discriminated union. We type-ignore the return:
    # Pydantic's TypeAdapter returns the union type, which is exactly one of
    # the two concrete configs.
    from pydantic import TypeAdapter

    adapter: TypeAdapter[SpeechConfig] = TypeAdapter(SpeechConfig)
    return adapter.validate_python(data)  # type: ignore[return-value]


__all__ = [
    "EngineMode",
    "StageConfig",
    "STTStageConfig",
    "LLMStageConfig",
    "TTSStageConfig",
    "VADConfig",
    "TurnDetectionConfig",
    "RealtimeSpeechConfig",
    "PipelineSpeechConfig",
    "SpeechConfig",
    "default_realtime_config",
    "parse_speech_config",
]


# Silence the unused-import linter for ValidationError (re-exported for callers
# who want to catch it without importing pydantic directly).
_ = ValidationError
