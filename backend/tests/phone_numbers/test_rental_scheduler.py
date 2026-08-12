"""Tests for the phone-rental scheduler cadence and runtime overrides."""

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
