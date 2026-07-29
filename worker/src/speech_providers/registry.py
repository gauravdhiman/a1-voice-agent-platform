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
from typing import Any, Callable, Union

from speech_providers.llm import (
    build_cerebras_llm,
    build_livekit_inference_llm,
    build_openai_llm,
)
from speech_providers.realtime.provider import build_realtime_model
from speech_providers.stt import build_deepgram_stt, build_livekit_inference_stt
from speech_providers.tts import build_cartesia_tts, build_livekit_inference_tts
from speech_providers.vad import build_silero_vad

from shared.voice_agents.speech_config import (
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    StageConfig,
)

# ---------------------------------------------------------------------------
# Per-stage provider dispatch tables.
#
# Each table maps the ``provider`` dispatch key (from a stage config) to the
# builder that constructs that provider's LiveKit plugin. Adding a provider =
# one new builder module + one entry here. The builder signature for keyed
# stages is ``(api_key, config)``; the VAD builder is ``(config)`` (Silero is
# local, no key).
# ---------------------------------------------------------------------------
STT_BUILDERS: dict[str, Callable[[str, StageConfig], Any]] = {
    "deepgram": build_deepgram_stt,
}
LLM_BUILDERS: dict[str, Callable[[str, StageConfig], Any]] = {
    "openai": build_openai_llm,
    "cerebras": build_cerebras_llm,
}
TTS_BUILDERS: dict[str, Callable[[str, StageConfig], Any]] = {
    "cartesia": build_cartesia_tts,
}
# VAD has no API key (Silero is local/on-device), so its builder takes only the
# config. Other VAD providers would go here when added.
VAD_BUILDERS: dict[str, Callable[[StageConfig], Any]] = {
    "silero": build_silero_vad,
}

# ---------------------------------------------------------------------------
# LiveKit Inference stage dispatch table (Phase 2b).
#
# LiveKit Inference (``livekit.agents.inference``) gives access to many STT/LLM/
# TTS models through a SINGLE LiveKit Cloud auth (``api_key`` + ``api_secret``)
# rather than a per-provider key. So Inference stages bypass the keyed
# ``*_BUILDERS`` path (and its per-provider key guard): when a stage's
# ``provider == "livekit_inference"``, the registry dispatches through this table
# instead, and the builder resolves the LiveKit key on its own (env in Phase
# 2b; per-org injection in Phase 3 — see :mod:`speech_providers.stt.inference`).
# A pipeline may mix Inference stages with direct stages freely (the "mixed
# preset" direction): each stage dispatches on its own ``provider``.
# ---------------------------------------------------------------------------
LIVEKIT_INFERENCE_STAGE_BUILDERS: dict[str, Callable[..., Any]] = {
    "stt": build_livekit_inference_stt,
    "llm": build_livekit_inference_llm,
    "tts": build_livekit_inference_tts,
}
# The dispatch key a stage config sets to opt into the Inference path.
LIVEKIT_INFERENCE_PROVIDER = "livekit_inference"


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
            present in ``api_keys``, or if a pipeline config is missing a
            required stage provider's key in ``api_keys``.
        NotImplementedError: If a pipeline config names an unsupported provider
            for any stage, or sets a non-``None`` ``turn_detection`` (deferred
            to Phase 5).

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
        return _build_pipeline_components(speech_config, api_keys)

    # Defensive: the union is closed, but a future variant would surface here.
    raise TypeError(f"Unsupported speech config type: {type(speech_config).__name__}")


