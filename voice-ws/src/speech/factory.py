"""Build Pipecat speech services from the shared speech-config contract."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.utils import create_stream_resampler
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import InputAudioRawFrame
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.fish.tts import FishAudioTTSService, FishAudioTTSSettings
from pipecat.services.google.gemini_live.llm import (
    GeminiLiveLLMService,
    GeminiVADParams,
)
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openai.realtime.events import (
    AudioConfiguration,
    AudioInput,
    AudioOutput,
    InputAudioTranscription,
    SessionProperties,
    TurnDetection,
)
from pipecat.services.openai.realtime.llm import (
    OpenAIRealtimeLLMService as PipecatOpenAIRealtimeLLMService,
)
from pipecat.services.openrouter.llm import OpenRouterLLMService, OpenRouterLLMSettings
from src.speech.openai_live import OpenAILiveLLMService
from src.speech.thinking_text_filter import ThinkingChannelTextFilter

from shared.voice_agents.model_capabilities import OPENROUTER_DEFAULT_MODEL
from shared.voice_agents.speech_config import (
    OPENAI_REALTIME_MODEL_VOICES,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    SpeechConfig,
)

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
FISH_DEFAULT_MODEL = "s2.1-pro-free"
# Disable OpenRouter reasoning via extra_body — the OpenAI SDK rejects a top-level
# ``reasoning`` kwarg on chat.completions.create(), but OpenRouter honors it in the
# request body. TTS also uses ThinkingChannelTextFilter as a second line of defense.
OPENROUTER_DISABLE_REASONING = {
    "extra_body": {
        "reasoning": {"effort": "none", "exclude": True},
    },
}


def _merge_openrouter_extra(preset_extra: dict[str, Any] | None) -> dict[str, Any]:
    """Merge preset LLM extras without passing unsupported SDK kwargs."""
    extra: dict[str, Any] = {
        "extra_body": dict(OPENROUTER_DISABLE_REASONING["extra_body"]),
    }
    if not isinstance(preset_extra, dict):
        return extra

    for key, value in preset_extra.items():
        if key == "reasoning":
            extra["extra_body"]["reasoning"] = value
        elif key == "extra_body" and isinstance(value, dict):
            extra["extra_body"].update(value)
        elif key != "extra_body":
            extra[key] = value
    return extra


def _pipeline_tts_text_filters() -> list[ThinkingChannelTextFilter]:
    """Return TTS filters that strip leaked model thinking/channel markers."""
    return [ThinkingChannelTextFilter()]


@dataclass
class RealtimeComponents:
    """Configured end-to-end realtime component bundle."""

    mode: Literal["realtime"]
    llm: Any
    greeting: Callable[[str], Awaitable[None]] | None = None


class OpenAIRealtimeLLMService(PipecatOpenAIRealtimeLLMService):
    """Keep the pinned OpenAI Realtime adapter's provider audio contract.

    The browser and Twilio transports intentionally remain 16 kHz. Pipecat's
    OpenAI Realtime service forwards input bytes unchanged and the provider
    session is fixed at 24 kHz, so conversion belongs at this adapter seam.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._provider_input_resampler = create_stream_resampler()

    async def _send_user_audio(self, frame: InputAudioRawFrame) -> None:
        """Resample transport audio before the pinned adapter sends it."""
        if frame.sample_rate != 24000:
            audio = await self._provider_input_resampler.resample(
                frame.audio,
                frame.sample_rate,
                24000,
            )
            frame = InputAudioRawFrame(
                audio=audio,
                sample_rate=24000,
                num_channels=frame.num_channels,
            )
        await super()._send_user_audio(frame)


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


_SUPPORTED_STAGE_PROVIDERS = {
    "stt": ("deepgram",),
    "llm": ("openai", "cerebras", "openrouter"),
    "tts": ("cartesia", "fish"),
}


def _stage_provider(config: Any, stage: str) -> str:
    """Resolve direct provider for a pipeline preset stage."""
    from shared.voice_agents.key_resolver import normalize_stage_provider

    provider = normalize_stage_provider(config.provider, stage=stage)
    candidates = _SUPPORTED_STAGE_PROVIDERS[stage]
    if provider in candidates:
        return provider
    raise ValueError(
        f"Pipeline {stage} provider '{config.provider}' is not supported. "
        f"Use one of {candidates}."
    )


def _require_key(api_keys: dict[str, Any], provider: str, stage: str) -> str:
    """Return a provider key or raise an actionable configuration error."""
    api_key = api_keys.get(provider)
    if not api_key:
        raise ValueError(
            f"{stage.capitalize()} provider '{provider}' requires a "
            f"'{provider}' API key."
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
        preset_extra = llm_kwargs.pop("extra", None)
        extra = _merge_openrouter_extra(
            preset_extra if isinstance(preset_extra, dict) else None
        )
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
        api_key = _require_key(api_keys, speech_config.provider, "realtime")
        if speech_config.provider == "google":
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
                        thinking={"thinking_budget": 0},
                        vad=GeminiVADParams(
                            silence_duration_ms=speech_config.silence_duration_ms,
                            prefix_padding_ms=speech_config.prefix_padding_ms,
                        ),
                    ),
                ),
            )

        if speech_config.model not in OPENAI_REALTIME_MODEL_VOICES:
            raise ValueError(
                f"OpenAI realtime model '{speech_config.model}' is not supported."
            )
        if speech_config.model == "gpt-live-1":
            service = OpenAILiveLLMService(
                api_key=api_key,
                model=speech_config.model,
                voice=speech_config.voice,
                system_instruction=system_instruction,
                tools=tools,
            )
            return RealtimeComponents(
                mode="realtime",
                llm=service,
                greeting=service.send_greeting,
            )

        session_properties = SessionProperties(
            model=speech_config.model,
            output_modalities=["audio"],
            instructions=system_instruction,
            audio=AudioConfiguration(
                input=AudioInput(
                    transcription=InputAudioTranscription(),
                    turn_detection=TurnDetection(
                        prefix_padding_ms=speech_config.prefix_padding_ms,
                        silence_duration_ms=speech_config.silence_duration_ms,
                    ),
                ),
                output=AudioOutput(voice=speech_config.voice),
            ),
            tools=tools,
            tool_choice="auto" if tools and tools.standard_tools else None,
        )
        return RealtimeComponents(
            mode="realtime",
            llm=OpenAIRealtimeLLMService(
                api_key=api_key,
                settings=OpenAIRealtimeLLMService.Settings(
                    model=speech_config.model,
                    system_instruction=system_instruction,
                    temperature=None,
                    max_tokens=None,
                    top_p=None,
                    top_k=None,
                    frequency_penalty=None,
                    presence_penalty=None,
                    seed=None,
                    filter_incomplete_user_turns=False,
                    user_turn_completion_config=None,
                    session_properties=session_properties,
                ),
            ),
        )

    if not isinstance(speech_config, PipelineSpeechConfig):
        raise TypeError(f"Unsupported speech config: {type(speech_config).__name__}")

    stt = _build_pipeline_stt(speech_config.stt, api_keys)
    llm = _build_pipeline_llm(speech_config.llm, api_keys, system_instruction, tools)
    tts = _build_pipeline_tts(speech_config.tts, api_keys)
    vad_params = dict(speech_config.vad.params) if speech_config.vad else {}
    return PipelineComponents(
        mode="pipeline",
        stt=stt,
        llm=llm,
        tts=tts,
        vad=SileroVADAnalyzer(sample_rate=16000, **vad_params),
    )
