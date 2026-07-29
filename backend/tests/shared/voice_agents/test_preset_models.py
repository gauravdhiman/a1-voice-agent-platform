"""Tests for the preset Pydantic models (Phase 3).

Covers the ``config`` discriminated-union validation (realtime vs pipeline) and
that ``preset_type`` is NOT accepted as input on create/update (it is derived by
the service from ``config.engine_mode``).
"""
import pytest
from pydantic import ValidationError

from shared.voice_agents.preset_models import (
    Preset,
    PresetCreate,
    PresetType,
    PresetUpdate,
)


class TestPresetModels:
    """Test cases for the preset models."""

    def test_create_realtime_config_validates(self):
        """A realtime config body validates into the discriminated union."""
        preset = PresetCreate(
            name="R",
            config={"engine_mode": "realtime"},
        )
        assert preset.config.engine_mode.value == "realtime"

    def test_create_pipeline_config_validates(self):
        """A pipeline config body validates into the discriminated union."""
        preset = PresetCreate(
            name="P",
            config={
                "engine_mode": "pipeline",
                "stt": {"provider": "deepgram"},
                "llm": {"provider": "openai"},
                "tts": {"provider": "cartesia"},
            },
        )
        assert preset.config.engine_mode.value == "pipeline"

    def test_create_rejects_unknown_engine_mode(self):
        """An unknown engine_mode is rejected by the discriminated union."""
        with pytest.raises(ValidationError):
            PresetCreate(name="X", config={"engine_mode": "telepathy"})

    def test_create_rejects_pipeline_missing_stages(self):
        """A pipeline config missing a required stage is rejected."""
        with pytest.raises(ValidationError):
            PresetCreate(
                name="X",
                config={"engine_mode": "pipeline", "stt": {"provider": "deepgram"}},
            )

    def test_create_rejects_extra_field(self):
        """StageConfig forbids extra fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            PresetCreate(
                name="X",
                config={
                    "engine_mode": "pipeline",
                    "stt": {"provider": "deepgram", "bogus": 1},
                    "llm": {"provider": "openai"},
                    "tts": {"provider": "cartesia"},
                },
            )

    def test_preset_type_not_settable_on_create(self):
        """preset_type is not an input field on PresetCreate (service derives it)."""
        with pytest.raises(ValidationError):
            PresetCreate(
                name="X",
                config={"engine_mode": "realtime"},
                preset_type="realtime",  # type: ignore[call-arg]
            )

    def test_preset_type_not_settable_on_update(self):
        """preset_type is not an input field on PresetUpdate."""
        with pytest.raises(ValidationError):
            PresetUpdate(preset_type="realtime")  # type: ignore[call-arg]

    def test_preset_response_carries_preset_type(self):
        """The Preset response model requires preset_type (set by the service)."""
        from uuid import uuid4
        from datetime import datetime, timezone

        preset = Preset(
            id=uuid4(),
            name="R",
            preset_type=PresetType.REALTIME,
            config={"engine_mode": "realtime"},
            is_published=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert preset.preset_type is PresetType.REALTIME