def _build_keyed_stage(
    stage_name: str,
    stage_config: StageConfig,
    builders: dict[str, Callable[..., Any]],
    api_keys: dict[str, str],
) -> Any:
    """Dispatch a keyed stage (STT/LLM/TTS) to its provider builder.

    Looks up the provider in ``builders``, reads the matching key from
    ``api_keys``, and calls ``builder(api_key, stage_config)``. Mirrors the
    realtime branch's Google-key guard: a missing key fails fast with a clear
    ``ValueError`` naming the provider, and an unsupported provider raises
    ``NotImplementedError`` listing the supported providers.

    Args:
        stage_name: Human-readable stage label for error messages (e.g. "stt").
        stage_config: The stage's config (carries ``provider``/``model``/``params``).
        builders: The per-stage provider dispatch table.
        api_keys: Per-provider API key map.

    Returns:
        The constructed LiveKit plugin for the stage.

    Raises:
        NotImplementedError: If ``stage_config.provider`` is not in ``builders``.
        ValueError: If the provider's key is absent from ``api_keys``.
    """
    provider = stage_config.provider
    builder = builders.get(provider)
    if builder is None:
        raise NotImplementedError(
            f"Pipeline {stage_name} provider '{provider}' is not supported; "
            f"supported providers: {sorted(builders.keys())}"
        )
    api_key = api_keys.get(provider)
    if not api_key:
        raise ValueError(
            f"Pipeline {stage_name} stage requires a '{provider}' API key in "
            f"api_keys; got keys: {sorted(api_keys.keys()) or '(none)'}"
        )
    return builder(api_key, stage_config)


def _build_pipeline_vad(
    vad_config: Any,
) -> Any:
    """Build the VAD for a pipeline config.

    The registry **always** builds an explicit standalone Silero VAD for the
    pipeline engine — even when ``vad_config`` is ``None`` (then Silero defaults
    apply). This keeps the pipeline off the bundled ``livekit.agents.inference``
    VAD path that ``AgentSession`` would otherwise fall back to (the
    missing-Pillow path, deferred bug #7). See the Phase 2 plan's "VAD default
    nuance" section.

    Args:
        vad_config: The pipeline's ``VADConfig`` or ``None``.

    Returns:
        The constructed VAD plugin (never ``None`` from this path).

    Raises:
        NotImplementedError: If a non-Silero VAD provider is requested.
    """
    if vad_config is None:
        # No VAD config -> default Silero. Routed through the dispatch table
        # (not a direct build_silero_vad call) so the table is the single source
        # of truth and tests can patch VAD_BUILDERS["silero"].
        return VAD_BUILDERS["silero"](None)
    provider = vad_config.provider
    builder = VAD_BUILDERS.get(provider)
    if builder is None:
        raise NotImplementedError(
            f"Pipeline vad provider '{provider}' is not supported; "
            f"supported providers: {sorted(VAD_BUILDERS.keys())}"
        )
    return builder(vad_config)


def _build_pipeline_turn_detection(
    turn_detection_config: Any,
) -> Any:
    """Build the turn detector for a pipeline config.

    Phase 2 runs on LiveKit's default VAD-based turn detection: a ``None``
    ``turn_detection_config`` returns ``None`` so ``session_builder`` omits the
    ``turn_detection=`` kwarg entirely. An explicit turn-detector builder (RNT
    / speculative turn tracking) is deferred to Phase 5 latency hardening, so
    any non-``None`` config raises ``NotImplementedError`` rather than being
    silently ignored.

    Args:
        turn_detection_config: The pipeline's ``TurnDetectionConfig`` or ``None``.

    Returns:
        ``None`` (Phase 2 default).

    Raises:
        NotImplementedError: If ``turn_detection_config`` is not ``None``.
    """
    if turn_detection_config is None:
        return None
    # TODO: [Phase 5] Add an explicit turn-detector builder (RNT / speculative
    # turn tracking) here once latency hardening lands. Rationale: the default
    # VAD-based turn detection adds end-of-turn dead-air; a speculative tracker
    # cuts that latency. Until then, refuse non-None configs loudly.
    raise NotImplementedError(
        "Pipeline turn_detection providers arrive in Phase 5 (latency "
        "hardening). Leave turn_detection unset to use LiveKit's default "
        "VAD-based turn detection. Requested provider: "
        f"{turn_detection_config.provider!r}"
    )


