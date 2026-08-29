"""Tests for provider-neutral email delivery adapters."""

from unittest.mock import patch

import pytest
import resend
from src.notifications.email_providers import EmailMessage, ResendEmailProvider


@pytest.mark.asyncio
async def test_resend_provider_adapts_a_message_and_runs_sync_sdk_off_loop():
    """The Resend adapter returns the provider message ID through one interface."""
    provider = ResendEmailProvider(
        api_key="re_test_key",
        default_from_email="noreply@example.com",
        default_from_name="24x7 AI",
    )
    message = EmailMessage(
        recipient_email="owner@example.com",
        recipient_name="Business Owner",
        subject="Credits are running low",
        html_content="<p>Low balance</p>",
        text_content="Low balance",
    )

    with patch(
        "src.notifications.email_providers.resend.Emails.send",
        return_value={"id": "email-123"},
    ) as send:
        result = await provider.send(message)

    assert result.provider_message_id == "email-123"
    assert result.provider == "resend"
    send.assert_called_once()


@pytest.mark.asyncio
async def test_resend_provider_forwards_idempotency_key():
    """Retries can reuse the provider key without changing the email payload."""
    provider = ResendEmailProvider(
        api_key="re_test_key",
        default_from_email="noreply@example.com",
        default_from_name="24x7 AI",
    )
    message = EmailMessage(
        recipient_email="owner@example.com",
        recipient_name=None,
        subject="Callback requested",
        html_content="",
        text_content="Please call the customer.",
        idempotency_key="voice-resend-test-key",
    )

    with patch(
        "src.notifications.email_providers.resend.Emails.send",
        return_value={"id": "email-456"},
    ) as send:
        result = await provider.send(message)

    assert result.provider_message_id == "email-456"
    send.assert_called_once_with(
        {
            "from": "24x7 AI <noreply@example.com>",
            "to": ["owner@example.com"],
            "subject": "Callback requested",
            "text": "Please call the customer.",
        },
        {"idempotency_key": "voice-resend-test-key"},
    )


@pytest.mark.asyncio
async def test_resend_provider_restores_sdk_global_key_after_send():
    """One organization's credential cannot remain active for the next call."""
    provider = ResendEmailProvider(
        api_key="re_org_key",
        default_from_email="noreply@example.com",
        default_from_name="Example Business",
    )
    message = EmailMessage(
        recipient_email="owner@example.com",
        recipient_name=None,
        subject="Callback requested",
        html_content="",
        text_content="Please call the customer.",
    )

    previous_key = resend.api_key

    def fake_send(params, options=None):
        """Observe the key only while the provider owns the SDK call."""
        assert resend.api_key == "re_org_key"
        return {"id": "email-isolated"}

    with patch("src.notifications.email_providers.resend.Emails.send", fake_send):
        result = await provider.send(message)

    assert result.provider_message_id == "email-isolated"
    assert resend.api_key == previous_key
