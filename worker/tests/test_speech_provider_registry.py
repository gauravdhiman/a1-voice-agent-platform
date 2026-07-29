"""Tests for the speech provider factory registry.

The registry maps a :class:`SpeechConfig` to the concrete LiveKit plugin
instance(s) the session needs — either a single RealtimeModel (realtime mode)
or a set of stage plugins (pipeline mode). Phase 1 wires only the realtime
branch; the pipeline branch raises ``NotImplementedError`` until Phase 2
adds the STT/LLM/TTS/VAD/turn-detection factories.
"""

import pytest

from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
    default_realtime_config,
)


def _pipeline_cfg() -> PipelineSpeechConfig:
    return PipelineSpeechConfig(
        stt=STTStageConfig(provider="deepgram"),
        llm=LLMStageConfig(provider="openai", model="gpt-4o-mini"),
        tts=TTSStageConfig(provider="cartesia"),
    )


class TestBuildSessionComponents:
    """Tests for build_session_components dispatch."""

    def test_realtime_config_returns_realtime_components(self):
        """A realtime config + a google api key must yield RealtimeComponents
        carrying a constructed RealtimeModel (the single plugin passed as
        llm= to AgentSession)."""
        from livekit.plugins.google.realtime import RealtimeModel
        from speech_providers.registry import (
            RealtimeComponents,
            build_session_components,
        )

        comps = build_session_components(
            default_realtime_config(), api_keys={"google": "fake-key"}
        )
        assert isinstance(comps, RealtimeComponents)
        assert isinstance(comps.llm, RealtimeModel)

    def test_realtime_passes_google_key_and_config(self, monkeypatch):
        """The registry must read the Google key from the api_keys map and
        forward the concrete config to the realtime provider builder."""
        import speech_providers.registry as registry

        captured: dict = {}
        sentinel = object()

        def fake_build(api_key, config=None):
            captured["api_key"] = api_key
            captured["config"] = config
            return sentinel

        monkeypatch.setattr(registry, "build_realtime_model", fake_build)

        cfg = RealtimeSpeechConfig(voice="Charon")
        comps = registry.build_session_components(cfg, api_keys={"google": "KEY-123"})
        assert captured["api_key"] == "KEY-123"
        assert captured["config"] is cfg
        assert comps.llm is sentinel

    def test_realtime_missing_google_key_raises(self):
        """A realtime config without a google key in the map is a misconfig —
        fail fast with a clear error rather than passing None to the provider."""
        from speech_providers.registry import build_session_components

        with pytest.raises(ValueError, match="google"):
            build_session_components(default_realtime_config(), api_keys={})

    def test_pipeline_config_raises_not_implemented(self):
        """Phase 1 does not implement the pipeline factories yet — the branch
        must fail explicitly so a pipeline config can't silently fall through
        to realtime. Phase 2 replaces this with real stage factories."""
        from speech_providers.registry import build_session_components

        with pytest.raises(NotImplementedError):
            build_session_components(_pipeline_cfg(), api_keys={})

    def test_unknown_config_type_raises_type_error(self):
        """A config object that is neither realtime nor pipeline (a future
        variant, or a misuse) must be rejected with a clear TypeError rather
        than silently returning realtime components."""
        from speech_providers.registry import build_session_components

        with pytest.raises(TypeError):
            build_session_components(object(), api_keys={})  # type: ignore[arg-type]
