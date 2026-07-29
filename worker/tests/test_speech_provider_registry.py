"""Tests for the speech provider factory registry.

The registry maps a :class:`SpeechConfig` to the concrete LiveKit plugin
instance(s) the session needs — either a single RealtimeModel (realtime mode)
or a set of stage plugins (pipeline mode). Phase 1 wired the realtime branch;
Phase 2 wires the pipeline branch: per-stage dispatch on the stage's
``provider``, per-provider key guards, always-on standalone Silero VAD, and
turn-detection deferred to Phase 5.
"""

import pytest

from shared.voice_agents.speech_config import (
    LLMStageConfig,
    PipelineSpeechConfig,
    RealtimeSpeechConfig,
    STTStageConfig,
    TTSStageConfig,
    TurnDetectionConfig,
    VADConfig,
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

    def test_pipeline_config_returns_pipeline_components(self, monkeypatch):
        """Phase 2: a {deepgram, openai, cartesia} pipeline config must yield
        PipelineComponents built via the per-stage factories. The registry reads
        each stage's provider-matched key from api_keys and forwards the stage
        config; vad=None still builds a default Silero VAD; turn_detection=None
        stays None (deferred to Phase 5)."""
        import speech_providers.registry as registry
        from speech_providers.registry import (
            PipelineComponents,
            build_session_components,
        )

        captured: dict = {}
        stt_sentinel, llm_sentinel, tts_sentinel, vad_sentinel = (
            object(),
            object(),
            object(),
            object(),
        )

        monkeypatch.setitem(
            registry.STT_BUILDERS,
            "deepgram",
            lambda api_key, config=None: captured.update(stt_api_key=api_key, stt_config=config) or stt_sentinel,  # type: ignore[return-value]
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS,
            "openai",
            lambda api_key, config=None: captured.update(llm_api_key=api_key, llm_config=config) or llm_sentinel,  # type: ignore[return-value]
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS,
            "cartesia",
            lambda api_key, config=None: captured.update(tts_api_key=api_key, tts_config=config) or tts_sentinel,  # type: ignore[return-value]
        )
        monkeypatch.setitem(
            registry.VAD_BUILDERS,
            "silero",
            lambda config=None: captured.setdefault("vad_config", config) or vad_sentinel,  # type: ignore[return-value]
        )

        cfg = _pipeline_cfg()
        comps = build_session_components(
            cfg,
            api_keys={"deepgram": "DKEY", "openai": "OKEY", "cartesia": "CKEY"},
        )
        assert isinstance(comps, PipelineComponents)
        assert comps.stt is stt_sentinel
        assert comps.llm is llm_sentinel
        assert comps.tts is tts_sentinel
        assert comps.vad is vad_sentinel
        assert comps.turn_detection is None
        # Each stage got the right key + its own stage config object.
        assert captured["stt_api_key"] == "DKEY"
        assert captured["stt_config"] is cfg.stt
        assert captured["llm_api_key"] == "OKEY"
        assert captured["llm_config"] is cfg.llm
        assert captured["tts_api_key"] == "CKEY"
        assert captured["tts_config"] is cfg.tts
        # vad=None in config -> registry builds the default Silero (None config).
        assert captured["vad_config"] is None

    def test_pipeline_missing_stt_key_raises(self):
        """A pipeline config whose STT provider's key is absent must fail fast
        with a clear error naming the provider, not pass None to the builder."""
        from speech_providers.registry import build_session_components

        with pytest.raises(ValueError, match="deepgram"):
            build_session_components(
                _pipeline_cfg(), api_keys={"openai": "O", "cartesia": "C"}
            )

    def test_pipeline_missing_llm_key_raises(self):
        from speech_providers.registry import build_session_components

        with pytest.raises(ValueError, match="openai"):
            build_session_components(
                _pipeline_cfg(), api_keys={"deepgram": "D", "cartesia": "C"}
            )

    def test_pipeline_missing_tts_key_raises(self):
        from speech_providers.registry import build_session_components

        with pytest.raises(ValueError, match="cartesia"):
            build_session_components(
                _pipeline_cfg(), api_keys={"deepgram": "D", "openai": "O"}
            )

    def test_pipeline_unsupported_stt_provider_raises(self):
        """An unsupported STT provider must raise NotImplementedError naming
        the stage, listing supported providers."""
        from speech_providers.registry import build_session_components

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="assemblyai"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        with pytest.raises(NotImplementedError, match="stt"):
            build_session_components(
                cfg,
                api_keys={"assemblyai": "A", "openai": "O", "cartesia": "C"},
            )

    def test_pipeline_unsupported_vad_provider_raises(self):
        """A non-silero VAD provider is not wired in Phase 2 -> NotImplementedError."""
        from speech_providers.registry import build_session_components

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="deepgram"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
            vad=VADConfig(provider="webrtc"),
        )
        with pytest.raises(NotImplementedError, match="vad"):
            build_session_components(
                cfg,
                api_keys={"deepgram": "D", "openai": "O", "cartesia": "C"},
            )

    def test_pipeline_turn_detection_non_none_raises(self):
        """A non-None turn_detection config is deferred to Phase 5 -> explicit
        NotImplementedError so it can't be silently ignored."""
        from speech_providers.registry import build_session_components

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="deepgram"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
            turn_detection=TurnDetectionConfig(provider="rnt"),
        )
        with pytest.raises(NotImplementedError, match="turn_detection"):
            build_session_components(
                cfg,
                api_keys={"deepgram": "D", "openai": "O", "cartesia": "C"},
            )

    def test_pipeline_vad_none_builds_default_silero(self, monkeypatch):
        """vad=None must NOT leave PipelineComponents.vad as None — the registry
        always builds an explicit standalone Silero VAD to keep the pipeline off
        the bundled livekit.agents.inference VAD path (deferred bug #7)."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        vad_sentinel = object()
        monkeypatch.setitem(
            registry.VAD_BUILDERS, "silero", lambda config=None: vad_sentinel
        )
        monkeypatch.setitem(
            registry.STT_BUILDERS, "deepgram", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS, "openai", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        comps = build_session_components(
            _pipeline_cfg(),
            api_keys={"deepgram": "D", "openai": "O", "cartesia": "C"},
        )
        assert comps.vad is vad_sentinel

    def test_pipeline_vad_silero_config_dispatches_to_builder(self, monkeypatch):
        """A non-None VADConfig(provider='silero') must dispatch through
        VAD_BUILDERS (distinct from the vad=None default path) and forward the
        config object to the builder."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        captured: dict = {}
        vad_sentinel = object()

        def fake_vad(config=None):
            captured["vad_cfg"] = config
            return vad_sentinel

        monkeypatch.setitem(registry.VAD_BUILDERS, "silero", fake_vad)
        monkeypatch.setitem(
            registry.STT_BUILDERS, "deepgram", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS, "openai", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        vad_cfg = VADConfig(provider="silero", params={"min_silence_duration": 0.3})
        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="deepgram"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
            vad=vad_cfg,
        )
        comps = build_session_components(
            cfg, api_keys={"deepgram": "D", "openai": "O", "cartesia": "C"}
        )
        assert comps.vad is vad_sentinel
        assert captured["vad_cfg"] is vad_cfg

    def test_unknown_config_type_raises_type_error(self):
        """A config object that is neither realtime nor pipeline (a future
        variant, or a misuse) must be rejected with a clear TypeError rather
        than silently returning realtime components."""
        from speech_providers.registry import build_session_components

        with pytest.raises(TypeError):
            build_session_components(object(), api_keys={})  # type: ignore[arg-type]


