"""Contract tests for the unlimited-agent rollout migration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20261008000001_unlimited_agents_by_default.py"
)
SPEC = spec_from_file_location("unlimited_agents_migration", MIGRATION_PATH)
assert SPEC and SPEC.loader
MIGRATION = module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class _MigrationResult:
    def __init__(self, *, row=None, scalar=None, rowcount=0):
        self._row = row
        self._scalar = scalar
        self.rowcount = rowcount

    def mappings(self):
        return self

    def first(self):
        return self._row

    def scalar_one(self):
        return self._scalar


class _MigrationConnection:
    def __init__(self, execute):
        self._execute = execute
        self.calls = []

    def execute(self, statement, parameters=None):
        sql = str(statement)
        params = parameters or {}
        self.calls.append((sql, params))
        return self._execute(sql, params)


def test_upgrade_publishes_next_free_version_and_migrates_subscriptions(monkeypatch):
    """Upgrade preserves Free terms and changes only the agent entitlement."""
    old_version_id = uuid4()
    product_id = uuid4()
    publish_event_id = uuid4()
    free_version = {
        "id": old_version_id,
        "plan_product_id": product_id,
        "version_number": 3,
        "billing_mode": "free",
        "credit_grant_policy": "recurring",
        "price_amount_cents": 0,
        "currency": "USD",
        "billing_interval": "monthly",
        "trial_period_days": None,
    }

    def execute(sql, _params):
        if "SELECT pv.*" in sql:
            return _MigrationResult(row=free_version)
        if "SELECT COALESCE(MAX(version_number)" in sql:
            return _MigrationResult(scalar=5)
        if "SELECT 1" in sql and "plan_version_entitlements" in sql:
            return _MigrationResult()
        if "INSERT INTO plan_version_publish_events" in sql:
            return _MigrationResult(scalar=publish_event_id)
        return _MigrationResult()

    connection = _MigrationConnection(execute)
    monkeypatch.setattr(MIGRATION, "op", SimpleNamespace(get_bind=lambda: connection))

    MIGRATION.upgrade()

    version_sql, version_params = next(
        (sql, params)
        for sql, params in connection.calls
        if "INSERT INTO plan_versions" in sql
    )
    assert version_params["version_number"] == 5
    assert version_params["display_label"] == "Free v5"
    assert version_params["price_amount_cents"] == free_version["price_amount_cents"]
    assert "NULL, NULL, true" in version_sql

    entitlement_sql = next(
        sql
        for sql, _params in connection.calls
        if "INSERT INTO plan_version_entitlements" in sql
    )
    assert "WHEN entitlement_key = 'max_agents'" in entitlement_sql
    assert '\'{"type":"unlimited"}\'::jsonb' in entitlement_sql

    event_params = next(
        params
        for sql, params in connection.calls
        if "INSERT INTO plan_version_publish_events" in sql
    )
    assert event_params["from_version_id"] == old_version_id
    assert event_params["to_version_id"] == version_params["id"]

    migration_sql = next(
        sql
        for sql, _params in connection.calls
        if "INSERT INTO organization_subscription_migrations" in sql
    )
    assert "status IN ('active', 'trial')" in migration_sql
    assert any(
        'SET default_when_absent = \'{"type":"unlimited"}\'::jsonb' in sql
        for sql, _params in connection.calls
    )


def test_downgrade_stops_when_untracked_subscriptions_use_new_free_version(
    monkeypatch,
):
    """Rollback refuses to strand subscriptions created after the rollout."""
    publish_event = {
        "id": uuid4(),
        "from_plan_version_id": uuid4(),
        "to_plan_version_id": uuid4(),
    }

    def execute(sql, _params):
        if "FROM plan_version_publish_events AS e" in sql:
            return _MigrationResult(row=publish_event)
        if "FROM organization_subscriptions AS subscription" in sql:
            return _MigrationResult(row={"id": uuid4()})
        return _MigrationResult()

    connection = _MigrationConnection(execute)
    monkeypatch.setattr(MIGRATION, "op", SimpleNamespace(get_bind=lambda: connection))

    with pytest.raises(RuntimeError, match="subscriptions use the new version"):
        MIGRATION.downgrade()

    assert not any(
        "UPDATE organization_subscriptions" in sql for sql, _params in connection.calls
    )
