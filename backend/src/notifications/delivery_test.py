"""Explicit admin-requested probes using saved destinations and server secrets."""

import asyncio
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from .email_providers import EmailMessage, build_email_provider
from .organization_settings_service import organization_notification_settings_service
from .platform_settings_service import platform_notification_settings_service
from .telegram_service import telegram_service


class DeliveryTestRequest(BaseModel):
    """Select a configured channel; arbitrary recipients and content are forbidden."""

    model_config = ConfigDict(extra="forbid")
    channel: Literal["email", "telegram"]


class DeliveryTestResult(BaseModel):
    """Provider acceptance is distinct from receipt confirmed by an administrator."""

    status: Literal["accepted"] = "accepted"
    message: str = (
        "Provider accepted the test. Confirm receipt at the saved destination."
    )


async def send_delivery_test(
    channel: str, organization_id: UUID | None = None
) -> DeliveryTestResult:
    """Send one fixed test to saved settings; callers enforce admin/tenant access.

    No automatic retry is attempted. Provider diagnostics and destinations are
    never returned to the browser. Email probes carry a per-attempt idempotency
    key; a missing provider message ID never counts as success.
    """
    if channel == "email":
        if organization_id is None:
            destination = (
                await platform_notification_settings_service.get_platform_admin_email()
            )
        else:
            settings = await organization_notification_settings_service.get_settings(
                organization_id
            )
            destination = settings.alert_email
        if not destination:
            raise HTTPException(
                422, "Save a notification email destination before testing."
            )
        message = EmailMessage(
            recipient_email=str(destination),
            recipient_name=None,
            subject="24x7 AI notification test",
            html_content=(
                "<p>This test confirms your saved 24x7 AI notification destination.</p>"
            ),
            text_content=(
                "This test confirms your saved 24x7 AI notification destination."
            ),
            idempotency_key=f"notification-test/{uuid4()}",
        )
        try:
            result = await asyncio.wait_for(
                build_email_provider().send(message), timeout=20
            )
            accepted = bool(result.provider_message_id)
        except Exception:
            accepted = False
    else:
        if organization_id is None:
            token, destination, enabled = (
                await platform_notification_settings_service.get_telegram_credentials()
            )
        else:
            delivery = (
                await organization_notification_settings_service.get_delivery_settings(
                    organization_id
                )
            )
            token, destination, enabled = (
                delivery.telegram_bot_token,
                delivery.telegram_chat_id,
                True,
            )
        if not token or not destination or not enabled:
            raise HTTPException(
                422, "Save and enable the Telegram bot and destination before testing."
            )
        accepted = await telegram_service.send_message(
            token,
            destination,
            "24x7 AI notification test: your saved destination is reachable.",
        )
    if not accepted:
        raise HTTPException(
            502,
            "The provider did not confirm the test. Check saved settings "
            "and provider configuration before retrying.",
        )
    return DeliveryTestResult()