class TestPipelineLiveKitInferenceAndCerebrasDispatch:
    """Phase 2b: LiveKit Inference + Cerebras dispatch.

    Inference stages (``provider == "inference"``) take a special path: they use
    a single LiveKit Cloud auth (api_key + api_secret) instead of a per-stage
    provider key, so they bypass the keyed ``*_BUILDERS`` tables and the
    per-provider key guard. Cerebras is a direct OpenAI-compatible LLM, so it
    rides the normal keyed path with a ``"cerebras"`` entry in LLM_BUILDERS. A
    pipeline may mix the two freely (e.g. Inference STT + Cerebras LLM +
    Inference TTS) — that is the "mixed preset" direction (still just a
    pipeline; ``type`` stays ``{realtime, pipeline}``).
    """

    def test_inference_stt_dispatches_through_inference_table(self, monkeypatch):
        """An inference STT stage must dispatch through
        LIVEKIT_INFERENCE_STAGE_BUILDERS (NOT the keyed STT_BUILDERS table) and forward
        the stage config — no per-stage key guard fires."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        captured: dict = {}
        stt_sentinel = object()

        def fake_inference_stt(config=None, **kwargs):
            captured["stt_config"] = config
            captured["stt_kwargs"] = kwargs
            return stt_sentinel

        monkeypatch.setitem(
            registry.LIVEKIT_INFERENCE_STAGE_BUILDERS, "stt", fake_inference_stt
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS, "openai", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="livekit_inference", model="deepgram/nova-3"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        comps = build_session_components(cfg, api_keys={"openai": "O", "cartesia": "C"})
        assert comps.stt is stt_sentinel
        assert captured["stt_config"] is cfg.stt

    def test_inference_stage_needs_no_provider_key(self, monkeypatch):
        """An inference stage must NOT raise the per-provider key guard even
        when its provider ('inference') is absent from api_keys — Inference uses
        the LiveKit key, not a per-stage provider key."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        monkeypatch.setitem(
            registry.LIVEKIT_INFERENCE_STAGE_BUILDERS,
            "stt",
            lambda config=None, **kwargs: object(),
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS, "openai", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="livekit_inference", model="deepgram/nova-3"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        # No 'inference' key in api_keys — must not raise ValueError.
        comps = build_session_components(cfg, api_keys={"openai": "O", "cartesia": "C"})
        assert comps.stt is not None

    def test_cerebras_llm_dispatches_via_keyed_path(self, monkeypatch):
        """Cerebras rides the normal keyed path: read the 'cerebras' key from
        api_keys and forward the stage config to the LLM_BUILDERS entry."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        captured: dict = {}
        llm_sentinel = object()

        def fake_cerebras(api_key, config=None):
            captured["llm_api_key"] = api_key
            captured["llm_config"] = config
            return llm_sentinel

        monkeypatch.setitem(registry.LLM_BUILDERS, "cerebras", fake_cerebras)
        monkeypatch.setitem(
            registry.STT_BUILDERS, "deepgram", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="deepgram"),
            llm=LLMStageConfig(
                provider="cerebras", model="llama-4-maverick-17b-128e-instruct"
            ),
            tts=TTSStageConfig(provider="cartesia"),
        )
        comps = build_session_components(
            cfg, api_keys={"deepgram": "D", "cerebras": "CK", "cartesia": "C"}
        )
        assert comps.llm is llm_sentinel
        assert captured["llm_api_key"] == "CK"
        assert captured["llm_config"] is cfg.llm

    def test_cerebras_missing_key_raises(self):
        """Cerebras is a keyed direct provider — a missing 'cerebras' key must
        fail fast with a clear error, same guard as deepgram/openai/cartesia."""
        from speech_providers.registry import build_session_components

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="deepgram"),
            llm=LLMStageConfig(provider="cerebras"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        with pytest.raises(ValueError, match="cerebras"):
            build_session_components(cfg, api_keys={"deepgram": "D", "cartesia": "C"})

    def test_mixed_inference_and_direct_providers(self, monkeypatch):
        """A pipeline mixing Inference stages (stt, tts) with a direct provider
        (cerebras llm) must dispatch each correctly — the 'mixed preset'
        direction. This is still just a pipeline (no third preset type)."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        stt_sentinel, tts_sentinel, llm_sentinel = object(), object(), object()

        monkeypatch.setitem(
            registry.LIVEKIT_INFERENCE_STAGE_BUILDERS,
            "stt",
            lambda config=None, **kwargs: stt_sentinel,
        )
        monkeypatch.setitem(
            registry.LIVEKIT_INFERENCE_STAGE_BUILDERS,
            "tts",
            lambda config=None, **kwargs: tts_sentinel,
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS,
            "cerebras",
            lambda api_key, config=None: llm_sentinel,
        )
        monkeypatch.setitem(
            registry.VAD_BUILDERS, "silero", lambda config=None: object()
        )

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="livekit_inference", model="deepgram/nova-3"),
            llm=LLMStageConfig(
                provider="cerebras", model="llama-4-maverick-17b-128e-instruct"
            ),
            tts=TTSStageConfig(provider="livekit_inference", model="cartesia/sonic-3"),
        )
        comps = build_session_components(cfg, api_keys={"cerebras": "CK"})
        assert comps.stt is stt_sentinel
        assert comps.llm is llm_sentinel
        assert comps.tts is tts_sentinel

    def test_inference_unknown_stage_name_raises(self):
        """Defensive guard: _build_livekit_inference_stage with a stage name that is not
        stt/llm/tts must raise NotImplementedError (unreachable via the public
        API, which only ever passes those three)."""
        from speech_providers.registry import _build_livekit_inference_stage

        with pytest.raises(NotImplementedError, match="Inference"):
            _build_livekit_inference_stage(
                "vad",
                STTStageConfig(provider="livekit_inference", model="deepgram/nova-3"),
                api_keys={},
            )

    def test_inference_stage_injects_livekit_key_from_api_keys(self, monkeypatch):
        """Phase 3: when api_keys carries a nested 'livekit' {api_key, api_secret},
        the Inference builder is called with those kwargs (tenant BYO LiveKit key
        for Inference — injected by the per-org key_resolver)."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        captured: dict = {}

        def fake_inference_stt(config=None, **kwargs):
            captured["stt_kwargs"] = kwargs
            return object()

        monkeypatch.setitem(
            registry.LIVEKIT_INFERENCE_STAGE_BUILDERS, "stt", fake_inference_stt
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS, "openai", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="livekit_inference", model="deepgram/nova-3"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        build_session_components(
            cfg,
            api_keys={
                "openai": "O",
                "cartesia": "C",
                "livekit": {"api_key": "tenant-lk", "api_secret": "tenant-lks"},
            },
        )
        assert captured["stt_kwargs"]["api_key"] == "tenant-lk"
        assert captured["stt_kwargs"]["api_secret"] == "tenant-lks"

    def test_inference_stage_falls_back_to_none_when_livekit_absent(self, monkeypatch):
        """Phase 3: when api_keys has no 'livekit' entry, the Inference builder is
        called with api_key=None / api_secret=None — it then falls back to the
        platform LIVEKIT_API_KEY/LIVEKIT_API_SECRET env (Phase 2b behavior)."""
        import speech_providers.registry as registry
        from speech_providers.registry import build_session_components

        captured: dict = {}

        def fake_inference_stt(config=None, **kwargs):
            captured["stt_kwargs"] = kwargs
            return object()

        monkeypatch.setitem(
            registry.LIVEKIT_INFERENCE_STAGE_BUILDERS, "stt", fake_inference_stt
        )
        monkeypatch.setitem(
            registry.LLM_BUILDERS, "openai", lambda api_key, config=None: object()
        )
        monkeypatch.setitem(
            registry.TTS_BUILDERS, "cartesia", lambda api_key, config=None: object()
        )

        cfg = PipelineSpeechConfig(
            stt=STTStageConfig(provider="livekit_inference", model="deepgram/nova-3"),
            llm=LLMStageConfig(provider="openai"),
            tts=TTSStageConfig(provider="cartesia"),
        )
        build_session_components(cfg, api_keys={"openai": "O", "cartesia": "C"})
        assert captured["stt_kwargs"]["api_key"] is None
        assert captured["stt_kwargs"]["api_secret"] is None
