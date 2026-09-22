"""Per-agent speech engine configuration models.

This module defines the typed contract between three layers:

1. **Storage** — the ``voice_agents.speech_config`` JSONB column.
2. **Backend CRUD** — the voice-agent API reads/writes this column and
   validates it through :func:`parse_speech_config`.
3. **voice-ws session setup** — :mod:`voice_ws.src.session_setup` and
   :mod:`voice_ws.src.speech.factory` dispatch on ``engine_mode`` to build
   either a Gemini realtime session or a modular STT → LLM → TTS pipeline.

Two engine modes are supported via a discriminated union on ``engine_mode``:

- ``realtime`` — a single end-to-end speech model (Google Gemini or OpenAI)
  that handles STT + LLM + TTS together.
- ``pipeline`` — a modular cascade where each stage (STT, LLM, TTS, VAD, turn
  detection) can use a different provider/model, independently configurable.

Design notes:

- ``RealtimeSpeechConfig`` defaults match the voice-ws Gemini realtime provider
  (model, voice, temperature, endpointing). OpenAI model/voice combinations are
  limited to the adapters implemented by voice-ws. ``default_realtime_config()``
  keeps legacy agents (no ``speech_config`` column) on the same tuning.
- The pipeline stage configs (``STTStageConfig`` etc.) carry a ``provider``
  dispatch key, an optional provider-specific ``model`` id, and an open
  ``params`` dict for provider-specific kwargs — so the factory can swap a
  provider without a schema change.
- ``parse_speech_config(None)`` falls back to the default realtime config so
  legacy agents (no column set) keep working unchanged.
"""

from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

# ---------------------------------------------------------------------------
# Engine mode
# ---------------------------------------------------------------------------


class EngineMode(str, Enum):
    """The conversation engine strategy for a voice agent.

    Attributes:
        REALTIME: End-to-end speech model — one model does STT+LLM+TTS
            (e.g. Google Gemini or OpenAI voice models). Lowest component
            count, single provider.
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
            ``"cartesia"``. The voice-ws factory maps this to a provider builder.
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
    voice-ws applies a sensible default when ``None``."""


class TurnDetectionConfig(StageConfig):
    """Turn-detection / endpointing config. Optional — voice-ws applies a
    default when ``None``."""


# ---------------------------------------------------------------------------
# Engine configs
# ---------------------------------------------------------------------------


# Default Gemini native-audio realtime model id used by voice-ws.
DEFAULT_REALTIME_MODEL = "gemini-3.8-live"
DEFAULT_REALTIME_VOICE = "Zephyr"
DEFAULT_REALTIME_TEMPERATURE = 0.7
DEFAULT_ENDPOINTING_SILENCE_DURATION_MS = 500
DEFAULT_ENDPOINTING_PREFIX_PADDING_MS = 200

RealtimeProvider = Literal["google", "openai"]
REALTIME_PROVIDERS: tuple[RealtimeProvider, ...] = ("google", "openai")

OPENAI_REALTIME_DEFAULT_MODEL = "gpt-live-1"
OPENAI_REALTIME_DEFAULT_VOICE = "marin"
OPENAI_REALTIME_MODELS = ("gpt-live-1", "gpt-realtime-2.1")
OPENAI_REALTIME_MODEL_VOICES: dict[str, frozenset[str]] = {
    "gpt-live-1": frozenset(
        {
            "marin",
            "quartz",
            "ripple",
            "vesper",
            "willow",
            "stone",
            "gleam",
            "meridian",
            "bossa",
            "tempo",
            "beacon",
            "delta",
            "cinder",
        }
    ),
    "gpt-realtime-2.1": frozenset(
        {
            "alloy",
            "ash",
            "ballad",
            "coral",
            "echo",
            "sage",
            "shimmer",
            "verse",
            "marin",
            "cedar",
        }
    ),
}


