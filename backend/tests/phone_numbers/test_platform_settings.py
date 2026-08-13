"""Tests for platform-admin phone-number lifecycle settings."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from src.phone_numbers.platform_settings_models import (
    PHONE_NUMBER_SETTINGS_SINGLETON_ID,
    PlatformPhoneNumberSettingsUpdate,
)
from src.phone_numbers.platform_settings_service import (
    PlatformPhoneNumberSettingsService,
)


def _settings_row():
    """Build a representative singleton row."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(PHONE_NUMBER_SETTINGS_SINGLETON_ID),
        "billing_grace_period_days": 9,
        "billing_check_interval_hours": 12,
        "release_retry_interval_hours": 6,
        "updated_by": str(uuid4()),
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_get_settings_reads_singleton_row():
    """Admin reads receive the persisted database values."""
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = MagicMock(data=_settings_row())
    config = MagicMock(is_configured=MagicMock(return_value=True), client=MagicMock())
    config.client.table.return_value = table

    with patch("src.phone_numbers.platform_settings_service.supabase_config", config):
        result = await PlatformPhoneNumberSettingsService().get_settings(
            allow_fallback=False
        )

    assert result.billing_grace_period_days == 9
    assert result.release_retry_interval_hours == 6


@pytest.mark.asyncio
async def test_get_settings_falls_back_when_database_is_unavailable():
    """Runtime processing keeps working during a transient settings outage."""
    config = MagicMock(is_configured=MagicMock(return_value=False))

    with patch("src.phone_numbers.platform_settings_service.supabase_config", config):
        result = await PlatformPhoneNumberSettingsService().get_settings()

    assert result.id == PHONE_NUMBER_SETTINGS_SINGLETON_ID
    assert result.billing_grace_period_days >= 1
    assert result.billing_check_interval_hours > 0


@pytest.mark.asyncio
async def test_update_settings_persists_only_supplied_values():
    """Partial admin updates preserve the other singleton values."""
    table = MagicMock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.return_value = MagicMock(data=[])
    table.select.return_value = table
    table.single.return_value = table
    table.execute.side_effect = [MagicMock(data=[]), MagicMock(data=_settings_row())]
    config = MagicMock(is_configured=MagicMock(return_value=True), client=MagicMock())
    config.client.table.return_value = table

    with patch("src.phone_numbers.platform_settings_service.supabase_config", config):
        result = await PlatformPhoneNumberSettingsService().update_settings(
            PlatformPhoneNumberSettingsUpdate(billing_grace_period_days=14),
            UUID("00000000-0000-0000-0000-000000000040"),
        )

    update_payload = table.update.call_args.args[0]
    assert update_payload["billing_grace_period_days"] == 14
    assert "release_retry_interval_hours" not in update_payload
    assert result.billing_grace_period_days == 9
