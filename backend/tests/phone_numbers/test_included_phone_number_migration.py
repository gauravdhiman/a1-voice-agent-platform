"""Tests for the included US local phone-number allowance migration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20260930000001_included_phone_number_allowance.py"
)
SPEC = spec_from_file_location("included_phone_number_migration", MIGRATION_PATH)
assert SPEC and SPEC.loader
MIGRATION = module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_upgrade_adds_flag_and_updates_only_us_local_rental_rate(
    monkeypatch,
):
    """Upgrade keeps one included number per organization and prices add-ons."""
    operations = MagicMock()
    statements: list[str] = []
    operations.execute.side_effect = lambda statement: statements.append(str(statement))
    monkeypatch.setattr(MIGRATION, "op", operations)

    MIGRATION.upgrade()

    operations.add_column.assert_called_once()
    table_name, column = operations.add_column.call_args.args
    assert table_name == "phone_numbers"
    assert column.name == "is_included_in_plan"
    assert column.nullable is False
    assert str(column.server_default.arg) == "false"

    sql = "\n".join(statements)
    assert "ROW_NUMBER() OVER" in sql
    assert "PARTITION BY candidate.organization_id" in sql
    assert "management_mode = 'platform_managed'" in sql
    assert "organization_subscriptions AS subscription" in sql
    assert "version.billing_mode = 'paid'" in sql
    assert "subscription.status IN ('active', 'trial')" in sql
    assert "subscription.cancel_at_period_end IS FALSE" in sql
    assert "subscription.current_period_end > CURRENT_TIMESTAMP" in sql
    assert "monthly_cost_credits = 0" in sql
    assert "monthly_cost_credits = 80" in sql
    assert "country_code = 'US'" in sql
    assert "UPDATE credit_events" not in sql

    operations.create_index.assert_called_once()
    args, kwargs = operations.create_index.call_args
    assert args[:3] == (
        "uq_phone_numbers_one_included_us_local_per_org",
        "phone_numbers",
        ["organization_id"],
    )
    assert kwargs["unique"] is True
    assert "is_included_in_plan IS TRUE" in str(kwargs["postgresql_where"])
    assert "provisioning" in str(kwargs["postgresql_where"])


def test_downgrade_restores_active_us_local_number_costs(
    monkeypatch,
):
    """Downgrade reverses only the schema and system pricing default."""
    operations = MagicMock()
    statements: list[str] = []
    operations.execute.side_effect = lambda statement: statements.append(str(statement))
    monkeypatch.setattr(MIGRATION, "op", operations)

    MIGRATION.downgrade()

    sql = "\n".join(statements)
    assert "monthly_cost_credits = 200" in sql
    assert (
        "status IN ('provisioning', 'purchased', 'active', 'verification_required', 'release_pending')"
        in sql
    )
    assert "country_code = 'US'" in sql
    operations.drop_index.assert_called_once_with(
        "uq_phone_numbers_one_included_us_local_per_org",
        table_name="phone_numbers",
    )
    operations.drop_column.assert_called_once_with(
        "phone_numbers", "is_included_in_plan"
    )
