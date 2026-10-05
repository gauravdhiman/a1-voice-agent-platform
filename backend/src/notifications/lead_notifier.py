"""Platform-admin delivery for public interest-lead submissions."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from opentelemetry import trace
from src.leads.models import InterestLead
from src.notifications.models import SendNotificationRequest
from src.notifications.platform_settings_models import (
    PlatformNotificationSettings,
    verification_sender_configured,
)
from src.notifications.platform_settings_service import (
    platform_notification_settings_service,
)
from src.notifications.service import notification_service
from src.notifications.telegram_service import telegram_service
from src.notifications.whatsapp_service import whatsapp_service

from shared.config import settings

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

INTEREST_LEAD_EVENT_KEY = "lead.interest_submitted"


def _display_value(value: Optional[Any]) -> str:
    """Return a human-readable placeholder for an omitted lead field."""
    if value is None:
        return "—"
    text = str(value).strip()
    return text or "—"


def build_interest_lead_template_variables(lead: InterestLead) -> dict[str, str]:
    """Build the allowlisted values rendered in a platform-admin lead alert."""
    created_at = lead.created_at
    if isinstance(created_at, datetime):
        submitted_at = created_at.astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    else:
        submitted_at = _display_value(created_at)

    return {
        "lead_name": _display_value(lead.name),
        "business_name": _display_value(lead.business_name),
        "lead_email": _display_value(lead.email),
        "lead_phone": _display_value(lead.phone),
        "vertical": _display_value(lead.vertical),
        "message": _display_value(lead.message),
        "source": _display_value(lead.source),
        "demo_slug": _display_value(lead.demo_slug),
        "submitted_at": submitted_at,
        "interests_url": f"{settings.app_base_url.rstrip('/')}/platform/interest",
        "app_name": settings.app_name,
    }


def build_interest_lead_whatsapp_variables(lead: InterestLead) -> dict[str, str]:
    """Map all submitted fields to the approved Twilio template placeholders."""
    values = build_interest_lead_template_variables(lead)
    return {
        "1": values["lead_name"],
        "2": values["business_name"],
        "3": values["lead_email"],
        "4": values["lead_phone"],
        "5": values["vertical"],
        "6": values["message"],
        "7": values["source"],
        "8": values["demo_slug"],
        "9": values["submitted_at"],
        "10": values["interests_url"],
    }


class InterestLeadNotifier:
    """Render and send one lead alert to configured platform-admin channels.

    Public submissions are dispatched through the durable
    ``interest_lead_notification_outbox``. Email also uses the notification
    service's lead-id-based idempotency key; Telegram and WhatsApp use the
    encrypted platform bot settings and approved Twilio Content template.
    """

    @tracer.start_as_current_span("notifications.notify_interest_lead")
    async def notify_interest_lead(self, lead: InterestLead) -> None:
        """Send an email and/or Telegram alert for one persisted lead."""
        current_span = trace.get_current_span()
        current_span.set_attribute("lead.id", str(lead.id))
        current_span.set_attribute("lead.source", lead.source)

        try:
            platform_settings = (
                await platform_notification_settings_service.get_settings()
            )
        except Exception:
            logger.exception(
                "Could not load platform notification settings for lead %s", lead.id
            )
            current_span.set_attribute("notification.settings_error", True)
            return

        tasks: list[Any] = []
        if self._email_is_configured(platform_settings):
            tasks.append(self._send_email(lead, platform_settings))
        else:
            current_span.set_attribute("notification.email_configured", False)

        if platform_settings.telegram_notifications_enabled:
            tasks.append(self._send_telegram(lead))
        else:
            current_span.set_attribute("notification.telegram_configured", False)

        if self._whatsapp_is_configured(platform_settings):
            tasks.append(self._send_whatsapp(lead, platform_settings))
        else:
            current_span.set_attribute("notification.whatsapp_configured", False)

        if not tasks:
            current_span.set_attribute("notification.channels", 0)
            logger.debug("No platform notification channel is configured")
            return

        current_span.set_attribute("notification.channels", len(tasks))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for channel, result in zip(self._channel_names(platform_settings), results):
            if isinstance(result, Exception):
                logger.warning(
                    "Interest notification %s failed for lead %s",
                    channel,
                    lead.id,
                    exc_info=(type(result), result, result.__traceback__),
                )

    @staticmethod
    def _email_is_configured(platform_settings: PlatformNotificationSettings) -> bool:
        """Return whether the email provider and recipient are ready."""
        return bool(
            settings.resend_api_key
            and platform_settings.platform_admin_email
            and (
                verification_sender_configured(
                    platform_settings.verification_from_email,
                    platform_settings.verification_from_name,
                )
                or (settings.resend_from_email and settings.resend_from_name)
            )
        )

    @staticmethod
    def _channel_names(
        platform_settings: PlatformNotificationSettings,
    ) -> list[str]:
        """Return channel labels in the same order as scheduled tasks."""
        channels: list[str] = []
        if InterestLeadNotifier._email_is_configured(platform_settings):
            channels.append("email")
        if platform_settings.telegram_notifications_enabled:
            channels.append("telegram")
        if InterestLeadNotifier._whatsapp_is_configured(platform_settings):
            channels.append("whatsapp")
        return channels

    @staticmethod
    def _whatsapp_is_configured(
        platform_settings: PlatformNotificationSettings,
    ) -> bool:
        """Check the admin opt-in, destination, and backend Twilio setup."""
        return bool(
            platform_settings.platform_admin_whatsapp_notifications_enabled
            and platform_settings.platform_admin_whatsapp_phone
            and whatsapp_service.is_configured()
        )

    async def _send_email(
        self, lead: InterestLead, platform_settings: PlatformNotificationSettings
    ) -> None:
        """Send one durable, idempotent email alert."""
        from_email: Optional[str] = settings.resend_from_email
        from_name: Optional[str] = settings.resend_from_name
        if verification_sender_configured(
            platform_settings.verification_from_email,
            platform_settings.verification_from_name,
        ):
            from_email = str(platform_settings.verification_from_email)
            from_name = platform_settings.verification_from_name

        metadata = {
            "kind": "interest_lead",
            "lead_id": str(lead.id),
            "source": lead.source,
            "from_email": from_email,
            "from_name": from_name,
        }
        response = await notification_service.send_notification(
            SendNotificationRequest(
                event_key=INTEREST_LEAD_EVENT_KEY,
                recipient_email=str(platform_settings.platform_admin_email),
                recipient_name="Platform admin",
                template_variables=build_interest_lead_template_variables(lead),
                from_email=from_email,
                from_name=from_name,
                log_metadata=metadata,
                idempotency_key=f"interest-lead:{lead.id}:email",
            )
        )
        if not response.success:
            raise RuntimeError("Email provider rejected the lead notification")

    async def _send_telegram(self, lead: InterestLead) -> None:
        """Send the lead details to the configured Telegram chat."""
        bot_token, chat_id, enabled = (
            await platform_notification_settings_service.get_telegram_credentials()
        )
        if not enabled:
            logger.debug("Telegram lead notifications are incomplete")
            return
        if not bot_token or not chat_id:
            raise RuntimeError("Telegram lead notification settings are incomplete")

        lines = [
            "📩 New interest request",
            f"Name: {_display_value(lead.name)}",
            f"Business: {_display_value(lead.business_name)}",
            f"Email: {_display_value(lead.email)}",
            f"Phone: {_display_value(lead.phone)}",
            f"Vertical: {_display_value(lead.vertical)}",
            f"Source: {_display_value(lead.source)}",
            f"Demo: {_display_value(lead.demo_slug)}",
            f"Message: {_display_value(lead.message)}",
            f"Lead ID: {lead.id}",
            f"Open: {settings.app_base_url.rstrip('/')}/platform/interest",
        ]
        sent = await telegram_service.send_message(bot_token, chat_id, "\n".join(lines))
        if not sent:
            raise RuntimeError("Telegram provider rejected the lead notification")

    async def _send_whatsapp(
        self, lead: InterestLead, platform_settings: PlatformNotificationSettings
    ) -> None:
        """Send every submitted lead field through an approved WhatsApp template."""
        recipient = platform_settings.platform_admin_whatsapp_phone
        if not recipient:
            return
        sent = await whatsapp_service.send_template_message(
            recipient, build_interest_lead_whatsapp_variables(lead)
        )
        if not sent:
            raise RuntimeError("Twilio rejected the WhatsApp lead notification")


interest_lead_notifier = InterestLeadNotifier()

__all__ = [
    "INTEREST_LEAD_EVENT_KEY",
    "InterestLeadNotifier",
    "build_interest_lead_template_variables",
    "build_interest_lead_whatsapp_variables",
    "interest_lead_notifier",
]
