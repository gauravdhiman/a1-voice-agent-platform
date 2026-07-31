"""Tests for the Cartesia TTS pipeline builder (speech_providers.tts.cartesia).

Mirrors ``test_realtime_provider.py``. Cartesia is the one provider that stores
``api_key`` on ``_opts``, so the build test also asserts the key was injected.
Construction opens no network connection, so a fake key is safe.
"""

from livekit.plugins import cartesia

from shared.voice_agents.speech_config import TTSStageConfig


class TestCartesiaTtsConfig:
    """Tests for build_cartesia_tts_config (pure kwargs, no api_key)."""

    def test_config_includes_model_override_and_forwards_params(self):
        """A model override and params (voice/language) must flow verbatim."""
        from speech_providers.tts import build_cartesia_tts_config

        cfg = TTSStageConfig(
            provider="cartesia",
            model="sonic-2",
            params={"voice": "voice-uuid-abc", "language": "es"},
        )
        kwargs = build_cartesia_tts_config(cfg)
        assert kwargs["model"] == "sonic-2"
        assert kwargs["voice"] == "voice-uuid-abc"
        assert kwargs["language"] == "es"
        assert "api_key" not in kwargs
        assert "provider" not in kwargs

    def test_config_omits_model_when_unset(self):
        """When model is None, 'model' is omitted so the plugin default
        (sonic-3) applies."""
        from speech_providers.tts import build_cartesia_tts_config

        kwargs = build_cartesia_tts_config(
            TTSStageConfig(provider="cartesia", params={"voice": "v1"})
        )
        assert "model" not in kwargs
        assert kwargs == {"voice": "v1"}

    def test_config_dedicated_voice_field_takes_precedence_over_params(self):
        """TTSStageConfig.voice wins over params['voice'] when both are set."""
        from speech_providers.tts import build_cartesia_tts_config

        kwargs = build_cartesia_tts_config(
            TTSStageConfig(
                provider="cartesia",
                voice="field-voice",
                params={"voice": "params-voice", "language": "en"},
            )
        )
        assert kwargs["voice"] == "field-voice"
        assert kwargs["language"] == "en"

    def test_config_dedicated_voice_field_without_params(self):
        from speech_providers.tts import build_cartesia_tts_config

        kwargs = build_cartesia_tts_config(
            TTSStageConfig(provider="cartesia", voice="uuid-123")
        )
        assert kwargs == {"voice": "uuid-123"}

    def test_config_default_is_empty(self):
        from speech_providers.tts import build_cartesia_tts_config

        assert build_cartesia_tts_config() == {}


class TestCartesiaTtsBuild:
    """Tests for build_cartesia_tts (constructs the real plugin, no network)."""

    def test_build_constructs_cartesia_tts_with_config_and_key(self):
        from speech_providers.tts import build_cartesia_tts

        cfg = TTSStageConfig(
            provider="cartesia",
            model="sonic-2",
            params={"voice": "voice-uuid-abc", "language": "es"},
        )
        tts = build_cartesia_tts(api_key="fake-key", config=cfg)
        assert isinstance(tts, cartesia.TTS)
        assert tts._opts.model == "sonic-2"
        assert tts._opts.voice == "voice-uuid-abc"
        assert tts._opts.language == "es"
        # Cartesia stores the api_key on _opts — assert it was injected.
        assert tts._opts.api_key == "fake-key"

    def test_build_default_uses_sonic_3(self):
        from speech_providers.tts import build_cartesia_tts

        tts = build_cartesia_tts(api_key="fake-key")
        assert isinstance(tts, cartesia.TTS)
        assert tts._opts.model == "sonic-3"
