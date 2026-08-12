"""Provider-neutral email delivery contracts and the Resend adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

import resend


@dataclass(frozen=True)
class EmailMessage:
    """Normalized email payload passed to any provider adapter."""

    recipient_email: str
    recipient_name: str | None
    subject: str
    html_content: str
    text_content: str | None = None
    from_email: str | None = None
    from_name: str | None = None


@dataclass(frozen=True)
class EmailSendResult:
    """Provider response normalized for notification-log persistence."""

    provider: str
    provider_message_id: str | None = None


class EmailProvider(Protocol):
    """Async contract implemented by email service providers."""

    name: str

    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Send one normalized email and return its provider identifier."""


class ResendEmailProvider:
    """Resend adapter that keeps the synchronous SDK off the event loop."""

    name = "resend"

    def __init__(
        self,
        api_key: str | None,
        default_from_email: str,
        default_from_name: str,
    ) -> None:
        self.default_from_email = default_from_email
        self.default_from_name = default_from_name
        if api_key:
            resend.api_key = api_key

    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Send through Resend without blocking the async application loop."""
        from_email = message.from_email or self.default_from_email
        from_name = message.from_name or self.default_from_name
        params = {
            "from": f"{from_name} <{from_email}>",
            "to": [message.recipient_email],
            "subject": message.subject,
            "html": message.html_content,
        }
        if message.text_content:
            params["text"] = message.text_content

        response = await asyncio.to_thread(resend.Emails.send, params)
        return EmailSendResult(
            provider=self.name,
            provider_message_id=(response or {}).get("id"),
        )


def build_email_provider() -> EmailProvider:
    """Build the configured provider adapter.

    Resend is the only installed adapter today. The service depends on the
    ``EmailProvider`` contract, so adding SendGrid later does not change
    notification rendering, persistence, or retry behavior.
    """
    from shared.config import settings

    provider_name = getattr(settings, "email_provider", "resend").lower()
    if provider_name != "resend":
        raise ValueError(
            f"Email provider '{provider_name}' is not configured. "
            "Add its adapter before selecting it."
        )
    return ResendEmailProvider(
        api_key=settings.resend_api_key,
        default_from_email=settings.resend_from_email,
        default_from_name=settings.resend_from_name,
    )
