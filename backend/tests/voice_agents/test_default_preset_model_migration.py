"""Contract tests for the system-default Gemini Live preset migration."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260922000001_update_default_gemini_live.py"
)


def _load_migration():
    """Load the migration without starting the Alembic environment."""
    spec = importlib.util.spec_from_file_location(
        "default_gemini_live_migration", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_current_head_and_has_one_revision():
    migration = _load_migration()

    assert migration.revision == "20260922000001"
    assert migration.down_revision == "20260920000001"
    assert migration.branch_labels in (None, (), [])
    assert migration.depends_on in (None, (), [])


def test_upgrade_changes_only_the_system_default_realtime_row():
    migration = _load_migration()
    migration.op = MagicMock()
    bind = migration.op.get_bind.return_value

    migration.upgrade()

    statement, params = bind.execute.call_args.args
    sql = str(statement)
    assert "UPDATE pipeline_presets" in sql
    assert "jsonb_set" in sql
    assert "WHERE is_default = true" in sql
    assert "preset_type = 'realtime'" in sql
    assert "config->>'engine_mode' = 'realtime'" in sql
    assert "updated_at = now()" in sql
    assert params == {
        "provider": "google",
        "model": "gemini-3.8-live",
        "voice": "Zephyr",
    }


def test_downgrade_preserves_a_default_edited_after_upgrade():
    migration = _load_migration()
    migration.op = MagicMock()
    bind = migration.op.get_bind.return_value

    migration.downgrade()

    statement, params = bind.execute.call_args.args
    sql = str(statement)
    assert "WHERE is_default = true" in sql
    assert "config->>'model' = :current_model" in sql
    assert "config->>'voice' = :current_voice" in sql
    assert params == {
        "model": "gemini-2.5-flash-native-audio-preview-12-2025",
        "voice": "Puck",
        "current_model": "gemini-3.8-live",
        "current_voice": "Zephyr",
    }
