"""Tests for the LiveKit Inference STT pipeline builder.

LiveKit Inference (``livekit.agents.inference``) gives access to many STT models
through a single LiveKit Cloud auth (``api_key`` + ``api_secret``). The builder
mirrors the other pipeline providers: a pure ``build_livekit_inference_stt_config``
(plugin kwargs, no credentials — deterministic, unit-testable) +
``build_livekit_inference_stt`` (constructs the plugin, no network until start).

Phase 2b reads the platform's LiveKit key from the environment; the
``api_key``/``api_secret`` keyword args are the forward-compatible seam Phase 3's
per-org ``key_resolver`` will inject into. The config function REQUIRES a model
string (Inference has no implicit default) and splits ``params`` into top-level
constructor kwargs vs ``extra_kwargs`` (provider-specific options like Deepgram
``keywords`` are not top-level on ``inference.STT``).
"""

import pytest
from livekit.agents import inference

from shared.voice_agents.speech_config import STTStageConfig


class TestLiveKitInferenceSttConfig:
    """Tests for build_livekit_inference_stt_config (pure kwargs, no credentials)."""

    def test_config_requires_model(self):
        """Inference has no implicit default model — a missing model is a
        misconfig, fail fast with a clear error rather than letting the plugin
        raise an opaque one."""
        from speech_providers.stt import build_livekit_inference_stt_config

        with pytest.raises(ValueError, match="model"):
            build_livekit_inference_stt_config(
                STTStageConfig(provider="livekit_inference")
            )

    def test_config_includes_model_and_splits_params(self):
        """model is top-level; known top-level params (language) stay top-level;
        provider-specific params (keywords) route into extra_kwargs."""
        from speech_providers.stt import build_livekit_inference_stt_config

        cfg = STTStageConfig(
            provider="livekit_inference",
            model="deepgram/nova-3",
            params={"language": "en-US", "keywords": ["foo", "bar"]},
        )
        kwargs = build_livekit_inference_stt_config(cfg)
        assert kwargs["model"] == "deepgram/nova-3"
        assert kwargs["language"] == "en-US"
        assert kwargs["extra_kwargs"] == {"keywords": ["foo", "bar"]}
        # credentials are injected by build_livekit_inference_stt, never by the config fn.
        assert "api_key" not in kwargs
        assert "api_secret" not in kwargs
        # provider is the dispatch key, not a plugin kwarg.
        assert "provider" not in kwargs

    def test_config_no_params_omits_extra_kwargs(self):
        """When params is empty, extra_kwargs must be omitted (NOT passed as
        None) so the plugin's own default applies."""
        from speech_providers.stt import build_livekit_inference_stt_config

        cfg = STTStageConfig(provider="livekit_inference", model="deepgram/nova-3")
        kwargs = build_livekit_inference_stt_config(cfg)
        assert kwargs == {"model": "deepgram/nova-3"}
        assert "extra_kwargs" not in kwargs


class TestLiveKitInferenceSttBuild:
    """Tests for build_livekit_inference_stt (constructs the real plugin, no network)."""

    def test_build_constructs_inference_stt_with_env_creds(self):
        """With no explicit creds, the builder reads LIVEKIT_API_KEY /
        LIVEKIT_API_SECRET from the env (set in conftest) — Phase 2b's
        platform-key path."""
        from speech_providers.stt import build_livekit_inference_stt

        cfg = STTStageConfig(
            provider="livekit_inference",
            model="deepgram/nova-3",
            params={"language": "en-US"},
        )
        stt = build_livekit_inference_stt(cfg)
        assert isinstance(stt, inference.STT)
        assert stt._opts.model == "deepgram/nova-3"
        assert stt._opts.language == "en-US"
        assert stt._opts.api_key == "test-api-key"
        assert stt._opts.api_secret == "test-api-secret"

    def test_build_accepts_explicit_creds(self):
        """Explicit api_key/api_secret override the env — the Phase 3 per-org
        injection path. Proves the builder is forward-compatible."""
        from speech_providers.stt import build_livekit_inference_stt

        cfg = STTStageConfig(provider="livekit_inference", model="deepgram/nova-3")
        stt = build_livekit_inference_stt(
            cfg, api_key="explicit-key", api_secret="explicit-secret"
        )
        assert stt._opts.api_key == "explicit-key"
        assert stt._opts.api_secret == "explicit-secret"

    def test_build_without_key_raises(self, monkeypatch):
        """No explicit creds AND no env key is a misconfig — fail fast with a
        clear error rather than constructing an unauthenticated plugin."""
        from speech_providers.stt import build_livekit_inference_stt

        monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
        monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
        with pytest.raises(ValueError, match="LiveKit"):
            build_livekit_inference_stt(
                STTStageConfig(provider="livekit_inference", model="deepgram/nova-3")
            )
