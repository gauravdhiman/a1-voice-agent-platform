"""Provider-neutral SMS delivery contracts and the Twilio adapter.

The module is shared by backend notification workflows and native voice
tools. It intentionally contains no persistence or business-event logic;
callers own those concerns and use the provider only for an outbound
delivery attempt.

Deliberately SDK-free: Twilio's Messages API is a single form-encoded
POST, so ``httpx`` (already a shared dependency) avoids adding the
Twilio SDK to the voice runtime image.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

_E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")
_MAX_BODY_LENGTH = 1600
_TIMEOUT_SECONDS = 8.0

# Twilio error codes with deterministic retry guidance.
_RETRYABLE_CODES = frozenset({20429, 20500})
_AUTH_CODES = frozenset({20003, 20005})


@dataclass(frozen=True)
class SmsMessage:
    """Normalized SMS payload passed to any provider adapter."""

    recipient_phone: str
    body: str
    from_phone: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class SmsSendResult:
    """Provider response normalized for notification-log persistence."""

    provider: str
    provider_message_id: str | None = None


class SmsProvider(Protocol):
    """Async contract implemented by SMS service providers."""

    name: str

    async def send(self, message: SmsMessage) -> SmsSendResult:
        """Send one normalized SMS and return its provider identifier."""


def is_valid_sms_phone(value: object) -> bool:
    """Return True for E.164 numbers Twilio will accept.

    Args:
        value: Candidate phone value.

    Returns:
        True for ``+``-prefixed 7-15 digit numbers.
    """
    return isinstance(value, str) and bool(_E164_PATTERN.fullmatch(value.strip()))


class TwilioSmsProvider:
    """Twilio Messages API adapter over plain HTTPS."""

    name = "twilio"

    def __init__(
        self,
        account_sid: str | None,
        auth_token: str | None,
        default_from_phone: str,
    ) -> None:
        """Store explicitly resolved runtime credentials.

        Args:
            account_sid: Twilio Account SID.
            auth_token: Twilio Auth Token (never logged).
            default_from_phone: E.164 sender number for this organization.
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.default_from_phone = default_from_phone

    async def send(self, message: SmsMessage) -> SmsSendResult:
        """Send one SMS through Twilio's Messages API.

        Raises:
            ValueError: Credentials, sender, recipient, or body invalid.
            TwilioSmsError: Provider rejection (carries code + retryable).
        """
        if (
            not isinstance(self.account_sid, str)
            or not self.account_sid.strip()
            or not isinstance(self.auth_token, str)
            or not self.auth_token.strip()
        ):
            raise ValueError("Twilio credentials are not configured")
        sender = message.from_phone or self.default_from_phone
        if not is_valid_sms_phone(sender):
            raise ValueError("SMS sender number is not a valid E.164 number")
        if not is_valid_sms_phone(message.recipient_phone):
            raise ValueError("SMS recipient number is not a valid E.164 number")
        body = message.body.strip()
        if not body:
            raise ValueError("SMS body must not be empty")
        if len(body) > _MAX_BODY_LENGTH:
            raise ValueError("SMS body is too long")

        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid.strip()}/Messages.json"
        )
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    url,
                    auth=(self.account_sid.strip(), self.auth_token.strip()),
                    data={
                        "To": message.recipient_phone.strip(),
                        "From": sender.strip(),
                        "Body": body,
                    },
                )
        except Exception as exc:
            logger.warning(
                "Twilio SMS transport failed error_type=%s", type(exc).__name__
            )
            raise TwilioSmsError(
                "Twilio did not respond before the delivery timeout.",
                retryable=True,
            ) from exc

        if response.status_code in (200, 201):
            try:
                sid = response.json().get("sid")
            except Exception:
                sid = None
            return SmsSendResult(provider=self.name, provider_message_id=sid)

        code, provider_message = _parse_error(response)
        raise TwilioSmsError(provider_message, code=code, retryable=_retryable(code))


def _parse_error(response: httpx.Response) -> tuple[int | None, str]:
    """Extract a Twilio error code and safe message from a rejection."""
    try:
        payload = response.json()
    except Exception:
        return None, "Twilio rejected the SMS request."
    code = payload.get("code")
    try:
        code = int(code) if code is not None else None
    except (TypeError, ValueError):
        code = None
    message = payload.get("message") or "Twilio rejected the SMS request."
    return code, str(message)[:300]


def _retryable(code: int | None) -> bool:
    """Classify Twilio error codes into retry guidance."""
    if code is None:
        return True
    if code in _AUTH_CODES:
        return False
    if code in _RETRYABLE_CODES:
        return True
    # 21211 (bad To), 21610 (unsubscribed), 21608 (trial), 21606/21408
    # (sender capability/permission): resending the same payload cannot help.
    if 21200 <= code <= 21999:
        return False
    return response_is_server_error(code)


def response_is_server_error(code: int) -> bool:
    """Return True for 5xx-class provider failures."""
    return 500 <= code <= 599


class TwilioSmsError(Exception):
    """Twilio rejection with stable retry guidance (never raw secrets)."""

    def __init__(
        self, message: str, *, code: int | None = None, retryable: bool = False
    ) -> None:
        """Capture the safe message, numeric code, and retry flag."""
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def build_twilio_sms_provider(
    *,
    account_sid: str | None,
    auth_token: str | None,
    default_from_phone: str,
) -> TwilioSmsProvider:
    """Build a Twilio adapter from explicitly resolved runtime credentials.

    This factory is for native tools that resolve organization-owned
    credentials at call assembly time.
    """
    return TwilioSmsProvider(
        account_sid=account_sid,
        auth_token=auth_token,
        default_from_phone=default_from_phone,
    )
