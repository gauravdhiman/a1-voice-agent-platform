"""Tests for the OpenAI LLM pipeline builder (speech_providers.llm.openai).

Mirrors ``test_realtime_provider.py``: ``build_openai_llm_config`` returns the
plugin kwargs (no api_key), ``build_openai_llm`` injects the key and constructs
the plugin. Construction opens no network connection, so a fake key is safe.
"""

from livekit.plugins import openai

from shared.voice_agents.speech_config import LLMStageConfig


class TestOpenAiLlmConfig:
    """Tests for build_openai_llm_config (pure kwargs, no api_key)."""

    def test_config_includes_model_override_and_forwards_params(self):
        """A model override and params (e.g. temperature) must flow verbatim."""
        from speech_providers.llm import build_openai_llm_config

        cfg = LLMStageConfig(
            provider="openai",
            model="gpt-4o-mini",
            params={"temperature": 0.5},
        )
        kwargs = build_openai_llm_config(cfg)
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["temperature"] == 0.5
        assert "api_key" not in kwargs
        assert "provider" not in kwargs

    def test_config_omits_model_when_unset(self):
        """When model is None, 'model' is omitted so the plugin default
        (gpt-4.1) applies."""
        from speech_providers.llm import build_openai_llm_config

        kwargs = build_openai_llm_config(LLMStageConfig(provider="openai"))
        assert "model" not in kwargs
        assert kwargs == {}

    def test_config_default_is_empty(self):
        from speech_providers.llm import build_openai_llm_config

        assert build_openai_llm_config() == {}


class TestOpenAiLlmBuild:
    """Tests for build_openai_llm (constructs the real plugin, no network)."""

    def test_build_constructs_openai_llm_with_config(self):
        from speech_providers.llm import build_openai_llm

        cfg = LLMStageConfig(
            provider="openai", model="gpt-4o-mini", params={"temperature": 0.5}
        )
        llm = build_openai_llm(api_key="fake-key", config=cfg)
        assert isinstance(llm, openai.LLM)
        assert llm._opts.model == "gpt-4o-mini"
        assert llm._opts.temperature == 0.5

    def test_build_default_uses_gpt_4_1(self):
        from speech_providers.llm import build_openai_llm

        llm = build_openai_llm(api_key="fake-key")
        assert isinstance(llm, openai.LLM)
        assert llm._opts.model == "gpt-4.1"


class TestCerebrasLlmConfig:
    """Tests for build_cerebras_llm_config (pure kwargs, no api_key).

    Cerebras is a direct OpenAI-compatible LLM provider (high throughput) built
    via ``openai.LLM.with_cerebras``. It mirrors the OpenAI config: ``model``
    only when set (else the plugin default applies) + params forwarded verbatim.
    """

    def test_config_omits_model_when_unset(self):
        from speech_providers.llm import build_cerebras_llm_config

        assert build_cerebras_llm_config(LLMStageConfig(provider="cerebras")) == {}

    def test_config_includes_model_and_forwards_params(self):
        from speech_providers.llm import build_cerebras_llm_config

        cfg = LLMStageConfig(
            provider="cerebras",
            model="llama-4-maverick-17b-128e-instruct",
            params={"temperature": 0.3},
        )
        kwargs = build_cerebras_llm_config(cfg)
        assert kwargs["model"] == "llama-4-maverick-17b-128e-instruct"
        assert kwargs["temperature"] == 0.3
        assert "api_key" not in kwargs
        assert "provider" not in kwargs


class TestCerebrasLlmBuild:
    """Tests for build_cerebras_llm (constructs the real plugin, no network)."""

    def test_build_default_uses_llama4_scout(self):
        """No model override -> with_cerebras default (llama-4-scout) applies."""
        from speech_providers.llm import build_cerebras_llm

        llm = build_cerebras_llm(api_key="fake-key")
        assert isinstance(llm, openai.LLM)
        assert llm._opts.model == "llama-4-scout-17b-16e-instruct"

    def test_build_with_model_and_temperature(self):
        from speech_providers.llm import build_cerebras_llm

        cfg = LLMStageConfig(
            provider="cerebras",
            model="llama-4-maverick-17b-128e-instruct",
            params={"temperature": 0.3},
        )
        llm = build_cerebras_llm(api_key="fake-key", config=cfg)
        assert isinstance(llm, openai.LLM)
        assert llm._opts.model == "llama-4-maverick-17b-128e-instruct"
        assert llm._opts.temperature == 0.3
