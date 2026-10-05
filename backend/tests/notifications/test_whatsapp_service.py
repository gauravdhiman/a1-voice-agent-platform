"""Unit tests for Twilio WhatsApp template delivery."""

from unittest.mock import patch

import httpx
import pytest
from src.notifications.whatsapp_service import WhatsAppService


class FakeAsyncClient:
    """Capture form delivery while keeping the test fully offline."""

    def __init__(self, *, response: httpx.Response) -> None:
        self.response = response
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, *, data, auth):
        self.request = (url, data, auth)
        return self.response


@pytest.mark.asyncio
async def test_send_template_message_uses_twilio_content_template():
    service = WhatsAppService()
    client = FakeAsyncClient(response=httpx.Response(201, json={"sid": "SM123"}))
    with patch("src.notifications.whatsapp_service.settings") as app_settings, patch(
        "src.notifications.whatsapp_service.httpx.AsyncClient", return_value=client
    ):
        app_settings.twilio_account_sid = "AC_TEST"
        app_settings.twilio_auth_token = "test-auth-token"
        app_settings.twilio_whatsapp_from_number = "+14155550123"
        app_settings.twilio_whatsapp_content_sid = "HX_TEST"

        sent = await service.send_template_message(
            "+14805550100", {"1": "Sam Owner", "2": "Bright Smiles"}
        )

    assert sent is True
    assert client.request == (
        "https://api.twilio.com/2010-04-01/Accounts/AC_TEST/Messages.json",
        {
            "From": "whatsapp:+14155550123",
            "To": "whatsapp:+14805550100",
            "ContentSid": "HX_TEST",
            "ContentVariables": '{"1": "Sam Owner", "2": "Bright Smiles"}',
        },
        ("AC_TEST", "test-auth-token"),
    )


@pytest.mark.asyncio
async def test_send_template_message_rejects_provider_failure_without_body_logging():
    service = WhatsAppService()
    client = FakeAsyncClient(
        response=httpx.Response(400, json={"message": "private provider detail"})
    )
    with patch("src.notifications.whatsapp_service.settings") as app_settings, patch(
        "src.notifications.whatsapp_service.httpx.AsyncClient", return_value=client
    ):
        app_settings.twilio_account_sid = "AC_TEST"
        app_settings.twilio_auth_token = "test-auth-token"
        app_settings.twilio_whatsapp_from_number = "+14155550123"
        app_settings.twilio_whatsapp_content_sid = "HX_TEST"

        sent = await service.send_template_message("+14805550100", {"1": "Sam"})

    assert sent is False
