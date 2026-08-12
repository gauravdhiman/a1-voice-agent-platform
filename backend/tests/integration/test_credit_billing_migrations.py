"""Contract tests for the database-backed credit settlement migrations."""

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