def _build_livekit_inference_stage(
    stage_name: str,
    stage_config: StageConfig,
    api_keys: dict[str, str],
) -> Any:
    """Dispatch an Inference stage (``provider == "livekit_inference"``) to its builder.

    LiveKit Inference uses a single LiveKit Cloud auth across all Inference
    stages, so it bypasses the keyed ``*_BUILDERS`` path and its per-provider
    key guard. The builder resolves the LiveKit key itself (env in Phase 2b;
    Phase 3's per-org ``key_resolver`` will inject a tenant's key via the
    builder's ``api_key`` / ``api_secret`` kwargs).

    Args:
        stage_name: One of ``"stt"`` / ``"llm"`` / ``"tts"``.
        stage_config: The stage's config (carries ``provider``/``model``/``params``).
        api_keys: Per-provider API key map. Unused in Phase 2b (Inference reads
            the LiveKit key from the env); reserved for the Phase 3 per-org
            key_resolver.

    Returns:
        The constructed LiveKit Inference plugin for the stage.

    Raises:
        NotImplementedError: If ``stage_name`` is not a known Inference stage
            (defensive — the pipeline only ever passes stt/llm/tts).
    """
    builder = LIVEKIT_INFERENCE_STAGE_BUILDERS.get(stage_name)
    if builder is None:
        raise NotImplementedError(
            f"LiveKit Inference does not support stage {stage_name!r}; "
            f"supported stages: {sorted(LIVEKIT_INFERENCE_STAGE_BUILDERS.keys())}"
        )
    # TODO: [Phase 3] Inject the tenant's per-org LiveKit key for Inference
    # here once the key_resolver populates api_keys["livekit"]:
    #   lk = api_keys.get("livekit") or {}
    #   builder(stage_config, api_key=lk.get("api_key"), api_secret=lk.get("api_secret"))
    # Rationale: the platform's LiveKit plan limits won't scale to all tenants'
    # calls, so a tenant can bring its own LiveKit key for Inference (mirrors
    # the Google-key BYO / use_platform_credits pattern). Phase 2b uses the
    # platform key from the env until that resolver lands.
    _ = api_keys  # reserved for Phase 3 (see TODO above)
    return builder(stage_config)


def _build_keyed_or_livekit_inference_stage(
    stage_name: str,
    stage_config: StageConfig,
    builders: dict[str, Callable[..., Any]],
    api_keys: dict[str, str],
) -> Any:
    """Dispatch a pipeline stage, choosing the Inference or keyed path.

    A stage with ``provider == "livekit_inference"`` takes the special Inference path
    (single LiveKit Cloud auth, no per-stage key guard); any other provider
    takes the normal keyed path through ``builders``.

    Args:
        stage_name: Human-readable stage label for error messages.
        stage_config: The stage's config.
        builders: The per-stage provider dispatch table (for the keyed path).
        api_keys: Per-provider API key map.

    Returns:
        The constructed LiveKit plugin for the stage.
    """
    if stage_config.provider == LIVEKIT_INFERENCE_PROVIDER:
        return _build_livekit_inference_stage(stage_name, stage_config, api_keys)
    return _build_keyed_stage(stage_name, stage_config, builders, api_keys)


def _build_pipeline_components(
    speech_config: PipelineSpeechConfig,
    api_keys: dict[str, str],
) -> PipelineComponents:
    """Assemble PipelineComponents from a pipeline speech config.

    Dispatches each keyed stage (STT/LLM/TTS) via
    :func:`_build_keyed_or_livekit_inference_stage` (Inference stages take the special
    LiveKit-auth path; direct providers take the keyed path), always builds an
    explicit Silero VAD via :func:`_build_pipeline_vad`, and resolves turn
    detection via :func:`_build_pipeline_turn_detection`.

    Args:
        speech_config: The pipeline speech config.
        api_keys: Per-provider API key map.

    Returns:
        PipelineComponents with all stage plugins populated.
    """
    return PipelineComponents(
        stt=_build_keyed_or_livekit_inference_stage(
            "stt", speech_config.stt, STT_BUILDERS, api_keys
        ),
        llm=_build_keyed_or_livekit_inference_stage(
            "llm", speech_config.llm, LLM_BUILDERS, api_keys
        ),
        tts=_build_keyed_or_livekit_inference_stage(
            "tts", speech_config.tts, TTS_BUILDERS, api_keys
        ),
        vad=_build_pipeline_vad(speech_config.vad),
        turn_detection=_build_pipeline_turn_detection(speech_config.turn_detection),
    )


__all__ = [
    "RealtimeComponents",
    "PipelineComponents",
    "SessionComponents",
    "build_session_components",
]
