"""Utilities shared by phone-number provisioning and webhook flows."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlencode

from fastapi import HTTPException, status

from shared.organization.phone_number_models import PhoneNumberSearchMode


@dataclass(frozen=True)
class PhoneNumberWebhookUrls:
    """Canonical inbound and status callback URLs for one phone number."""

    voice_url: str
    status_callback: str


def normalize_phone_number(value: str, country_code: str = "US") -> str:
    """Normalize a phone number into the E.164 format used for routing.

    The first implementation supports common US formatting and already-E.164
    values. International numbers must be supplied with a leading ``+`` until
    country-specific parsing is introduced.

    Args:
        value: User- or provider-supplied phone number.
        country_code: ISO country code used for the US national shortcut.

    Returns:
        The normalized E.164 value.

    Raises:
        HTTPException: If the value is not a plausible E.164 number.
    """
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        normalized = f"+{digits}"
    elif country_code.upper() == "US" and len(digits) == 10:
        normalized = f"+1{digits}"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must be a valid E.164 number or a 10-digit US number",
        )

    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must be a valid E.164 number",
        )
    return normalized


def normalize_search_contains(
    value: str | None,
    search_mode: PhoneNumberSearchMode | str = PhoneNumberSearchMode.CONTAINS,
    country_code: str = "US",
) -> str | None:
    """Convert user input into Twilio's documented phone-search pattern.

    Args:
        value: User-entered phone-number pattern. Formatting characters are
            ignored so values such as ``(480)`` and ``480`` behave identically.
        search_mode: Whether the pattern should match anywhere, at the start,
            or at the end of the available number.
        country_code: ISO country code for the selected provider inventory.
            US national prefixes receive the ``1`` country calling code.

    Returns:
        A Twilio ``contains`` expression, or ``None`` when no digits were
        supplied. Twilio uses ``%`` for an anywhere match, ``+`` for a prefix,
        and ``$`` for a suffix.

    Notes:
        Twilio's prefix syntax expects the country calling code. The frontend
        currently exposes US inventory, so a national prefix such as ``480``
        becomes ``+1480``. Callers searching other countries should include
        the calling code in the entered prefix until country-specific dialing
        metadata is introduced.
    """
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None

    mode = PhoneNumberSearchMode(search_mode)
    if mode is PhoneNumberSearchMode.BEGINS_WITH:
        if country_code.upper() == "US" and not digits.startswith("1"):
            digits = f"1{digits}"
        return f"+{digits}"
    if mode is PhoneNumberSearchMode.ENDS_WITH:
        return f"{digits}$"
    return f"%{digits}%"


def hash_connection_token(token: str) -> str:
    """Hash a customer webhook token before storing it in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_phone_number_webhook_urls(
    api_base_url: str, connection_token: str | None = None
) -> PhoneNumberWebhookUrls:
    """Build the platform's canonical Twilio webhook URLs.

    Customer-managed numbers receive an opaque query token so they can be
    verified without storing their Twilio auth token. Platform-managed numbers
    use the bare endpoints and Twilio signature validation.
    """
    base = api_base_url.rstrip("/")
    suffix = (
        f"?{urlencode({'connection_token': connection_token})}"
        if connection_token
        else ""
    )
    return PhoneNumberWebhookUrls(
        voice_url=f"{base}/api/v1/voice/twilio/incoming{suffix}",
        status_callback=f"{base}/api/v1/voice/twilio/status{suffix}",
    )
