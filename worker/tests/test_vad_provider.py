"""Tests for the Silero VAD pipeline builder (speech_providers.vad.silero).

Unlike the cloud stage builders, Silero VAD is local/on-device: it needs no
api_key and has a single bundled ONNX model. The builder calls the sync
``silero.VAD.load(**kwargs)`` classmethod, which loads the bundled
``resources/silero_vad.onnx`` — fully offline, no network, so it is safe and
deterministic in tests. This keeps the pipeline off the bundled
``livekit.agents.inference`` VAD path (deferred bug #7, the missing-Pillow
path) — see the Phase 2 plan's "VAD default nuance" section.
"""

from livekit.plugins import silero

from shared.voice_agents.speech_config import VADConfig


class TestSileroVadConfig:
    """Tests for build_silero_vad_config (pure kwargs, no api_key, no model)."""

    def test_config_forwards_params_only(self):
        """VAD.load takes tuning kwargs (min_silence_duration etc.), not a
        model — so only params are forwarded, never 'model' or 'api_key'."""
        from speech_providers.vad import build_silero_vad_config

        cfg = VADConfig(provider="silero", params={"min_silence_duration": 0.3})
        kwargs = build_silero_vad_config(cfg)
        assert kwargs == {"min_silence_duration": 0.3}
        assert "api_key" not in kwargs
        assert "model" not in kwargs  # silero has one bundled model; not a load() kwarg

    def test_config_ignores_model_field(self):
        """VADConfig inherits a `model` field from StageConfig, but silero has a
        single bundled model — the builder must NOT forward it to VAD.load."""
        from speech_providers.vad import build_silero_vad_config

        cfg = VADConfig(provider="silero", model="silero_v5")
        assert build_silero_vad_config(cfg) == {}

    def test_config_default_is_empty(self):
        from speech_providers.vad import build_silero_vad_config

        assert build_silero_vad_config() == {}


class TestSileroVadBuild:
    """Tests for build_silero_vad (constructs the real VAD, offline, no key)."""

    def test_build_default_returns_silero_vad(self):
        """build_silero_vad() with no args loads the bundled model with plugin
        defaults — returns a livekit.plugins.silero.VAD instance."""
        from speech_providers.vad import build_silero_vad

        vad = build_silero_vad()
        assert isinstance(vad, silero.VAD)
        # Plugin default for min_silence_duration is 0.55s.
        assert vad._opts.min_silence_duration == 0.55

    def test_build_applies_params(self):
        """Forwarded params must land on the VAD's _opts."""
        from speech_providers.vad import build_silero_vad

        cfg = VADConfig(
            provider="silero",
            params={"min_silence_duration": 0.3, "activation_threshold": 0.6},
        )
        vad = build_silero_vad(cfg)
        assert isinstance(vad, silero.VAD)
        assert vad._opts.min_silence_duration == 0.3
        assert vad._opts.activation_threshold == 0.6

    def test_build_none_uses_defaults(self):
        """build_silero_vad(None) (the registry's call when config.vad is None)
        must build the default VAD — this is what keeps the pipeline off the
        bundled inference VAD path."""
        from speech_providers.vad import build_silero_vad

        vad = build_silero_vad(None)
        assert isinstance(vad, silero.VAD)
        assert vad._opts.min_silence_duration == 0.55
