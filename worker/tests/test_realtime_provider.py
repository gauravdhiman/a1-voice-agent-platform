"""Tests for the realtime provider builder (speech_providers.realtime).

``test_realtime_config.py`` guards the *default* tuning through the
backward-compat shim (``realtime_config.py``). These tests cover the
config-driven path that the pipeline feature introduces: a
``RealtimeSpeechConfig`` with non-default voice / temperature / endpointing
must flow through to the ``RealtimeModel`` kwargs, while the fixed tuning
(thinking off, barge-in on) stays constant regardless of config.
"""

from google.genai import types
from livekit.plugins.google.realtime import RealtimeModel

from shared.voice_agents.speech_config import (
    DEFAULT_REALTIME_MODEL,
    RealtimeSpeechConfig,
)


class TestRealtimeProviderConfigDriven:
    """Tests for build_realtime_model_config / build_realtime_model with an
    explicit RealtimeSpeechConfig."""

    def test_config_override_changes_user_tunable_kwargs(self):
        """A config with non-default voice/temperature/endpointing must be
        reflected in the returned kwargs."""
        from speech_providers.realtime import build_realtime_model_config

        cfg = RealtimeSpeechConfig(
            voice="Charon",
            temperature=0.4,
            silence_duration_ms=700,
            prefix_padding_ms=150,
        )
        kwargs = build_realtime_model_config(cfg)
        assert kwargs["voice"] == "Charon"
        assert kwargs["temperature"] == 0.4
        aad = kwargs["realtime_input_config"].automatic_activity_detection
        assert aad.silence_duration_ms == 700
        assert aad.prefix_padding_ms == 150

    def test_fixed_tuning_is_independent_of_config(self):
        """Thinking-off and barge-in are fixed (not user-tunable yet) and must
        hold for any realtime config — they are the latency/reliability
        levers documented in the provider docstring."""
        from speech_providers.realtime import build_realtime_model_config

        cfg = RealtimeSpeechConfig(voice="Charon", temperature=0.4)
        kwargs = build_realtime_model_config(cfg)
        assert kwargs["thinking_config"].thinking_budget == 0
        assert kwargs["thinking_config"].include_thoughts is False
        assert (
            kwargs["realtime_input_config"].activity_handling
            == types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS
        )

    def test_no_arg_uses_default_config(self):
        """build_realtime_model_config() with no args must use the default
        realtime config (behavior-neutrality vs. the old hardcoded constants)."""
        from speech_providers.realtime import build_realtime_model_config

        kwargs = build_realtime_model_config()
        assert kwargs["model"] == DEFAULT_REALTIME_MODEL
        assert kwargs["voice"] == "Puck"
        assert kwargs["temperature"] == 0.7
        assert (
            kwargs[
                "realtime_input_config"
            ].automatic_activity_detection.silence_duration_ms
            == 500
        )

    def test_build_realtime_model_reflects_config(self):
        """build_realtime_model must construct a RealtimeModel whose opts carry
        the config's voice/temperature — construction must not need a network
        connection (the WebSocket opens on session start)."""
        from speech_providers.realtime import build_realtime_model

        cfg = RealtimeSpeechConfig(voice="Charon", temperature=0.4)
        model = build_realtime_model(api_key="fake-test-key", config=cfg)
        assert isinstance(model, RealtimeModel)
        assert model._opts.voice == "Charon"
        assert model._opts.temperature == 0.4
        # Fixed tuning carried through.
        assert model._opts.thinking_config.thinking_budget == 0

    def test_build_realtime_model_default_config(self):
        """build_realtime_model with no config uses defaults and still disables
        thinking (the single biggest latency lever)."""
        from speech_providers.realtime import build_realtime_model

        model = build_realtime_model(api_key="fake-test-key")
        assert isinstance(model, RealtimeModel)
        assert model._opts.voice == "Puck"
        assert model._opts.thinking_config.thinking_budget == 0
        assert model.capabilities.turn_detection is True
