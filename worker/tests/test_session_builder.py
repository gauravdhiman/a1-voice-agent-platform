"""Tests for the session builder seam (worker.src.session_builder).

The session builder is the *single* place where the realtime vs pipeline
engines diverge: it takes a :class:`SpeechConfig` + an api-key map and returns
a LiveKit ``AgentSession`` constructed the right way for the engine mode.

Phase 1 wires only the realtime branch (``AgentSession(llm=RealtimeModel)``).
The pipeline branch raises ``NotImplementedError`` until Phase 2.
"""

import pytest
from livekit.agents import AgentSession
from livekit.plugins.google.realtime import RealtimeModel

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
        llm=LLMStageConfig(provider="openai"),
        tts=TTSStageConfig(provider="cartesia"),
    )


class TestBuildAgentSession:
    """Tests for build_agent_session."""

    def test_realtime_session_has_realtime_llm_and_userdata(self):
        """A realtime config must produce an AgentSession whose llm is the
        RealtimeModel and whose userdata is forwarded — matching today's
        construction (AgentSession(llm=model, userdata=...))."""
        from session_builder import build_agent_session

        session = build_agent_session(
            speech_config=default_realtime_config(),
            api_keys={"google": "fake-key"},
            userdata={"agent_id": "a1", "agent_name": "Test Agent"},
        )
        assert isinstance(session, AgentSession)
        assert isinstance(session._llm, RealtimeModel)
        assert session.userdata == {"agent_id": "a1", "agent_name": "Test Agent"}
        # Realtime mode: no separate STT/TTS plugins (the model handles both).
        assert session._stt is None
        assert session._tts is None

    def test_realtime_session_uses_config_voice(self):
        """The session's realtime model must reflect the per-agent config
        (voice override flows through to the constructed model)."""
        from session_builder import build_agent_session

        cfg = RealtimeSpeechConfig(voice="Charon")
        session = build_agent_session(
            speech_config=cfg,
            api_keys={"google": "fake-key"},
            userdata={},
        )
        assert session._llm._opts.voice == "Charon"

    def test_pipeline_session_raises_not_implemented(self):
        """Phase 1 does not build pipeline sessions yet — explicit failure so a
        pipeline config can't silently degrade to realtime. Phase 2 wires it."""
        from session_builder import build_agent_session

        with pytest.raises(NotImplementedError):
            build_agent_session(speech_config=_pipeline_cfg(), api_keys={}, userdata={})

    def test_pipeline_components_raise_not_implemented(self, monkeypatch):
        """Even if the registry handed back PipelineComponents (Phase 2 will),
        the session builder must refuse to assemble a pipeline session until
        Phase 2 wires it — guarded independently of the registry's own check."""
        import session_builder as sb
        from speech_providers.registry import PipelineComponents

        monkeypatch.setattr(
            sb,
            "build_session_components",
            lambda *_a, **_k: PipelineComponents(
                stt=object(), llm=object(), tts=object()
            ),
        )
        with pytest.raises(NotImplementedError):
            sb.build_agent_session(
                speech_config=_pipeline_cfg(), api_keys={}, userdata={}
            )

    def test_unknown_components_raise_type_error(self, monkeypatch):
        """A future component variant the builder does not know about must fail
        loudly rather than return an unconfigured AgentSession."""
        import session_builder as sb

        monkeypatch.setattr(sb, "build_session_components", lambda *_a, **_k: object())
        with pytest.raises(TypeError):
            sb.build_agent_session(
                speech_config=default_realtime_config(),
                api_keys={"google": "fake"},
                userdata={},
            )
