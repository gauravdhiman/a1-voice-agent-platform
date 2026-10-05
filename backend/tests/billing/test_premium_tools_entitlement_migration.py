"""Migration contract tests for customer-facing premium integration copy."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20261002000001_update_premium_tools_entitlement_copy.py"
)
SPEC = spec_from_file_location(
    "premium_tools_entitlement_copy_migration", MIGRATION_PATH
)
assert SPEC and SPEC.loader
MIGRATION = module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)
FRESH_INSTALL_MIGRATION_PATH = (
    MIGRATION_PATH.parents[0] / "20260807000002_add_plan_versioning_and_entitlements.py"
)


def test_upgrade_updates_premium_integration_metadata(monkeypatch):
    """Existing databases receive the same label and description as fresh ones."""
    operations = MagicMock()
    statements: list[str] = []
    operations.execute.side_effect = lambda statement: statements.append(
        str(statement)
    )
    monkeypatch.setattr(MIGRATION, "op", operations)

    MIGRATION.upgrade()

    sql = "\n".join(statements)
    assert "UPDATE entitlement_definitions" in sql
    assert "display_name = 'Premium integrations'" in sql
    assert (
        "Gmail, Google Sheets, HubSpot lead capture, and Cal.com scheduling" in sql
    )
    assert "WHERE key = 'premium_tools'" in sql
    assert "AND display_name = 'Premium tools'" in sql
    assert "AND description = 'Access to premium platform tools'" in sql


def test_fresh_install_seed_uses_the_same_premium_integration_copy():
    """Fresh databases start with the label and description from the update."""
    source = FRESH_INSTALL_MIGRATION_PATH.read_text()

    assert "'premium_tools', 'feature', 'Premium integrations'" in source
    assert (
        "'Includes Gmail, Google Sheets, HubSpot lead capture, and Cal.com scheduling.'"
        in source
    )


def test_downgrade_only_reverts_unmodified_migration_copy(monkeypatch):
    """Rollback preserves a catalog label customized after the migration."""
    operations = MagicMock()
    statements: list[str] = []
    operations.execute.side_effect = lambda statement: statements.append(
        str(statement)
    )
    monkeypatch.setattr(MIGRATION, "op", operations)

    MIGRATION.downgrade()

    sql = "\n".join(statements)
    assert "display_name = 'Premium tools'" in sql
    assert "AND display_name = 'Premium integrations'" in sql
    assert (
        "AND description = 'Includes Gmail, Google Sheets, HubSpot lead capture, "
        "and Cal.com scheduling.'"
    ) in sql
