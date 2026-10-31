"""Contract tests for selectable platform voice preset defaults."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261030000001_platform_credential_source_voice_presets.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "platform_preset_credential_migration", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_follows_current_head():
    migration = _load_migration()
    assert migration.revision == "20261030000001"
    assert migration.down_revision == "20261019000005"


def test_upgrade_adds_source_constraints_and_atomic_default_rpc():
    migration = _load_migration()
    migration.op = MagicMock()

    migration.upgrade()

    migration.op.add_column.assert_called_once()
    migration.op.create_check_constraint.assert_any_call(
        "ck_pipeline_presets_credential_source",
        "pipeline_presets",
        "credential_source IN ('platform', 'organization')",
    )
    migration.op.create_check_constraint.assert_any_call(
        "ck_pipeline_presets_default_platform_published",
        "pipeline_presets",
        "NOT is_default OR (credential_source = 'platform' AND is_published)",
    )
    statements = [str(call.args[0]) for call in migration.op.execute.call_args_list]
    sql = "\n".join(statements)
    assert "UPDATE public.pipeline_presets" in sql
    assert "SET credential_source = 'platform', is_published = true" in sql
    assert "Platform-managed profile used when no voice profile is selected." in sql
    assert "LOCK TABLE public.pipeline_presets IN EXCLUSIVE MODE" in sql
    assert "Only published presets can be the default" in sql
    assert "SET is_default = false, updated_at = now()" in sql
    assert "SET is_default = true, updated_at = now()" in sql
    assert "REVOKE ALL ON FUNCTION" in sql
    assert "GRANT EXECUTE ON FUNCTION" in sql


def test_downgrade_requires_a_forward_repair():
    migration = _load_migration()
    with pytest.raises(RuntimeError, match="forward repair"):
        migration.downgrade()
