"""Tests that Alembic migrations can import ``shared`` from the monorepo root."""

from __future__ import annotations

import sys
from pathlib import Path


def test_shared_importable_from_repo_root_on_sys_path() -> None:
    """Mirrors backend/alembic/env.py so migrations can seed shared defaults."""
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))

    from shared.voice_agents.speech_config import default_realtime_config

    config = default_realtime_config()
    assert config.engine_mode == "realtime"
    assert config.model == "gemini-3.8-live"
    assert config.voice == "Zephyr"
