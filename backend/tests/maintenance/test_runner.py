"""Tests for provider-neutral maintenance run coordination."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from src.maintenance.runner import (
    MaintenanceNotDue,
    MaintenanceRunner,
    RetryableMaintenanceError,
)


@pytest.mark.asyncio
async def test_success_is_completed_under_owned_lock():
    coordinator = AsyncMock()
    coordinator.acquire.return_value = "owner"
    task = AsyncMock()
    result = await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    assert result.status == "succeeded"
    task.assert_awaited_once()
    coordinator.complete.assert_awaited_once_with("refresh", "owner", True)


@pytest.mark.asyncio
async def test_overlap_does_not_execute():
    coordinator = AsyncMock()
    coordinator.acquire.return_value = None
    task = AsyncMock()
    result = await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    assert result.status == "already_running"
    task.assert_not_awaited()
    coordinator.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_not_due_is_a_successful_skip_without_running():
    coordinator = AsyncMock()
    coordinator.acquire.side_effect = MaintenanceNotDue()
    task = AsyncMock()
    result = await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    assert result.status == "not_due"
    task.assert_not_awaited()


@pytest.mark.asyncio
async def test_failure_is_recorded():
    coordinator = AsyncMock()
    coordinator.acquire.return_value = "owner"
    task = AsyncMock(side_effect=RuntimeError("failed"))
    result = await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    assert result.status == "failed"
    coordinator.complete.assert_awaited_once_with("refresh", "owner", False)


@pytest.mark.asyncio
async def test_explicitly_safe_failure_releases_claim_for_scheduler_retry():
    coordinator = AsyncMock()
    coordinator.acquire.return_value = "owner"
    task = AsyncMock(side_effect=RetryableMaintenanceError())
    result = await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    assert result.status == "failed"
    coordinator.retry.assert_awaited_once_with("refresh", "owner")


@pytest.mark.asyncio
async def test_failure_logs_do_not_expose_provider_details(caplog):
    coordinator = AsyncMock()
    coordinator.acquire.return_value = "owner"
    task = AsyncMock(side_effect=RuntimeError("sensitive provider details"))
    await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    assert "sensitive provider details" not in caplog.text


@pytest.mark.asyncio
async def test_cancellation_does_not_release_uncertain_work():
    coordinator = AsyncMock()
    coordinator.acquire.return_value = "owner"
    task = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    coordinator.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_failure_fails_closed():
    coordinator = AsyncMock()
    coordinator.acquire.side_effect = RuntimeError("unavailable")
    task = AsyncMock()
    with pytest.raises(RuntimeError):
        await MaintenanceRunner({"refresh": task}, coordinator).run("refresh")
    task.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_job_never_acquires_lock():
    coordinator = AsyncMock()
    with pytest.raises(ValueError):
        await MaintenanceRunner({}, coordinator).run("unknown")
    coordinator.acquire.assert_not_awaited()
