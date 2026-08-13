"""Tests for the phone-rental scheduler cadence and runtime overrides."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.phone_numbers import rental_scheduler


def test_check_interval_uses_the_shorter_environment_cadence(monkeypatch):
    """Startup cadence covers both billing and release-pending work."""
    monkeypatch.setattr(
        rental_scheduler,
        "settings",
        SimpleNamespace(
            phone_number_billing_check_interval_hours=24,
            phone_number_release_retry_interval_hours=6,
        ),
    )

    assert rental_scheduler._check_interval_hours() == 6


def test_check_interval_uses_default_when_settings_are_unset(monkeypatch):
    """The scheduler has a daily default when no deployment override exists."""
    monkeypatch.setattr(rental_scheduler, "settings", SimpleNamespace())

    assert rental_scheduler._check_interval_hours() == 24


def test_check_interval_uses_single_configured_value(monkeypatch):
    """A single configured cadence is honored when the other is absent."""
    monkeypatch.setattr(
        rental_scheduler,
        "settings",
        SimpleNamespace(phone_number_billing_check_interval_hours=8),
    )

    assert rental_scheduler._check_interval_hours() == 8


@pytest.mark.asyncio
async def test_runtime_interval_reads_platform_admin_settings():
    """Admin changes are picked up without restarting the scheduler."""
    scheduler = rental_scheduler.PhoneNumberRentalScheduler(24)
    configured = SimpleNamespace(
        billing_check_interval_hours=12,
        release_retry_interval_hours=4,
    )

    with patch.object(
        rental_scheduler.platform_phone_number_settings_service,
        "get_settings",
        new=AsyncMock(return_value=configured),
    ):
        assert await scheduler._get_runtime_interval_hours() == 4


@pytest.mark.asyncio
async def test_runtime_interval_falls_back_after_settings_failure():
    """A database outage keeps the scheduler on its previous safe cadence."""
    scheduler = rental_scheduler.PhoneNumberRentalScheduler(18)

    with patch.object(
        rental_scheduler.platform_phone_number_settings_service,
        "get_settings",
        new=AsyncMock(side_effect=RuntimeError("database unavailable")),
    ):
        assert await scheduler._get_runtime_interval_hours() == 18


@pytest.mark.asyncio
async def test_start_is_idempotent_and_stop_cancels_the_loop():
    """Starting twice does not create duplicate workers and stop is graceful."""
    scheduler = rental_scheduler.PhoneNumberRentalScheduler(24)
    scheduler._run_loop = AsyncMock()

    await scheduler.start()
    first_task = scheduler.task
    await scheduler.start()

    assert scheduler.running is True
    assert scheduler.task is first_task
    await first_task

    await scheduler.stop()
    assert scheduler.running is False


@pytest.mark.asyncio
async def test_stop_is_noop_when_scheduler_is_not_running():
    """Shutdown is safe even when startup never completed."""
    scheduler = rental_scheduler.PhoneNumberRentalScheduler(24)

    await scheduler.stop()

    assert scheduler.running is False


@pytest.mark.asyncio
async def test_stop_swallows_worker_cancellation():
    """Stopping an active worker awaits and absorbs its cancellation."""
    scheduler = rental_scheduler.PhoneNumberRentalScheduler(24)

    async def blocked_worker():
        await asyncio.sleep(3600)

    scheduler.running = True
    scheduler.task = asyncio.create_task(blocked_worker())

    await scheduler.stop()

    assert scheduler.running is False


@pytest.mark.asyncio
async def test_loop_continues_after_processing_failure_until_cancelled():
    """One failed iteration is logged and does not kill the worker."""
    scheduler = rental_scheduler.PhoneNumberRentalScheduler(24)
    scheduler.running = True

    with patch.object(
        rental_scheduler.phone_number_service,
        "process_due_rentals",
        new=AsyncMock(side_effect=RuntimeError("database unavailable")),
    ), patch.object(
        rental_scheduler.asyncio,
        "sleep",
        new=AsyncMock(side_effect=asyncio.CancelledError),
    ):
        await scheduler._run_loop()


@pytest.mark.asyncio
async def test_process_scheduler_entrypoints_manage_global_instance():
    """Process-level start and stop delegate to the shared scheduler instance."""
    with patch.object(
        rental_scheduler.PhoneNumberRentalScheduler,
        "start",
        new=AsyncMock(),
    ) as start_mock, patch.object(
        rental_scheduler.PhoneNumberRentalScheduler,
        "stop",
        new=AsyncMock(),
    ) as stop_mock:
        await rental_scheduler.start_phone_number_rental_scheduler()
        await rental_scheduler.stop_phone_number_rental_scheduler()

    start_mock.assert_awaited_once()
    stop_mock.assert_awaited_once()
