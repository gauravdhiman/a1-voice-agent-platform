"""Tests for the Deepgram STT pipeline builder (speech_providers.stt.deepgram).

Mirrors ``test_realtime_provider.py``: a pure ``build_deepgram_stt_config``
returns the plugin kwargs (no api_key — deterministic, unit-testable), and
``build_deepgram_stt`` injects the key and constructs the plugin. Construction
opens no network connection (the WebSocket opens on session start), so a fake
key is safe in tests.
"""

from livekit.plugins import deepgram

from shared.voice_agents.speech_config import STTStageConfig


class TestDeepgramSttConfig:
    """Tests for build_deepgram_stt_config (pure kwargs, no api_key)."""

    def test_config_includes_model_override_and_forwards_params(self):
        """A model override and params must flow into the kwargs verbatim."""
        from speech_providers.stt import build_deepgram_stt_config

        cfg = STTStageConfig(
            provider="deepgram",
            model="nova-2",
            params={"language": "en-GB", "smart_format": True},
        )
        kwargs = build_deepgram_stt_config(cfg)
        assert kwargs["model"] == "nova-2"
        assert kwargs["language"] == "en-GB"
        assert kwargs["smart_format"] is True
        # api_key is injected by build_deepgram_stt, never by the config fn.
        assert "api_key" not in kwargs
        # provider is the dispatch key, not a plugin kwarg.
        assert "provider" not in kwargs

    def test_config_omits_model_when_unset(self):
        """When model is None, 'model' must be omitted so the plugin default
        (nova-3) applies rather than passing model=None."""
        from speech_providers.stt import build_deepgram_stt_config

        kwargs = build_deepgram_stt_config(STTStageConfig(provider="deepgram"))
        assert "model" not in kwargs
        assert kwargs == {}

    def test_config_default_is_empty(self):
        """build_deepgram_stt_config() with no args uses a minimal default stage
        config -> empty kwargs -> all plugin defaults apply."""
        from speech_providers.stt import build_deepgram_stt_config

        assert build_deepgram_stt_config() == {}


class TestDeepgramSttBuild:
    """Tests for build_deepgram_stt (constructs the real plugin, no network)."""

    def test_build_constructs_deepgram_stt_with_config(self):
        """The constructed STT must reflect the config's model + forwarded
        params on its _opts."""
        from speech_providers.stt import build_deepgram_stt

        cfg = STTStageConfig(
            provider="deepgram", model="nova-2", params={"language": "en-GB"}
        )
        stt = build_deepgram_stt(api_key="fake-key", config=cfg)
        assert isinstance(stt, deepgram.STT)
        assert stt._opts.model == "nova-2"
        assert stt._opts.language == "en-GB"

    def test_build_default_uses_nova3(self):
        """No model override -> the plugin's default model (nova-3) applies."""
        from speech_providers.stt import build_deepgram_stt

        stt = build_deepgram_stt(api_key="fake-key")
        assert isinstance(stt, deepgram.STT)
        assert stt._opts.model == "nova-3"
        assert stt._opts.language == "en-US"
