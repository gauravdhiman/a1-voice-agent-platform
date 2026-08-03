"""Build Pipecat speech services from the shared speech-config contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.gemini_live.llm import (
    GeminiLiveLLMService,
    GeminiVADParams,
)
from pipecat.services.openai.llm import OpenAILLMService

from shared.voice_agents.speech_config import (
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    SpeechConfig,
)

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"


@dataclass
class RealtimeComponents:
    """Configured end-to-end Gemini Live component bundle."""

    mode: Literal["realtime"]
    llm: GeminiLiveLLMService


@dataclass
class PipelineComponents:
    """Configured modular STT → LLM → TTS component bundle."""

    mode: Literal["pipeline"]
    stt: Any
    llm: OpenAILLMService
    tts: Any
    vad: SileroVADAnalyzer


def _normalize_gemini_model(model: str) -> str:
    """Return a Gemini Live model ID with its required ``models/`` prefix."""
    return model if model.startswith("models/") else f"models/{model}"


def _stage_provider(config: Any, stage: str) -> str:
    """Resolve direct provider for a stage, including explicit inference hints."""
    if config.provider != "livekit_inference":
        return config.provider
    hint = str(config.params.get("direct_provider", "")).lower()
    model = (config.model or "").lower()
    candidates = {
        "stt": ("deepgram",),
        "llm": ("openai", "cerebras"),
        "tts": ("cartesia",),
    }[stage]
    for provider in candidates:
        if hint == provider or provider in model:
            return provider
    raise ValueError(
        f"Pipeline {stage} uses livekit_inference but cannot map it to a direct "
        f"Pipecat provider. Set params.direct_provider to one of {candidates} "
        "or select a direct provider."
    )


def _require_key(api_keys: dict[str, Any], provider: str, stage: str) -> str:
    """Return a provider key or raise an actionable pipeline configuration error."""
    api_key = api_keys.get(provider)
    if not api_key:
        raise ValueError(
            f"Pipeline {stage} provider '{provider}' requires a '{provider}' API key."
        )
    return str(api_key)


def build_speech_components(
    speech_config: SpeechConfig,
    api_keys: dict[str, Any],
    system_instruction: str,
    tools: ToolsSchema | None = None,
) -> RealtimeComponents | PipelineComponents:
    """Build Pipecat services for a resolved agent speech configuration.

    Args:
        speech_config: Concrete shared realtime or pipeline configuration.
        api_keys: Per-provider key map resolved for the organization.
        system_instruction: Agent prompt applied to the model service.
        tools: Optional Pipecat ``ToolsSchema`` advertised to the LLM.
            Gemini Live requires tools at construction time.

    Returns:
        Realtime or pipeline component bundle selected by ``engine_mode``.

    Raises:
        ValueError: For missing provider keys or unsupported stage mappings.
    """
    if isinstance(speech_config, RealtimeSpeechConfig):
        api_key = _require_key(api_keys, "google", "realtime")
        return RealtimeComponents(
            mode="realtime",
            llm=GeminiLiveLLMService(
                api_key=api_key,
                tools=tools,
                settings=GeminiLiveLLMService.Settings(
                    model=_normalize_gemini_model(speech_config.model),
                    voice=speech_config.voice,
                    system_instruction=system_instruction,
                    temperature=speech_config.temperature,
                    vad=GeminiVADParams(
                        silence_duration_ms=speech_config.silence_duration_ms,
                        prefix_padding_ms=speech_config.prefix_padding_ms,
                    ),
                ),
            ),
        )

    if not isinstance(speech_config, PipelineSpeechConfig):
        raise TypeError(f"Unsupported speech config: {type(speech_config).__name__}")

    stt_provider = _stage_provider(speech_config.stt, "stt")
    if stt_provider != "deepgram":
        raise ValueError(f"Unsupported Pipecat STT provider: {stt_provider}")
    stt_kwargs = dict(speech_config.stt.params)
    if speech_config.stt.model:
        stt_kwargs["model"] = speech_config.stt.model
    stt = DeepgramSTTService(
        api_key=_require_key(api_keys, stt_provider, "stt"), **stt_kwargs
    )

    llm_provider = _stage_provider(speech_config.llm, "llm")
    if llm_provider not in {"openai", "cerebras"}:
        raise ValueError(f"Unsupported Pipecat LLM provider: {llm_provider}")
    llm_kwargs = dict(speech_config.llm.params)
    if speech_config.llm.model:
        llm_kwargs["model"] = speech_config.llm.model
    if llm_provider == "cerebras":
        llm_kwargs.setdefault("base_url", CEREBRAS_BASE_URL)
    llm = OpenAILLMService(
        api_key=_require_key(api_keys, llm_provider, "llm"),
        tools=tools,
        settings=OpenAILLMService.Settings(system_instruction=system_instruction),
        **llm_kwargs,
    )

    tts_provider = _stage_provider(speech_config.tts, "tts")
    if tts_provider != "cartesia":
        raise ValueError(f"Unsupported Pipecat TTS provider: {tts_provider}")
    tts_kwargs = dict(speech_config.tts.params)
    if speech_config.tts.model:
        tts_kwargs["model"] = speech_config.tts.model
    if speech_config.tts.voice:
        tts_kwargs["voice_id"] = speech_config.tts.voice
    tts = CartesiaTTSService(
        api_key=_require_key(api_keys, tts_provider, "tts"), **tts_kwargs
    )
    vad_params = dict(speech_config.vad.params) if speech_config.vad else {}
    return PipelineComponents(
        mode="pipeline",
        stt=stt,
        llm=llm,
        tts=tts,
        vad=SileroVADAnalyzer(sample_rate=16000, **vad_params),
    )
