"""Tests for Pipecat speech-component factory provider dispatch."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
)
from src.speech.factory import build_speech_components


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
                _pipeline(stt_model="nova-3", llm_model="gpt-4o-mini", tts_voice="voice-1"),
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
        # Gemma/OpenRouter reasoning tokens must not stream into TTS content.
        assert settings.extra == {
            "reasoning": {"effort": "none", "exclude": True},
        }

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
        with pytest.raises(ValueError, match="Unsupported Pipecat STT provider"):
            build_speech_components(
                _pipeline(stt="assemblyai"),
                {"assemblyai": "x", "openai": "sk", "cartesia": "cart"},
                "system",
            )

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
