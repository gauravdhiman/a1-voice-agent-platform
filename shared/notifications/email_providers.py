"""Provider-neutral email delivery contracts and the Resend adapter.

The module is shared by backend notification workflows and native voice tools.
It intentionally contains no persistence or business-event logic; callers own
those concerns and use the provider only for an outbound delivery attempt.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from threading import RLock
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
    idempotency_key: str | None = None


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


_RESEND_SDK_LOCK = RLock()


class ResendEmailProvider:
    """Resend adapter that keeps the synchronous SDK off the event loop."""

    name = "resend"

    def __init__(
        self,
        api_key: str | None,
        default_from_email: str,
        default_from_name: str,
    ) -> None:
        self.api_key = api_key
        self.default_from_email = default_from_email
        self.default_from_name = default_from_name

    async def send(self, message: EmailMessage) -> EmailSendResult:
        """Send through Resend without blocking the async application loop.

        A caller-provided idempotency key is forwarded to Resend so a timeout
        or provider retry cannot create a duplicate email. The key is optional
        to preserve the existing notification-service behavior.
        """
        from_email = message.from_email or self.default_from_email
        from_name = message.from_name or self.default_from_name
        sender = f"{from_name} <{from_email}>" if from_name else from_email
        params: dict[str, object] = {
            "from": sender,
            "to": [message.recipient_email],
            "subject": message.subject,
        }
        if message.html_content:
            params["html"] = message.html_content
        if message.text_content:
            params["text"] = message.text_content

        options = (
            {"idempotency_key": message.idempotency_key}
            if message.idempotency_key
            else None
        )
        response = await asyncio.to_thread(self._send_with_sdk, params, options)

        return EmailSendResult(
            provider=self.name,
            provider_message_id=(response or {}).get("id"),
        )

    def _send_with_sdk(
        self,
        params: dict[str, object],
        options: dict[str, str] | None,
    ) -> object:
        """Call the global-state SDK with an isolated, restored API key.

        Resend's current Python SDK stores its API key in a module-global
        variable. Calls for different organizations can share one voice-ws
        process, so setting that value at construction time would allow a
        concurrent call to use another organization's credential. The lock
        serializes only the SDK section and restores the prior value afterward.
        """
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("Resend API key is not configured")

        with _RESEND_SDK_LOCK:
            previous_api_key = resend.api_key
            resend.api_key = self.api_key.strip()
            try:
                if options is None:
                    return resend.Emails.send(params)
                return resend.Emails.send(params, options)
            finally:
                resend.api_key = previous_api_key


def build_resend_email_provider(
    *,
    api_key: str,
    default_from_email: str,
    default_from_name: str,
) -> ResendEmailProvider:
    """Build a Resend adapter from an explicitly resolved runtime credential.

    This factory is for native tools that resolve organization-owned
    credentials at call assembly time. Platform-owned notification workflows
    should continue using :func:`build_email_provider`.
    """
    return ResendEmailProvider(
        api_key=api_key,
        default_from_email=default_from_email,
        default_from_name=default_from_name,
    )


def build_email_provider() -> EmailProvider:
    """Build the configured provider adapter.

    Resend is the only installed adapter today. The service depends on the
    ``EmailProvider`` contract, so adding another provider later does not
    change notification rendering or native tool contracts.
    """
    from shared.config import settings

    provider_name = str(getattr(settings, "email_provider", "resend")).lower()
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
