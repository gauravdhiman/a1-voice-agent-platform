"""Saved-destination probes deny unauthorized/foreign tenants and hide secrets."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.notifications import delivery_test, routes


def _client(*, platform=False, org=None):
    app = FastAPI()
    app.include_router(routes.router)
    profile = SimpleNamespace(
        has_role=lambda role, organization_id=None: (
            platform
            if role == "platform_admin"
            else role == "org_admin" and organization_id == str(org)
        )
    )
    app.dependency_overrides[routes.get_authenticated_user] = lambda: (uuid4(), profile)
    return TestClient(app)


@pytest.mark.parametrize("platform,org", [(False, None), (False, "another-tenant")])
def test_non_platform_admin_cannot_trigger_platform_delivery(
    monkeypatch, platform, org
):
    send = AsyncMock()
    monkeypatch.setattr(routes, "send_delivery_test", send)
    response = _client(platform=platform, org=org).post(
        "/api/v1/notifications/admin/settings/test", json={"channel": "email"}
    )
    assert response.status_code == 403
    send.assert_not_awaited()


def test_cross_tenant_and_regular_user_cannot_trigger_org_delivery(monkeypatch):
    send = AsyncMock()
    monkeypatch.setattr(routes, "send_delivery_test", send)
    path = f"/api/v1/notifications/organizations/{uuid4()}/settings/test"
    for org in [None, uuid4()]:
        assert (
            _client(org=org).post(path, json={"channel": "telegram"}).status_code == 403
        )
    send.assert_not_awaited()


@pytest.mark.parametrize("platform", [True, False])
def test_authorized_admin_can_only_probe_saved_destination(monkeypatch, platform):
    org = uuid4()
    send = AsyncMock(return_value=delivery_test.DeliveryTestResult())
    monkeypatch.setattr(routes, "send_delivery_test", send)
    path = (
        "/api/v1/notifications/admin/settings/test"
        if platform
        else f"/api/v1/notifications/organizations/{org}/settings/test"
    )
    client = _client(platform=platform, org=org)
    assert (
        client.post(
            path, json={"channel": "email", "recipient": "attacker@example.test"}
        ).status_code
        == 422
    )
    assert client.post(path, json={"channel": "sms"}).status_code == 422
    response = client.post(path, json={"channel": "email"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    send.assert_awaited_once_with("email", *([] if platform else [org]))


@pytest.mark.asyncio
async def test_email_uses_saved_org_destination_and_confirms_provider_id(monkeypatch):
    org = uuid4()
    monkeypatch.setattr(
        delivery_test.organization_notification_settings_service,
        "get_settings",
        AsyncMock(return_value=SimpleNamespace(alert_email="saved@example.test")),
    )
    provider = SimpleNamespace(
        send=AsyncMock(return_value=SimpleNamespace(provider_message_id="accepted-id"))
    )
    monkeypatch.setattr(delivery_test, "build_email_provider", lambda: provider)
    assert (await delivery_test.send_delivery_test("email", org)).status == "accepted"
    message = provider.send.call_args.args[0]
    assert message.recipient_email == "saved@example.test"
    assert message.idempotency_key.startswith("notification-test/")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [TimeoutError("provider-secret"), None])
async def test_provider_error_or_absent_id_never_claims_email_success(
    monkeypatch, failure
):
    monkeypatch.setattr(
        delivery_test.platform_notification_settings_service,
        "get_platform_admin_email",
        AsyncMock(return_value="saved@example.test"),
    )
    provider = SimpleNamespace(
        send=AsyncMock(
            side_effect=failure, return_value=SimpleNamespace(provider_message_id=None)
        )
    )
    monkeypatch.setattr(delivery_test, "build_email_provider", lambda: provider)
    with pytest.raises(delivery_test.HTTPException) as caught:
        await delivery_test.send_delivery_test("email")
    assert caught.value.status_code == 502
    assert "provider-secret" not in caught.value.detail


@pytest.mark.asyncio
async def test_telegram_uses_org_token_not_platform_credentials(monkeypatch):
    org = uuid4()
    get_org = AsyncMock(
        return_value=SimpleNamespace(
            telegram_bot_token="saved-token", telegram_chat_id="saved-chat"
        )
    )
    monkeypatch.setattr(
        delivery_test.organization_notification_settings_service,
        "get_delivery_settings",
        get_org,
    )
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(delivery_test.telegram_service, "send_message", send)
    result = await delivery_test.send_delivery_test("telegram", org)
    get_org.assert_awaited_once_with(org)
    assert send.call_args.args[:2] == ("saved-token", "saved-chat")
    assert "saved-token" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_missing_or_disabled_telegram_is_actionable_and_never_sent(monkeypatch):
    monkeypatch.setattr(
        delivery_test.platform_notification_settings_service,
        "get_telegram_credentials",
        AsyncMock(return_value=("token", "chat", False)),
    )
    send = AsyncMock()
    monkeypatch.setattr(delivery_test.telegram_service, "send_message", send)
    with pytest.raises(delivery_test.HTTPException) as caught:
        await delivery_test.send_delivery_test("telegram")
    assert caught.value.status_code == 422
    send.assert_not_awaited()
