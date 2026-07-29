"""Tests for the LiveKit Inference TTS pipeline builder.

Same pattern as the other Inference providers. ``inference.TTS`` takes ``voice``
and ``language`` as top-level kwargs, but provider-specific options (Cartesia
``speed``/``emotion``, etc.) route into ``extra_kwargs``.
"""

import pytest
from livekit.agents import inference

from shared.voice_agents.speech_config import TTSStageConfig


class TestLiveKitInferenceTtsConfig:
    """Tests for build_livekit_inference_tts_config (pure kwargs, no credentials)."""

    def test_config_requires_model(self):
        from speech_providers.tts import build_livekit_inference_tts_config

        with pytest.raises(ValueError, match="model"):
            build_livekit_inference_tts_config(
                TTSStageConfig(provider="livekit_inference")
            )

    def test_config_routes_voice_top_level_speed_to_extra_kwargs(self):
        """voice is top-level on inference.TTS; provider-specific options
        (speed) route into extra_kwargs."""
        from speech_providers.tts import build_livekit_inference_tts_config

        cfg = TTSStageConfig(
            provider="livekit_inference",
            model="cartesia/sonic-3",
            params={"voice": "abc-uuid", "speed": 1.2},
        )
        kwargs = build_livekit_inference_tts_config(cfg)
        assert kwargs["model"] == "cartesia/sonic-3"
        assert kwargs["voice"] == "abc-uuid"
        assert kwargs["extra_kwargs"] == {"speed": 1.2}
        assert "api_key" not in kwargs
        assert "api_secret" not in kwargs
        assert "provider" not in kwargs

    def test_config_no_params_omits_extra_kwargs(self):
        from speech_providers.tts import build_livekit_inference_tts_config

        cfg = TTSStageConfig(provider="livekit_inference", model="cartesia/sonic-3")
        kwargs = build_livekit_inference_tts_config(cfg)
        assert kwargs == {"model": "cartesia/sonic-3"}
        assert "extra_kwargs" not in kwargs


class TestLiveKitInferenceTtsBuild:
    """Tests for build_livekit_inference_tts (constructs the real plugin, no network)."""

    def test_build_constructs_inference_tts_with_env_creds(self):
        from speech_providers.tts import build_livekit_inference_tts

        cfg = TTSStageConfig(
            provider="livekit_inference",
            model="cartesia/sonic-3",
            params={"voice": "abc-uuid"},
        )
        tts = build_livekit_inference_tts(cfg)
        assert isinstance(tts, inference.TTS)
        assert tts._opts.model == "cartesia/sonic-3"
        assert tts._opts.voice == "abc-uuid"
        assert tts._opts.api_key == "test-api-key"
        assert tts._opts.api_secret == "test-api-secret"

    def test_build_accepts_explicit_creds(self):
        from speech_providers.tts import build_livekit_inference_tts

        cfg = TTSStageConfig(provider="livekit_inference", model="cartesia/sonic-3")
        tts = build_livekit_inference_tts(
            cfg, api_key="explicit-key", api_secret="explicit-secret"
        )
        assert tts._opts.api_key == "explicit-key"
        assert tts._opts.api_secret == "explicit-secret"

    def test_build_without_key_raises(self, monkeypatch):
        from speech_providers.tts import build_livekit_inference_tts

        monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
        monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
        with pytest.raises(ValueError, match="LiveKit"):
            build_livekit_inference_tts(
                TTSStageConfig(provider="livekit_inference", model="cartesia/sonic-3")
            )
