"""Contract tests for database-backed maintenance coordination."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from src.maintenance.coordinator import PostgresRunCoordinator
from src.maintenance.runner import MaintenanceNotDue


@pytest.mark.asyncio
async def test_acquire_returns_an_ownership_token_only_when_confirmed():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data="claimed")
    coordinator = PostgresRunCoordinator(client)
    claim = await coordinator.acquire("refresh")
    name, payload = client.rpc.call_args.args
    assert name == "claim_maintenance_run"
    assert payload == {"p_job": "refresh", "p_claim": claim, "p_interval_seconds": 0}
    assert claim


@pytest.mark.asyncio
async def test_existing_claim_prevents_duplicate_execution():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data="running")
    assert await PostgresRunCoordinator(client).acquire("refresh") is None


@pytest.mark.asyncio
async def test_unexpected_claim_response_fails_closed():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=None)
    with pytest.raises(RuntimeError):
        await PostgresRunCoordinator(client).acquire("refresh")


@pytest.mark.asyncio
async def test_not_due_is_distinct_from_a_busy_or_failed_job():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data="not_due")
    with pytest.raises(MaintenanceNotDue):
        await PostgresRunCoordinator(client).acquire("refresh")


@pytest.mark.asyncio
async def test_failed_job_requires_reconciliation():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data="blocked")
    with pytest.raises(RuntimeError, match="reconciliation"):
        await PostgresRunCoordinator(client).acquire("refresh")


@pytest.mark.asyncio
async def test_lost_ownership_cannot_be_reported_as_success():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=False)
    with pytest.raises(RuntimeError):
        await PostgresRunCoordinator(client).complete("refresh", "old-token", True)


@pytest.mark.asyncio
async def test_failure_is_recorded_with_ownership_token():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    await PostgresRunCoordinator(client).complete("refresh", "owner", False)
    client.rpc.assert_called_once_with(
        "complete_maintenance_run",
        {"p_job": "refresh", "p_claim": "owner", "p_succeeded": False},
    )


@pytest.mark.asyncio
async def test_retryable_failure_uses_distinct_fenced_rpc():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    await PostgresRunCoordinator(client).retry("refresh", "owner")
    client.rpc.assert_called_once_with(
        "retry_maintenance_run", {"p_job": "refresh", "p_claim": "owner"}
    )


@pytest.mark.asyncio
async def test_status_masks_organization_guard_identity():
    client = MagicMock()
    table = client.table.return_value
    for name in ("select", "in_", "like", "eq", "order", "limit"):
        getattr(table, name).return_value = table
    table.execute.side_effect = [
        SimpleNamespace(data=[{"job": "refresh", "state": "idle"}]),
        SimpleNamespace(
            data=[{"state": "failed", "started_at": "2026-11-02T00:00:00Z"}]
        ),
        SimpleNamespace(data=[]),
    ]
    result = await PostgresRunCoordinator(client).status(("refresh",))
    assert result == [
        {"job": "refresh", "state": "idle"},
        {"job": "phone-guard", "state": "failed", "started_at": "2026-11-02T00:00:00Z"},
    ]
