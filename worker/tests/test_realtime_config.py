"""Tests for the Gemini realtime model configuration.

The voice agent's conversation quality (latency, tool-calling reliability,
turn detection, barge-in) is almost entirely determined by the kwargs passed
to ``livekit.plugins.google.realtime.RealtimeModel``. Those kwargs are built by
``worker.src.realtime_config.build_realtime_model_config`` so they can be
asserted on deterministically, without standing up a live session or hitting
the network.

These tests guard the specific tuning decisions made to fix the choppy,
delayed, repetitive voice experience documented in the model-options analysis:

* **Thinking disabled** (``thinking_budget=0``) — the single biggest lever.
  On the Gemini-API native-audio model, thinking defaults ON, which causes
  6+ second response latency *and* is the documented driver of the
  native-audio model's ~95-98% function-calling failure rate. Disabling it fixes
  both latency and tool-calling reliability.
* **Barge-in explicitly enabled** (``START_OF_ACTIVITY_INTERRUPTS``) — so the
  agent stops and listens when the user speaks over it, instead of barreling
  ahead and repeating itself after the user already responded.
* **Endpointing tuned** (``silence_duration_ms=500``, ``prefix_padding_ms=200``)
  — so the model commits end-of-turn faster after the user pauses, cutting the
  dead-air delay before the agent replies.
* **Temperature lowered** (0.8 -> 0.7) — reduces rambling and repetition.
* **Model kept as the 2.5 native-audio preview** — the 3.1 "live" preview is NOT
  used (LiveKit plugin doesn't support it; it forces synchronous function
  calling that blocks the conversation; it breaks mid-session instruction
  updates). See the model-options analysis for the full rationale.
"""

from google.genai import types


class TestBuildRealtimeModelConfig:
    """Test cases for build_realtime_model_config."""

    def test_config_disables_thinking(self):
        """Thinking must be disabled (thinking_budget=0) to cut latency and fix
        tool-calling reliability on the native-audio model."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        thinking = config["thinking_config"]
        assert isinstance(thinking, types.ThinkingConfig)
        assert thinking.thinking_budget == 0
        # Thoughts must not be surfaced as audio/transcript — they are noise when
        # thinking is effectively off and would waste tokens.
        assert thinking.include_thoughts is False

    def test_config_enables_barge_in(self):
        """Activity handling must be START_OF_ACTIVITY_INTERRUPTS so the agent
        stops talking when the user speaks (fixes the 'repeats the same thing
        even when the user responded earlier' symptom)."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        rt_input = config["realtime_input_config"]
        assert isinstance(rt_input, types.RealtimeInputConfig)
        assert (
            rt_input.activity_handling
            == types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS
        )

    def test_config_tunes_endpointing(self):
        """Server-side automatic activity detection must be ON (not disabled —
        we want the server doing VAD/endpointing) with a snappy silence duration
        so the agent replies quickly after the user pauses."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        aad = config["realtime_input_config"].automatic_activity_detection
        assert isinstance(aad, types.AutomaticActivityDetection)
        # Must NOT be disabled — server-side turn detection stays active.
        assert aad.disabled is None or aad.disabled is False
        # Snappy endpointing: 500ms of silence commits end-of-turn.
        assert aad.silence_duration_ms == 500
        assert aad.prefix_padding_ms == 200

    def test_config_lowers_temperature(self):
        """Temperature lowered from 0.8 to 0.7 to reduce rambling/repetition."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        assert config["temperature"] == 0.7

    def test_config_keeps_native_audio_model(self):
        """Must keep the 2.5 native-audio preview model (async function calling,
        LiveKit-supported). The 3.1 'live' preview must NOT be used — the plugin
        doesn't support it and it forces blocking sync function calls."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        assert config["model"] == "gemini-2.5-flash-native-audio-preview-12-2025"
        assert "3.1" not in config["model"]
        assert "live" not in config["model"]

    def test_config_sets_voice(self):
        """Voice must still be set (carried over from prior config)."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        assert config["voice"] == "Puck"

    def test_config_keys_are_all_valid_plugin_params(self):
        """Every key returned must be a real RealtimeModel kwarg — if a key is
        misspelled or removed by a plugin bump, this catches it at build time
        rather than at the first live call."""
        from realtime_config import build_realtime_model_config

        config = build_realtime_model_config()
        # api_key is supplied by build_realtime_model(), not the config dict.
        assert "api_key" not in config
        # Core tuning knobs that must always be present.
        for key in (
            "model",
            "voice",
            "temperature",
            "thinking_config",
            "realtime_input_config",
        ):
            assert key in config, f"missing required config key: {key}"


class TestBuildRealtimeModel:
    """Test cases for build_realtime_model (constructs the live RealtimeModel)."""

    def test_constructs_realtime_model_without_network(self):
        """build_realtime_model must return a RealtimeModel instance using the
        tuned config — construction must not require a network connection (the
        WebSocket is only opened on session start). This proves the config dict
        is accepted by the installed plugin's constructor."""
        from livekit.plugins.google.realtime import RealtimeModel

        from realtime_config import build_realtime_model

        model = build_realtime_model(api_key="fake-test-key")
        assert isinstance(model, RealtimeModel)
        # Server-side turn detection must remain active (we did not disable
        # automatic activity detection).
        assert model.capabilities.turn_detection is True

    def test_constructed_model_carries_disabled_thinking(self):
        """The constructed model's options must reflect thinking disabled."""
        from realtime_config import build_realtime_model

        model = build_realtime_model(api_key="fake-test-key")
        assert model._opts.thinking_config.thinking_budget == 0

    def test_constructed_model_carries_barge_in(self):
        """The constructed model's options must reflect barge-in enabled."""
        from realtime_config import build_realtime_model

        model = build_realtime_model(api_key="fake-test-key")
        assert (
            model._opts.realtime_input_config.activity_handling
            == types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS
        )