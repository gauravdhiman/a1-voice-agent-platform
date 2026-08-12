"""Tests for provider-neutral email delivery adapters."""

from unittest.mock import patch

import pytest
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
