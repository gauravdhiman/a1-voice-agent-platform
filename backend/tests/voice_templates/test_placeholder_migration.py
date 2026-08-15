"""Contract tests for canonical voice-template placeholder migration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20260814000002_canonicalize_voice_template_placeholders.py"
)


def _load_migration():
    """Load the migration module without registering it as an application module."""
    spec = spec_from_file_location(
        "canonical_voice_template_placeholders", MIGRATION_PATH
    )
    assert spec and spec.loader
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_migration_rewrites_legacy_template_markers_to_supported_variables():
    """The forward migration updates every prompt-bearing template column."""
    migration = _load_migration()
    migration.op = MagicMock()

    migration.upgrade()

    sql = migration.op.execute.call_args.args[0]
    assert "UPDATE voice_templates" in sql
    for column in (
        "description",
        "persona",
        "tone",
        "mission",
        "greeting",
        "custom_instructions",
    ):
        assert f"{column} =" in sql
    assert "[Business Name]" in sql
    assert "[Agent Name]" in sql
    assert "{{org.name}}" in sql
    assert "{{agent.name}}" in sql
