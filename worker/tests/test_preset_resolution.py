"""Tests for the worker's speech-config resolution helper (Phase 4).

``worker._resolve_speech_config`` resolves the SpeechConfig for a call from the
agent's preset, with graceful fallbacks so a misconfigured preset/default never
breaks a live call:

- explicit ``preset_id``, loadable + parseable -> that preset's config;
- explicit ``preset_id``, missing / unparseable / load-error -> the hardcoded
  realtime default (graceful degrade, loud log);
- no ``preset_id`` -> the **system default preset** (the single ``is_default``
  row), if present and parseable, else the hardcoded realtime default. The
  seeded default keeps out-of-box behavior identical to the pre-Phase-4
  hardcoded realtime fallback.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from shared.voice_agents.preset_models import Preset, PresetType
from shared.voice_agents.speech_config import default_realtime_config

import worker

_TS = "2024-01-01T00:00:00"


def _preset(
    *,
    is_default: bool = False,
    is_published: bool = False,
    engine_mode: str = "realtime",
    preset_id=None,
) -> Preset:
    """Build a Preset row for tests."""
    if engine_mode == "pipeline":
        config = {
            "engine_mode": "pipeline",
            "stt": {"provider": "deepgram"},
            "llm": {"provider": "openai"},
            "tts": {"provider": "cartesia"},
        }
    else:
        config = {"engine_mode": "realtime"}
    return Preset(
        id=preset_id or str(uuid4()),
        name="System Default" if is_default else "P",
        preset_type=(
            PresetType.PIPELINE if engine_mode == "pipeline" else PresetType.REALTIME
        ),
        config=config,
        is_published=is_published,
        is_default=is_default,
        created_at=_TS,
        updated_at=_TS,
    )


def _agent(preset_id=None):
    """Build a mock voice_agent with a preset_id attribute."""
    a = MagicMock()
    a.preset_id = preset_id
    a.name = "Agent"
    return a


def _mock_service(*, get_by_id=None, get_default=None):
    """Build a preset_service mock with both methods as AsyncMock.

    Both are AsyncMock so the unused one supports ``assert_not_awaited()``
    (a plain auto-created MagicMock lacks async assertions).
    """
    mock_service = MagicMock()
    mock_service.get_preset_by_id = AsyncMock(
        return_value=get_by_id if get_by_id is not None else (None, None)
    )
    mock_service.get_default_preset = AsyncMock(
        return_value=get_default if get_default is not None else (None, None)
    )
    return mock_service


class TestResolveSpeechConfig:
    """The extracted worker preset-resolution helper."""

    @pytest.mark.asyncio
    async def test_explicit_preset_loaded(self):
        """An explicit, parseable preset is used as-is."""
        pid = uuid4()
        with patch(
            "worker.preset_service",
            _mock_service(
                get_by_id=(_preset(preset_id=pid, engine_mode="pipeline"), None),
            ),
        ) as mock_service:
            cfg = await worker._resolve_speech_config(_agent(preset_id=pid), "a1")
        assert cfg.engine_mode.value == "pipeline"
        mock_service.get_preset_by_id.assert_awaited_once_with(pid)
        mock_service.get_default_preset.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explicit_preset_missing_falls_back(self):
        """A missing explicit preset (deleted) -> realtime default."""
        pid = uuid4()
        with patch(
            "worker.preset_service",
            _mock_service(
                get_by_id=(None, None),
            ),
        ) as mock_service:
            cfg = await worker._resolve_speech_config(_agent(preset_id=pid), "a1")
        assert cfg.engine_mode.value == "realtime"
        mock_service.get_default_preset.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explicit_preset_error_falls_back(self):
        """A load error on the explicit preset -> realtime default."""
        pid = uuid4()
        with patch(
            "worker.preset_service",
            _mock_service(
                get_by_id=(None, "connection error"),
            ),
        ) as mock_service:
            cfg = await worker._resolve_speech_config(_agent(preset_id=pid), "a1")
        assert cfg.engine_mode.value == "realtime"
        mock_service.get_default_preset.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explicit_preset_unparseable_falls_back(self):
        """An unparseable explicit preset config -> realtime default."""
        pid = uuid4()
        with patch(
            "worker.preset_service",
            _mock_service(
                get_by_id=(_preset(preset_id=pid), None),
            ),
        ), patch("worker.parse_speech_config", side_effect=ValueError("bad config")):
            cfg = await worker._resolve_speech_config(_agent(preset_id=pid), "a1")
        assert cfg.engine_mode.value == "realtime"

    @pytest.mark.asyncio
    async def test_no_preset_uses_system_default(self):
        """No preset_id -> the system default preset (here a pipeline default)."""
        with patch(
            "worker.preset_service",
            _mock_service(
                get_default=(_preset(is_default=True, engine_mode="pipeline"), None),
            ),
        ) as mock_service:
            cfg = await worker._resolve_speech_config(_agent(preset_id=None), "a1")
        assert cfg.engine_mode.value == "pipeline"
        mock_service.get_preset_by_id.assert_not_awaited()
        mock_service.get_default_preset.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_preset_no_default_falls_back(self):
        """No preset_id and no seeded default row -> realtime default."""
        with patch(
            "worker.preset_service",
            _mock_service(
                get_default=(None, None),
            ),
        ):
            cfg = await worker._resolve_speech_config(_agent(preset_id=None), "a1")
        assert cfg.engine_mode.value == "realtime"

    @pytest.mark.asyncio
    async def test_no_preset_default_error_falls_back(self):
        """No preset_id and a default-preset load error -> realtime default."""
        with patch(
            "worker.preset_service",
            _mock_service(
                get_default=(None, "connection error"),
            ),
        ):
            cfg = await worker._resolve_speech_config(_agent(preset_id=None), "a1")
        assert cfg.engine_mode.value == "realtime"

    @pytest.mark.asyncio
    async def test_no_preset_default_unparseable_falls_back(self):
        """No preset_id and an unparseable default config -> realtime default."""
        with patch(
            "worker.preset_service",
            _mock_service(
                get_default=(_preset(is_default=True), None),
            ),
        ), patch("worker.parse_speech_config", side_effect=ValueError("bad config")):
            cfg = await worker._resolve_speech_config(_agent(preset_id=None), "a1")
        assert cfg.engine_mode.value == "realtime"
