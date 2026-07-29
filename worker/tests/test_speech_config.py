"""Tests for the per-agent speech engine configuration models.

``shared.voice_agents.speech_config`` defines the typed contract between the
agent DB config, the backend CRUD API, and the worker's session builder. It
supports two engine modes — ``realtime`` (end-to-end speech model) and
``pipeline`` (modular STT -> LLM -> TTS) — via a discriminated union on
``engine_mode``.

These tests guard:

* **Behavior-neutrality of the Phase 1 refactor:** the realtime defaults must
  exactly match the constants previously hardcoded in
  ``worker/src/realtime_config.py`` (model, voice, temperature, endpointing).
  This is what lets ``default_realtime_config()`` reproduce today's behavior.
* **Discriminated-union dispatch:** a plain dict with ``engine_mode`` resolves to
  the right concrete config, so the JSONB column (Phase 3) can be validated.
* **Per-stage modularity:** pipeline stage configs carry provider/model/params.
"""

import pytest
from pydantic import ValidationError


class TestRealtimeSpeechConfig:
    """Tests for the realtime (end-to-end) engine config and its defaults."""

    def test_default_realtime_config_matches_current_constants(self):
        """default_realtime_config() must reproduce the exact tuning that was
        hardcoded in realtime_config.py — this is the behavior-neutrality
        guarantee for the Phase 1 refactor."""
        from shared.voice_agents.speech_config import default_realtime_config

        cfg = default_realtime_config()
        assert cfg.engine_mode.value == "realtime"
        assert cfg.provider == "google"
        # Must match worker/src/realtime_config.py constants exactly.
        assert cfg.model == "gemini-2.5-flash-native-audio-preview-12-2025"
        assert cfg.voice == "Puck"
        assert cfg.temperature == 0.7
        assert cfg.silence_duration_ms == 500
        assert cfg.prefix_padding_ms == 200

    def test_realtime_config_accepts_overrides(self):
        """A user must be able to override model/voice/temperature per agent."""
        from shared.voice_agents.speech_config import RealtimeSpeechConfig

        cfg = RealtimeSpeechConfig(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Charon",
            temperature=0.5,
            silence_duration_ms=700,
        )
        assert cfg.voice == "Charon"
        assert cfg.temperature == 0.5
        assert cfg.silence_duration_ms == 700

    def test_realtime_config_rejects_non_google_provider(self):
        """The realtime engine currently only supports the Google native-audio
        model; a different provider must be rejected at validation time."""
        from shared.voice_agents.speech_config import RealtimeSpeechConfig

        with pytest.raises(ValidationError):
            RealtimeSpeechConfig(provider="openai")

    def test_realtime_engine_mode_is_locked(self):
        """RealtimeSpeechConfig must not be instantiable with engine_mode=
        pipeline (the Literal keeps the two variants disjoint for the
        discriminator)."""
        from shared.voice_agents.speech_config import RealtimeSpeechConfig

        with pytest.raises(ValidationError):
            RealtimeSpeechConfig(engine_mode="pipeline")


class TestPipelineSpeechConfig:
    """Tests for the modular pipeline engine config."""

    def _stage(self, provider="deepgram", model="nova-3"):
        return {"provider": provider, "model": model}

    def test_valid_pipeline_config(self):
        """A pipeline config with stt/llm/tts stages is valid and carries the
        chosen providers/models."""
        from shared.voice_agents.speech_config import PipelineSpeechConfig

        cfg = PipelineSpeechConfig(
            stt=self._stage("deepgram", "nova-3"),
            llm=self._stage("openai", "gpt-4o-mini"),
            tts=self._stage("cartesia", "sonic-2"),
        )
        assert cfg.engine_mode.value == "pipeline"
        assert cfg.stt.provider == "deepgram"
        assert cfg.stt.model == "nova-3"
        assert cfg.llm.provider == "openai"
        assert cfg.tts.provider == "cartesia"
        # VAD / turn detection are optional (LiveKit defaults apply when None).
        assert cfg.vad is None
        assert cfg.turn_detection is None

    def test_pipeline_config_requires_all_three_core_stages(self):
        """STT, LLM, and TTS are mandatory in pipeline mode; omitting any must
        raise a validation error."""
        from shared.voice_agents.speech_config import PipelineSpeechConfig

        with pytest.raises(ValidationError):
            PipelineSpeechConfig(stt=self._stage(), llm=self._stage())  # no tts

    def test_stage_config_requires_provider(self):
        """A stage without a provider is invalid — provider is the dispatch
        key for the factory."""
        from shared.voice_agents.speech_config import STTStageConfig

        with pytest.raises(ValidationError):
            STTStageConfig(model="nova-3")  # missing provider

    def test_stage_config_allows_extra_params(self):
        """Stage configs must tolerate provider-specific kwargs via params so
        adding a new provider does not require a schema migration."""
        from shared.voice_agents.speech_config import TTSStageConfig

        cfg = TTSStageConfig(
            provider="cartesia",
            model="sonic-2",
            params={"voice": "feminine", "speed": 1.1},
        )
        assert cfg.params == {"voice": "feminine", "speed": 1.1}


class TestSpeechConfigDiscriminatedUnion:
    """Tests for the discriminated union that dispatches on engine_mode."""

    def test_dict_with_realtime_mode_resolves_to_realtime(self):
        """Parsing a dict tagged engine_mode=realtime yields a
        RealtimeSpeechConfig (this is how the JSONB column will hydrate)."""
        from shared.voice_agents.speech_config import (
            RealtimeSpeechConfig,
            parse_speech_config,
        )

        cfg = parse_speech_config({"engine_mode": "realtime", "voice": "Aoede"})
        assert isinstance(cfg, RealtimeSpeechConfig)
        assert cfg.voice == "Aoede"

    def test_dict_with_pipeline_mode_resolves_to_pipeline(self):
        """Parsing a dict tagged engine_mode=pipeline yields a
        PipelineSpeechConfig with hydrated stage configs."""
        from shared.voice_agents.speech_config import (
            PipelineSpeechConfig,
            parse_speech_config,
        )

        cfg = parse_speech_config(
            {
                "engine_mode": "pipeline",
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "openai", "model": "gpt-4o-mini"},
                "tts": {"provider": "cartesia"},
            }
        )
        assert isinstance(cfg, PipelineSpeechConfig)
        assert cfg.stt.provider == "deepgram"
        assert cfg.llm.model == "gpt-4o-mini"

    def test_dict_with_unknown_engine_mode_rejected(self):
        """An unknown engine_mode must be rejected (no silent fallthrough)."""
        from shared.voice_agents.speech_config import parse_speech_config

        with pytest.raises(ValidationError):
            parse_speech_config({"engine_mode": "telepathy"})

    def test_none_resolves_to_default_realtime(self):
        """A null config (legacy agents with no speech_config column set) must
        fall back to the default realtime config — backward compatibility."""
        from shared.voice_agents.speech_config import (
            RealtimeSpeechConfig,
            parse_speech_config,
        )

        cfg = parse_speech_config(None)
        assert isinstance(cfg, RealtimeSpeechConfig)
        assert cfg.model == "gemini-2.5-flash-native-audio-preview-12-2025"
