"""Tests for the shared agent speech-config fallback resolver."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.voice_agents.speech_config import PipelineSpeechConfig, RealtimeSpeechConfig
from shared.voice_agents.speech_config_resolver import (
    resolve_speech_config_for_agent,
    resolve_speech_profile_for_agent,
)


class TestSpeechConfigResolver:
    """Verify preset selection and safe realtime fallback behavior."""

    @pytest.mark.asyncio
    async def test_resolves_explicit_pipeline_preset(self, monkeypatch) -> None:
        """An explicit valid preset takes priority over the system default."""
        preset = SimpleNamespace(
            credential_source="platform",
            config={
                "engine_mode": "pipeline",
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "openai"},
                "tts": {"provider": "cartesia"},
            }
        )

        async def get_preset_by_id(_preset_id: str):
            return preset, None

        monkeypatch.setattr(
            "shared.voice_agents.speech_config_resolver.preset_service.get_preset_by_id",
            get_preset_by_id,
        )

        config = await resolve_speech_config_for_agent(
            SimpleNamespace(preset_id="preset-id"), "agent-id"
        )

        assert isinstance(config, PipelineSpeechConfig)

        profile, source = await resolve_speech_profile_for_agent(
            SimpleNamespace(preset_id="preset-id"), "agent-id"
        )
        assert isinstance(profile, PipelineSpeechConfig)
        assert source == "platform"

    @pytest.mark.asyncio
    async def test_no_selected_preset_uses_current_default_and_its_source(
        self, monkeypatch
    ) -> None:
        preset = SimpleNamespace(
            credential_source="platform",
            config={"engine_mode": "realtime"},
        )

        async def get_default_preset():
            return preset, None

        monkeypatch.setattr(
            "shared.voice_agents.speech_config_resolver.preset_service.get_default_preset",
            get_default_preset,
        )

        config, source = await resolve_speech_profile_for_agent(
            SimpleNamespace(preset_id=None), "agent-id"
        )
        assert isinstance(config, RealtimeSpeechConfig)
        assert source == "platform"

    @pytest.mark.asyncio
    async def test_falls_back_when_explicit_preset_is_missing(self, monkeypatch) -> None:
        """A deleted explicit preset returns the durable realtime default."""

        async def get_preset_by_id(_preset_id: str):
            return None, None

        monkeypatch.setattr(
            "shared.voice_agents.speech_config_resolver.preset_service.get_preset_by_id",
            get_preset_by_id,
        )

        config = await resolve_speech_config_for_agent(
            SimpleNamespace(preset_id="deleted-preset"), "agent-id"
        )

        assert isinstance(config, RealtimeSpeechConfig)
