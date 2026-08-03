"""Build Pipecat speech services from the shared speech-config contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.fish.tts import FishAudioTTSService, FishAudioTTSSettings
from pipecat.services.google.gemini_live.llm import (
    GeminiLiveLLMService,
    GeminiVADParams,
)
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openrouter.llm import OpenRouterLLMService, OpenRouterLLMSettings

from shared.voice_agents.speech_config import (
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    SpeechConfig,
)
from src.speech.thinking_text_filter import ThinkingChannelTextFilter

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
OPENROUTER_DEFAULT_MODEL = "openai/gpt-4.1"
FISH_DEFAULT_MODEL = "s2.1-pro-free"
# Disable OpenRouter reasoning so Gemma/other thinking models do not stream
# internal channel tokens into assistant content (which TTS would then speak).
OPENROUTER_DISABLE_REASONING = {"reasoning": {"effort": "none", "exclude": True}}


def _pipeline_tts_text_filters() -> list[ThinkingChannelTextFilter]:
    """Return TTS filters that strip leaked model thinking/channel markers."""
    return [ThinkingChannelTextFilter()]


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
    llm: Any
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
        "llm": ("openai", "cerebras", "openrouter"),
        "tts": ("cartesia", "fish"),
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


def _build_pipeline_stt(config: Any, api_keys: dict[str, Any]) -> Any:
    """Build the STT service for a pipeline preset stage."""
    provider = _stage_provider(config, "stt")
    if provider != "deepgram":
        raise ValueError(f"Unsupported Pipecat STT provider: {provider}")
    stt_kwargs = dict(config.params)
    if config.model:
        stt_kwargs["model"] = config.model
    return DeepgramSTTService(
        api_key=_require_key(api_keys, provider, "stt"), **stt_kwargs
    )


def _build_pipeline_llm(
    config: Any,
    api_keys: dict[str, Any],
    system_instruction: str,
    tools: ToolsSchema | None,
) -> Any:
    """Build the LLM service for a pipeline preset stage."""
    provider = _stage_provider(config, "llm")
    llm_kwargs = dict(config.params)
    if provider == "openai":
        if config.model:
            llm_kwargs["model"] = config.model
        return OpenAILLMService(
            api_key=_require_key(api_keys, provider, "llm"),
            tools=tools,
            settings=OpenAILLMService.Settings(system_instruction=system_instruction),
            **llm_kwargs,
        )
    if provider == "cerebras":
        if config.model:
            llm_kwargs["model"] = config.model
        llm_kwargs.setdefault("base_url", CEREBRAS_BASE_URL)
        return OpenAILLMService(
            api_key=_require_key(api_keys, provider, "llm"),
            tools=tools,
            settings=OpenAILLMService.Settings(system_instruction=system_instruction),
            **llm_kwargs,
        )
    if provider == "openrouter":
        model = config.model or OPENROUTER_DEFAULT_MODEL
        # Merge preset params.extra (if any) under our reasoning defaults so
        # callers can still override, but thinking stays off by default.
        extra = dict(OPENROUTER_DISABLE_REASONING)
        preset_extra = llm_kwargs.pop("extra", None)
        if isinstance(preset_extra, dict):
            extra.update(preset_extra)
        return OpenRouterLLMService(
            api_key=_require_key(api_keys, provider, "llm"),
            tools=tools,
            settings=OpenRouterLLMSettings(
                model=model,
                system_instruction=system_instruction,
                extra=extra,
            ),
            **llm_kwargs,
        )
    raise ValueError(f"Unsupported Pipecat LLM provider: {provider}")


def _build_pipeline_tts(config: Any, api_keys: dict[str, Any]) -> Any:
    """Build the TTS service for a pipeline preset stage."""
    provider = _stage_provider(config, "tts")
    tts_kwargs = dict(config.params)
    # Always attach the thinking-channel filter so Gemma/OpenRouter (and similar
    # reasoning models) cannot leak "<|channel>thought" into spoken audio.
    tts_kwargs.setdefault("text_filters", _pipeline_tts_text_filters())
    if provider == "cartesia":
        if config.model:
            tts_kwargs["model"] = config.model
        if config.voice:
            tts_kwargs["voice_id"] = config.voice
        return CartesiaTTSService(
            api_key=_require_key(api_keys, provider, "tts"), **tts_kwargs
        )
    if provider == "fish":
        # Fish Audio uses ``voice`` as the reference/voice id and ``model`` for
        # the synthesis model (e.g. s2.1-pro-free). Extra params stay available
        # for latency/prosody via Settings when needed later.
        return FishAudioTTSService(
            api_key=_require_key(api_keys, provider, "tts"),
            settings=FishAudioTTSSettings(
                model=config.model or FISH_DEFAULT_MODEL,
                voice=config.voice,
            ),
            **tts_kwargs,
        )
    raise ValueError(f"Unsupported Pipecat TTS provider: {provider}")


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

    stt = _build_pipeline_stt(speech_config.stt, api_keys)
    llm = _build_pipeline_llm(
        speech_config.llm, api_keys, system_instruction, tools
    )
    tts = _build_pipeline_tts(speech_config.tts, api_keys)
    vad_params = dict(speech_config.vad.params) if speech_config.vad else {}
    return PipelineComponents(
        mode="pipeline",
        stt=stt,
        llm=llm,
        tts=tts,
        vad=SileroVADAnalyzer(sample_rate=16000, **vad_params),
    )