class RealtimeSpeechConfig(BaseModel):
    """Config for the end-to-end realtime engine.

    A single model handles STT + LLM + TTS. The non-tunable parts of the
    realtime tuning (thinking disabled, barge-in enabled) are fixed in the
    realtime provider builder — only the user-facing knobs are exposed here.

    Attributes:
        engine_mode: Always ``realtime`` (discriminator).
        provider: Realtime provider implemented by the voice runtime.
        model: Provider model id. Google accepts the provider's current model
            catalog; OpenAI is limited to the worker-supported models below.
        voice: Provider voice name. OpenAI voices are validated per model.
        temperature: Google sampling temperature. OpenAI Live currently uses
            its server-side defaults, so this must remain at the inert default.
        silence_duration_ms: Google trailing silence before end-of-turn.
        prefix_padding_ms: Google pre-speech audio kept to avoid clipping.
        params: Google provider-specific kwargs. OpenAI Live currently has no
            configurable params in this contract.
    """

    model_config = ConfigDict(extra="forbid")

    engine_mode: Literal[EngineMode.REALTIME] = EngineMode.REALTIME
    provider: RealtimeProvider = "google"
    model: str = DEFAULT_REALTIME_MODEL
    voice: str = DEFAULT_REALTIME_VOICE
    temperature: float = DEFAULT_REALTIME_TEMPERATURE
    silence_duration_ms: int = DEFAULT_ENDPOINTING_SILENCE_DURATION_MS
    prefix_padding_ms: int = DEFAULT_ENDPOINTING_PREFIX_PADDING_MS
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _apply_provider_defaults(cls, data: Any) -> Any:
        """Apply OpenAI defaults without changing legacy Google defaults."""
        if not isinstance(data, dict) or data.get("provider") != "openai":
            return data
        normalized = dict(data)
        normalized.setdefault("model", OPENAI_REALTIME_DEFAULT_MODEL)
        normalized.setdefault("voice", OPENAI_REALTIME_DEFAULT_VOICE)
        return normalized

    @model_validator(mode="after")
    def _validate_provider_contract(self) -> "RealtimeSpeechConfig":
        """Reject realtime combinations the worker cannot execute safely."""
        if self.provider == "google":
            return self

        if self.model not in OPENAI_REALTIME_MODEL_VOICES:
            raise ValueError(
                "OpenAI realtime model must be one of "
                f"{', '.join(OPENAI_REALTIME_MODELS)}."
            )
        if self.voice not in OPENAI_REALTIME_MODEL_VOICES[self.model]:
            voices = ", ".join(sorted(OPENAI_REALTIME_MODEL_VOICES[self.model]))
            raise ValueError(
                f"Voice '{self.voice}' is not supported by OpenAI realtime model "
                f"'{self.model}'. Choose one of: {voices}."
            )
        if self.params:
            raise ValueError("OpenAI realtime params must be an empty object.")
        if self.temperature != DEFAULT_REALTIME_TEMPERATURE:
            raise ValueError(
                "OpenAI realtime temperature is not configurable; use "
                f"{DEFAULT_REALTIME_TEMPERATURE}."
            )
        if self.silence_duration_ms != DEFAULT_ENDPOINTING_SILENCE_DURATION_MS:
            raise ValueError(
                "OpenAI realtime silence_duration_ms is not configurable; use "
                f"{DEFAULT_ENDPOINTING_SILENCE_DURATION_MS}."
            )
        if self.prefix_padding_ms != DEFAULT_ENDPOINTING_PREFIX_PADDING_MS:
            raise ValueError(
                "OpenAI realtime prefix_padding_ms is not configurable; use "
                f"{DEFAULT_ENDPOINTING_PREFIX_PADDING_MS}."
            )
        return self


class PipelineSpeechConfig(BaseModel):
    """Config for the modular pipeline engine (STT -> LLM -> TTS).

    Each core stage is independently configurable. ``vad`` and
    ``turn_detection`` are optional — voice-ws applies defaults when ``None``.

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
        RealtimeSpeechConfig with all defaults (Gemini 3.8 Live,
        Zephyr voice, temperature 0.7, endpointing 500/200ms).
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
    "RealtimeProvider",
    "REALTIME_PROVIDERS",
    "OPENAI_REALTIME_DEFAULT_MODEL",
    "OPENAI_REALTIME_DEFAULT_VOICE",
    "OPENAI_REALTIME_MODELS",
    "OPENAI_REALTIME_MODEL_VOICES",
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
