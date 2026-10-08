"""Contract tests for the database-backed credit settlement migrations."""

import importlib.util
from pathlib import Path

MIGRATIONS = Path(__file__).parents[2] / "alembic" / "versions"


def test_low_credit_event_migration_seeds_the_builtin_event():
    """The required event exists after migrations without a manual seed command."""
    migration = MIGRATIONS / "20260811000004_seed_low_credit_notification_event.py"
    source = migration.read_text()

    assert "credits.low_balance" in source
    assert "ON CONFLICT (event_key)" in source
    assert "built_in_template" in source


def test_voice_settlement_migration_allows_atomic_final_call_overdraft():
    """The final-call RPC settles all minutes and records overdraft metadata."""
    migration = (
        MIGRATIONS
        / "20260811000005_add_credit_notification_outbox_and_voice_settlement.py"
    )
    source = migration.read_text()

    assert "credit_notification_outbox" in source
    assert "v_overdraft" in source
    assert "overdraft_credits" in source
    assert "p_call_log_id" in source
    assert "v_plan_after" in source


def test_credit_notification_outbox_is_hardened_with_row_level_security():
    """The follow-up migration protects the service-owned queue from clients."""
    migration = MIGRATIONS / "20260812000001_enable_credit_notification_outbox_rls.py"
    source = migration.read_text()

    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "credit_notification_outbox" in source


def test_low_credit_threshold_update_migration_uses_twenty_ten_five():
    """The applied notification registry describes the current thresholds."""
    migration = MIGRATIONS / "20260812000003_update_low_credit_thresholds.py"
    source = migration.read_text()

    assert "20%, 10%, or 5%" in source
    assert "'[20, 10, 5]'::jsonb" in source


def test_regular_debit_rpc_handles_negative_plan_pool_after_voice_overdraft():
    """Phone rentals can consume positive pools while preserving call debt."""
    migration = MIGRATIONS / "20260812000002_fix_debit_after_voice_overdraft.py"
    source = migration.read_text()

    assert "debit_organization_credits" in source
    assert "GREATEST(v_plan, 0)" in source
    assert "v_total < p_credits_needed" in source


def test_credit_catalog_sync_migration_accepts_four_discounted_packs():
    """The database RPC contract matches all current catalog amounts and prices."""
    migration = MIGRATIONS / "20261007000001_four_tier_credit_product_catalog.py"
    spec = importlib.util.spec_from_file_location("four_tier_credit_catalog", migration)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    upgrade_sql = module._credit_catalog_sync_function(module._CURRENT_PACKS)
    downgrade_sql = module._credit_catalog_sync_function(module._PREVIOUS_PACKS)

    assert (
        'down_revision: Union[str, Sequence[str], None] = "20261002000001"'
        in migration.read_text()
    )
    assert "product_count <> 4" in upgrade_sql
    assert "ARRAY[200, 500, 1000, 2000]" in upgrade_sql
    assert "(200, 500), (500, 1200), (1000, 2300), (2000, 4400)" in upgrade_sql
    assert "product_count <> 3" in downgrade_sql
    assert "ARRAY[200, 400, 1000]" in downgrade_sql
