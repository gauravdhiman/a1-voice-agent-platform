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

    def test_pipeline_session_assembles_stt_llm_tts_and_vad(self):
        """Phase 2: a {deepgram, openai, cartesia} pipeline config must produce
        an AgentSession with the per-stage plugins set on _stt/_llm/_tts and an
        explicit Silero VAD on _vad (registry always builds one even when
        config.vad is None). Construction opens no network, so fake keys are
        safe. userdata must be forwarded."""
        from livekit.plugins import cartesia, deepgram, openai, silero
        from session_builder import build_agent_session

        session = build_agent_session(
            speech_config=_pipeline_cfg(),
            api_keys={"deepgram": "fake", "openai": "fake", "cartesia": "fake"},
            userdata={"agent_id": "a1", "agent_name": "Test Agent"},
        )
        assert isinstance(session, AgentSession)
        assert isinstance(session._stt, deepgram.STT)
        assert isinstance(session._llm, openai.LLM)
        assert isinstance(session._tts, cartesia.TTS)
        # Explicit standalone Silero VAD (not the bundled inference default).
        assert isinstance(session._vad, silero.VAD)
        assert session.userdata == {"agent_id": "a1", "agent_name": "Test Agent"}

    def test_pipeline_session_omits_none_vad_and_turn_detection(self, monkeypatch):
        """When the registry returns PipelineComponents with vad=None and
        turn_detection=None, the builder must OMIT them (not pass None) —
        vad=None opts out of VAD entirely; turn_detection has no valid None.
        The session must still construct with the stage plugins set."""
        import session_builder as sb
        from livekit.plugins import cartesia, deepgram, openai
        from speech_providers.registry import PipelineComponents

        comps = PipelineComponents(
            stt=deepgram.STT(api_key="fake"),
            llm=openai.LLM(api_key="fake"),
            tts=cartesia.TTS(api_key="fake"),
            vad=None,
            turn_detection=None,
        )
        monkeypatch.setattr(sb, "build_session_components", lambda *_a, **_k: comps)

        session = sb.build_agent_session(
            speech_config=_pipeline_cfg(), api_keys={}, userdata={}
        )
        assert isinstance(session, AgentSession)
        assert isinstance(session._stt, deepgram.STT)
        assert isinstance(session._llm, openai.LLM)
        assert isinstance(session._tts, cartesia.TTS)
        # vad omitted -> AgentSession applies its own default VAD (not None).
        assert session._vad is not None

    def test_pipeline_session_forwards_non_none_turn_detection(self, monkeypatch):
        """When PipelineComponents.turn_detection is non-None, the builder must
        pass it through to AgentSession (the None-omission path is covered
        separately). Uses a fake AgentSession so the test does not depend on
        AgentSession accepting an arbitrary turn-detection object."""
        import session_builder as sb
        from speech_providers.registry import PipelineComponents

        td_sentinel = object()
        recorded: dict = {}

        class FakeSession:
            def __init__(self, **kwargs):
                recorded.update(kwargs)

        monkeypatch.setattr(sb, "AgentSession", FakeSession)
        monkeypatch.setattr(
            sb,
            "build_session_components",
            lambda *_a, **_k: PipelineComponents(
                stt=object(), llm=object(), tts=object(), turn_detection=td_sentinel
            ),
        )

        sb.build_agent_session(speech_config=_pipeline_cfg(), api_keys={}, userdata={})
        assert recorded["turn_detection"] is td_sentinel
        # vad=None -> omitted (not passed as None).
        assert "vad" not in recorded

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
