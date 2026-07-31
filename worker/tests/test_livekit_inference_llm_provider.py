"""Tests for the LiveKit Inference LLM pipeline builder.

Same pattern as the other Inference providers, with one key difference:
``inference.LLM`` takes chat-completion options (``temperature``, ``max_tokens``,
...) in ``extra_kwargs``, NOT as top-level kwargs. The config function routes
the known top-level kwargs (``provider`` / ``base_url`` / ``inference_class``)
directly and packs the rest into ``extra_kwargs`` so a common
``temperature`` param does not TypeError.
"""

import pytest
from livekit.agents import inference

from shared.voice_agents.speech_config import LLMStageConfig


class TestLiveKitInferenceLlmConfig:
    """Tests for build_livekit_inference_llm_config (pure kwargs, no credentials)."""

    def test_config_requires_model(self):
        from speech_providers.llm import build_livekit_inference_llm_config

        with pytest.raises(ValueError, match="model"):
            build_livekit_inference_llm_config(
                LLMStageConfig(provider="livekit_inference")
            )

    def test_config_routes_temperature_to_extra_kwargs(self):
        """temperature is NOT a top-level inference.LLM kwarg — it must land in
        extra_kwargs; provider/base_url/inference_class stay top-level."""
        from speech_providers.llm import build_livekit_inference_llm_config

        cfg = LLMStageConfig(
            provider="livekit_inference",
            model="google/gemma-4-31b-it",
            params={"temperature": 0.5, "base_url": "https://custom.example/v1"},
        )
        kwargs = build_livekit_inference_llm_config(cfg)
        assert kwargs["model"] == "google/gemma-4-31b-it"
        assert kwargs["base_url"] == "https://custom.example/v1"
        assert kwargs["extra_kwargs"] == {"temperature": 0.5}
        assert "api_key" not in kwargs
        assert "api_secret" not in kwargs
        assert "provider" not in kwargs

    def test_config_no_params_omits_extra_kwargs(self):
        from speech_providers.llm import build_livekit_inference_llm_config

        cfg = LLMStageConfig(
            provider="livekit_inference", model="google/gemma-4-31b-it"
        )
        kwargs = build_livekit_inference_llm_config(cfg)
        assert kwargs == {"model": "google/gemma-4-31b-it"}
        assert "extra_kwargs" not in kwargs


class TestLiveKitInferenceLlmBuild:
    """Tests for build_livekit_inference_llm (constructs the real plugin, no network)."""

    def test_build_constructs_inference_llm_with_env_creds(self):
        from speech_providers.llm import build_livekit_inference_llm

        cfg = LLMStageConfig(
            provider="livekit_inference",
            model="google/gemma-4-31b-it",
            params={"temperature": 0.5},
        )
        llm = build_livekit_inference_llm(cfg)
        assert isinstance(llm, inference.LLM)
        assert llm._opts.model == "google/gemma-4-31b-it"
        assert llm._opts.extra_kwargs == {"temperature": 0.5}
        assert llm._opts.api_key == "test-api-key"
        assert llm._opts.api_secret == "test-api-secret"

    def test_build_accepts_explicit_creds(self):
        from speech_providers.llm import build_livekit_inference_llm

        cfg = LLMStageConfig(
            provider="livekit_inference", model="google/gemma-4-31b-it"
        )
        llm = build_livekit_inference_llm(
            cfg, api_key="explicit-key", api_secret="explicit-secret"
        )
        assert llm._opts.api_key == "explicit-key"
        assert llm._opts.api_secret == "explicit-secret"

    def test_build_without_key_raises(self, monkeypatch):
        from speech_providers.llm import build_livekit_inference_llm

        monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
        monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
        with pytest.raises(ValueError, match="LiveKit"):
            build_livekit_inference_llm(
                LLMStageConfig(
                    provider="livekit_inference", model="google/gemma-4-31b-it"
                )
            )
