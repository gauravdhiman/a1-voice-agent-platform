"""Tests for Pipecat speech-component factory provider dispatch."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pipecat.frames.frames import InputAudioRawFrame
from src.speech.factory import OpenAIRealtimeLLMService, build_speech_components

from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
)


def _pipeline(
    stt: str = "deepgram",
    llm: str = "openai",
    tts: str = "cartesia",
    *,
    stt_model: str | None = None,
    llm_model: str | None = None,
    tts_model: str | None = None,
    tts_voice: str | None = None,
) -> PipelineSpeechConfig:
    return PipelineSpeechConfig(
        stt=STTStageConfig(provider=stt, model=stt_model),
        llm=LLMStageConfig(provider=llm, model=llm_model),
        tts=TTSStageConfig(provider=tts, model=tts_model, voice=tts_voice),
    )


class TestBuildSpeechComponentsPipeline:
    """Ensure each supported STT/LLM/TTS provider is wired for Pipecat."""

    def test_deepgram_stt_openai_llm_cartesia_tts(self) -> None:
        """Baseline Deepgram → OpenAI → Cartesia path remains available."""
        with (
            patch("src.speech.factory.DeepgramSTTService") as stt_cls,
            patch("src.speech.factory.OpenAILLMService") as llm_cls,
            patch("src.speech.factory.CartesiaTTSService") as tts_cls,
            patch("src.speech.factory.SileroVADAnalyzer", return_value=MagicMock()),
        ):
            stt_cls.return_value = MagicMock(name="stt")
            llm_cls.return_value = MagicMock(name="llm")
            tts_cls.return_value = MagicMock(name="tts")

            result = build_speech_components(
                _pipeline(
                    stt_model="nova-3", llm_model="gpt-4o-mini", tts_voice="voice-1"
                ),
                {
                    "deepgram": "dg",
                    "openai": "sk",
                    "cartesia": "cart",
                },
                "system",
            )

        assert result.mode == "pipeline"
        stt_cls.assert_called_once()
        assert stt_cls.call_args.kwargs["api_key"] == "dg"
        assert stt_cls.call_args.kwargs["model"] == "nova-3"
        llm_cls.assert_called_once()
        assert llm_cls.call_args.kwargs["api_key"] == "sk"
        tts_cls.assert_called_once()
        assert tts_cls.call_args.kwargs["api_key"] == "cart"
        assert tts_cls.call_args.kwargs["voice_id"] == "voice-1"

    def test_cerebras_llm_uses_openai_compatible_base_url(self) -> None:
        """Cerebras stays on the OpenAI-compatible client with Cerebras base URL."""
        with (
            patch("src.speech.factory.DeepgramSTTService", return_value=MagicMock()),
            patch("src.speech.factory.OpenAILLMService") as llm_cls,
            patch("src.speech.factory.CartesiaTTSService", return_value=MagicMock()),
            patch("src.speech.factory.SileroVADAnalyzer", return_value=MagicMock()),
        ):
            llm_cls.return_value = MagicMock()
            build_speech_components(
                _pipeline(llm="cerebras", llm_model="llama-3.3-70b"),
                {"deepgram": "dg", "cerebras": "cb", "cartesia": "cart"},
                "system",
            )

        assert llm_cls.call_args.kwargs["api_key"] == "cb"
        assert llm_cls.call_args.kwargs["base_url"] == "https://api.cerebras.ai/v1"
        assert llm_cls.call_args.kwargs["model"] == "llama-3.3-70b"

    def test_openrouter_llm_uses_openrouter_service(self) -> None:
        """OpenRouter is a first-class LLM provider for arbitrary model ids."""
        with (
            patch("src.speech.factory.DeepgramSTTService", return_value=MagicMock()),
            patch("src.speech.factory.OpenRouterLLMService") as llm_cls,
            patch("src.speech.factory.CartesiaTTSService", return_value=MagicMock()),
            patch("src.speech.factory.SileroVADAnalyzer", return_value=MagicMock()),
        ):
            llm_cls.return_value = MagicMock()
            build_speech_components(
                _pipeline(llm="openrouter", llm_model="anthropic/claude-sonnet-4"),
                {"deepgram": "dg", "openrouter": "or", "cartesia": "cart"},
                "system prompt",
            )

        assert llm_cls.call_args.kwargs["api_key"] == "or"
        settings = llm_cls.call_args.kwargs["settings"]
        assert settings.model == "anthropic/claude-sonnet-4"
        assert settings.system_instruction == "system prompt"
        # Gemma/OpenRouter reasoning must go via extra_body (SDK rejects top-level).
        assert settings.extra == {
            "extra_body": {
                "reasoning": {"effort": "none", "exclude": True},
            },
        }

    def test_openrouter_extra_merges_legacy_top_level_reasoning(self) -> None:
        """Preset params.extra reasoning is relocated into extra_body."""
        from src.speech.factory import _merge_openrouter_extra

        merged = _merge_openrouter_extra(
            {"reasoning": {"effort": "low"}, "temperature": 0.2}
        )
        assert merged["extra_body"]["reasoning"] == {"effort": "low"}
        assert merged["temperature"] == 0.2
        assert "reasoning" not in merged

    def test_pipeline_tts_attaches_thinking_text_filter(self) -> None:
        """Cartesia and Fish TTS always get the thinking-channel strip filter."""
        from src.speech.thinking_text_filter import ThinkingChannelTextFilter

        with (
            patch("src.speech.factory.DeepgramSTTService", return_value=MagicMock()),
            patch("src.speech.factory.OpenAILLMService", return_value=MagicMock()),
            patch("src.speech.factory.CartesiaTTSService") as cartesia_cls,
            patch("src.speech.factory.FishAudioTTSService") as fish_cls,
            patch("src.speech.factory.SileroVADAnalyzer", return_value=MagicMock()),
        ):
            cartesia_cls.return_value = MagicMock()
            fish_cls.return_value = MagicMock()
            build_speech_components(
                _pipeline(tts="cartesia"),
                {"deepgram": "dg", "openai": "sk", "cartesia": "cart"},
                "system",
            )
            build_speech_components(
                _pipeline(tts="fish", tts_model="s2.1-pro-free"),
                {"deepgram": "dg", "openai": "sk", "fish": "fish-key"},
                "system",
            )

        cartesia_filters = cartesia_cls.call_args.kwargs["text_filters"]
        fish_filters = fish_cls.call_args.kwargs["text_filters"]
        assert len(cartesia_filters) == 1
        assert isinstance(cartesia_filters[0], ThinkingChannelTextFilter)
        assert len(fish_filters) == 1
        assert isinstance(fish_filters[0], ThinkingChannelTextFilter)

    def test_fish_tts_uses_fish_audio_service(self) -> None:
        """Fish Audio TTS accepts model + voice (reference id) from the preset."""
        with (
            patch("src.speech.factory.DeepgramSTTService", return_value=MagicMock()),
            patch("src.speech.factory.OpenAILLMService", return_value=MagicMock()),
            patch("src.speech.factory.FishAudioTTSService") as tts_cls,
            patch("src.speech.factory.SileroVADAnalyzer", return_value=MagicMock()),
        ):
            tts_cls.return_value = MagicMock()
            build_speech_components(
                _pipeline(
                    tts="fish",
                    tts_model="s2.1-pro-free",
                    tts_voice="ref-voice-123",
                ),
                {"deepgram": "dg", "openai": "sk", "fish": "fish-key"},
                "system",
            )

        assert tts_cls.call_args.kwargs["api_key"] == "fish-key"
        settings = tts_cls.call_args.kwargs["settings"]
        assert settings.model == "s2.1-pro-free"
        assert settings.voice == "ref-voice-123"

    def test_unsupported_stt_provider_raises(self) -> None:
        """Unknown STT providers fail fast instead of silently degrading."""
        with pytest.raises(ValueError, match="is not supported"):
            build_speech_components(
                _pipeline(stt="assemblyai"),
                {"assemblyai": "x", "openai": "sk", "cartesia": "cart"},
                "system",
            )

    def test_gemini_38_live_uses_default_model_voice_without_thinking_override(
        self,
    ) -> None:
        """Gemini 3.8 Live rejects the legacy thinking-budget setting."""
        with (
            patch("src.speech.factory.GeminiLiveLLMService") as gemini_cls,
            patch("src.speech.factory.GeminiLiveLLMService.Settings") as settings_cls,
        ):
            settings_cls.return_value = MagicMock()
            gemini_cls.return_value = MagicMock()
            build_speech_components(
                RealtimeSpeechConfig(),
                {"google": "gem"},
                "system",
            )
        settings_kwargs = settings_cls.call_args.kwargs
        assert settings_kwargs["model"] == "models/gemini-3.8-live"
        assert settings_kwargs["voice"] == "Zephyr"
        assert "thinking" not in settings_kwargs

    def test_legacy_gemini_realtime_disables_thinking(self) -> None:
        """Gemini 2.5 continues to receive the low-latency thinking override."""
        with (
            patch("src.speech.factory.GeminiLiveLLMService") as gemini_cls,
            patch("src.speech.factory.GeminiLiveLLMService.Settings") as settings_cls,
        ):
            settings_cls.return_value = MagicMock()
            gemini_cls.return_value = MagicMock()
            build_speech_components(
                RealtimeSpeechConfig(
                    model="gemini-2.5-flash-native-audio-preview-12-2025",
                    voice="Puck",
                ),
                {"google": "gem"},
                "system",
            )
        assert settings_cls.call_args.kwargs["thinking"] == {"thinking_budget": 0}

    def test_realtime_still_uses_gemini_live(self) -> None:
        """Realtime presets continue to use Gemini Live."""
        with patch("src.speech.factory.GeminiLiveLLMService") as gemini_cls:
            gemini_cls.return_value = MagicMock()
            result = build_speech_components(
                RealtimeSpeechConfig(),
                {"google": "gem"},
                "system",
            )
        assert result.mode == "realtime"
        gemini_cls.assert_called_once()

    def test_gpt_live_uses_openai_live_adapter(self) -> None:
        """GPT-Live uses the custom delegation-capable WebSocket adapter."""
        with patch("src.speech.factory.OpenAILiveLLMService") as live_cls:
            live_service = MagicMock()
            live_cls.return_value = live_service
            result = build_speech_components(
                RealtimeSpeechConfig(provider="openai"),
                {"openai": "openai-key"},
                "system prompt",
            )

        live_cls.assert_called_once_with(
            api_key="openai-key",
            model="gpt-live-1",
            voice="marin",
            system_instruction="system prompt",
            tools=None,
        )
        assert result.llm is live_service
        assert result.greeting == live_service.send_greeting

    def test_openai_realtime_model_uses_pinned_pipecat_service(self) -> None:
        """The standard OpenAI realtime model uses Pipecat's native adapter."""
        with (
            patch("src.speech.factory.OpenAIRealtimeLLMService") as realtime_cls,
            patch(
                "src.speech.factory.OpenAIRealtimeLLMService.Settings"
            ) as settings_cls,
        ):
            settings_cls.return_value = MagicMock()
            realtime_cls.return_value = MagicMock()
            build_speech_components(
                RealtimeSpeechConfig(
                    provider="openai",
                    model="gpt-realtime-2.1",
                    voice="cedar",
                ),
                {"openai": "openai-key"},
                "system prompt",
            )

        settings_cls.assert_called_once()
        assert settings_cls.call_args.kwargs["model"] == "gpt-realtime-2.1"
        assert settings_cls.call_args.kwargs["system_instruction"] == "system prompt"
        properties = settings_cls.call_args.kwargs["session_properties"]
        assert properties.audio.output.voice == "cedar"
        assert properties.audio.input.transcription is not None
        assert properties.audio.input.turn_detection.silence_duration_ms == 500


@pytest.mark.asyncio
async def test_openai_realtime_resamples_transport_audio_before_provider_send() -> None:
    """The standard OpenAI adapter sends 24 kHz audio to its provider boundary."""
    service = OpenAIRealtimeLLMService(
        api_key="openai-key",
        settings=OpenAIRealtimeLLMService.Settings(
            model="gpt-realtime-2.1",
            system_instruction="system prompt",
        ),
    )
    service._provider_input_resampler.resample = AsyncMock(
        return_value=b"converted-audio"
    )
    service.send_client_event = AsyncMock()

    frame = InputAudioRawFrame(
        audio=b"transport-audio",
        sample_rate=16000,
        num_channels=1,
    )
    await service._send_user_audio(frame)

    service._provider_input_resampler.resample.assert_awaited_once_with(
        b"transport-audio", 16000, 24000
    )
    event = service.send_client_event.await_args.args[0]
    assert base64.b64decode(event.audio) == b"converted-audio"
