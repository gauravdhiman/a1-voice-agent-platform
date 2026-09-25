"""Tests for tenant-scoped critical notification destinations."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from src.notifications.organization_settings_models import (
    OrganizationNotificationSettingsUpdate,
)
from src.notifications.organization_settings_service import (
    OrganizationNotificationSettingsService,
)
from src.notifications.routes import (
    get_organization_notification_settings,
    update_organization_notification_settings,
)


class _Profile:
    def __init__(self, *, organization_admins=(), platform_admin=False):
        self.organization_admins = {str(value) for value in organization_admins}
        self.platform_admin = platform_admin

    def has_role(self, role_name, organization_id=None):
        if role_name == "platform_admin":
            return self.platform_admin
        return (
            role_name == "org_admin"
            and str(organization_id) in self.organization_admins
        )


class _Query:
    def __init__(self, rows=None, data=None):
        self.rows = rows or []
        self.data = data
        self.filters = []

    def select(self, _fields):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, _limit):
        return self

    def execute(self):
        return SimpleNamespace(
            data=self.rows if self.data is None else self.data, error=None
        )


class _Supabase:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.rpc_calls = []

    def table(self, _name):
        return _Query(rows=self.rows)

    def rpc(self, name, arguments):
        self.rpc_calls.append((name, arguments))
        return _Query(data={"organization_id": arguments["p_organization_id"]})


def _settings_row(organization_id):
    return {
        "organization_id": str(organization_id),
        "alert_email": "ops@example.com",
        "sms_phone": "+15551234567",
        "sms_enabled": False,
        "telegram_chat_id": "-100123456789",
        "telegram_enabled": False,
        "updated_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _platform_settings():
    return SimpleNamespace(
        sms_sender_configured=True,
        telegram_bot_token_configured=True,
    )


def test_settings_update_trims_destinations_and_accepts_explicit_clears():
    payload = OrganizationNotificationSettingsUpdate.model_validate(
        {
            "alert_email": "  operations@example.com  ",
            "sms_phone": " +15551234567 ",
            "telegram_chat_id": " -100123456789 ",
        }
    )

    assert payload.alert_email == "operations@example.com"
    assert payload.sms_phone == "+15551234567"
    assert payload.telegram_chat_id == "-100123456789"
    cleared = OrganizationNotificationSettingsUpdate.model_validate(
        {"alert_email": "", "sms_phone": "", "telegram_chat_id": ""}
    )
    assert cleared.alert_email is None
    assert cleared.sms_phone is None
    assert cleared.telegram_chat_id is None


@pytest.mark.parametrize(
    "payload",
    [
        {"sms_phone": "555-123-4567"},
        {"telegram_chat_id": "@abc"},
        {"sms_enabled": None},
        {"unknown": "field"},
    ],
)
def test_settings_update_rejects_malformed_destinations_and_unknown_fields(payload):
    with pytest.raises(ValidationError):
        OrganizationNotificationSettingsUpdate.model_validate(payload)


@pytest.mark.asyncio
async def test_service_uses_atomic_partial_update_rpc():
    organization_id = uuid4()
    user_id = uuid4()
    client = _Supabase([_settings_row(organization_id)])
    service = OrganizationNotificationSettingsService(
        platform_settings_service=SimpleNamespace(
            get_settings=AsyncMock(return_value=_platform_settings())
        ),
        supabase_config_override=SimpleNamespace(service_client=client, client=client),
    )
    payload = OrganizationNotificationSettingsUpdate(sms_enabled=True)

    await service.update_settings(organization_id, payload, user_id)

    name, arguments = client.rpc_calls[0]
    assert name == "update_organization_notification_settings"
    assert arguments == {
        "p_organization_id": str(organization_id),
        "p_updated_by": str(user_id),
        "p_updates": {"sms_enabled": True},
    }


@pytest.mark.asyncio
async def test_service_rejects_enabling_channel_without_destination_before_write():
    organization_id = uuid4()
    client = _Supabase([_settings_row(organization_id) | {"sms_phone": None}])
    service = OrganizationNotificationSettingsService(
        platform_settings_service=SimpleNamespace(
            get_settings=AsyncMock(return_value=_platform_settings())
        ),
        supabase_config_override=SimpleNamespace(service_client=client, client=client),
    )

    with pytest.raises(ValueError, match="phone number"):
        await service.update_settings(
            organization_id,
            OrganizationNotificationSettingsUpdate(sms_enabled=True),
            uuid4(),
        )
    assert client.rpc_calls == []


@pytest.mark.asyncio
async def test_route_allows_only_target_organization_or_platform_admin(monkeypatch):
    organization_id = uuid4()
    user_id = uuid4()
    settings = SimpleNamespace(organization_id=organization_id)
    service = SimpleNamespace(get_settings=AsyncMock(return_value=settings))
    monkeypatch.setattr(
        "src.notifications.routes.organization_notification_settings_service", service
    )

    result = await get_organization_notification_settings(
        organization_id,
        (user_id, _Profile(organization_admins=[organization_id])),
    )
    assert result is settings

    with pytest.raises(HTTPException) as denied:
        await get_organization_notification_settings(
            organization_id,
            (user_id, _Profile(organization_admins=[uuid4()])),
        )
    assert denied.value.status_code == 403
    service.get_settings.assert_awaited_once_with(organization_id)

    platform_result = await get_organization_notification_settings(
        organization_id, (user_id, _Profile(platform_admin=True))
    )
    assert platform_result is settings


@pytest.mark.asyncio
async def test_update_route_translates_service_validation_to_422(monkeypatch):
    organization_id = uuid4()
    user_id = uuid4()
    service = SimpleNamespace(
        update_settings=AsyncMock(side_effect=ValueError("Enter a phone number."))
    )
    monkeypatch.setattr(
        "src.notifications.routes.organization_notification_settings_service", service
    )

    with pytest.raises(HTTPException) as invalid:
        await update_organization_notification_settings(
            organization_id,
            OrganizationNotificationSettingsUpdate(sms_enabled=True),
            (user_id, _Profile(organization_admins=[organization_id])),
        )
    assert invalid.value.status_code == 422
    service.update_settings.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_route_denies_admin_of_another_organization(monkeypatch):
    service = SimpleNamespace(update_settings=AsyncMock())
    monkeypatch.setattr(
        "src.notifications.routes.organization_notification_settings_service", service
    )

    with pytest.raises(HTTPException) as denied:
        await update_organization_notification_settings(
            uuid4(),
            OrganizationNotificationSettingsUpdate(alert_email="ops@example.com"),
            (uuid4(), _Profile(organization_admins=[uuid4()])),
        )
    assert denied.value.status_code == 403
    service.update_settings.assert_not_awaited()
