"""Cloudflare Turnstile bot protection (Epic E hardening).

Verification is enforced only when ``TURNSTILE_SECRET_KEY`` is configured;
without it (local/dev) every token is accepted so development never needs
a Cloudflare account. Production must set the secret plus the frontend
``NEXT_PUBLIC_TURNSTILE_SITE_KEY``.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
_TIMEOUT_SECONDS = 8.0


def is_turnstile_configured() -> bool:
    """Return True when Turnstile verification is active."""
    return bool(settings.turnstile_secret_key)


async def verify_turnstile_token(
    token: Optional[str], remote_ip: Optional[str] = None
) -> bool:
    """Verify a Turnstile client token with Cloudflare.

    Args:
        token: Client-side Turnstile token (may be missing).
        remote_ip: Caller IP forwarded for Cloudflare risk analysis.

    Returns:
        True when verification is disabled (no secret configured) or
        Cloudflare confirms the token; False otherwise (missing token,
        rejection, timeout, or transport failure).
    """
    secret = settings.turnstile_secret_key
    if not secret:
        return True
    if not token:
        return False
    payload: dict[str, str] = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(_VERIFY_URL, data=payload)
    except Exception:
        logger.error("Turnstile verification transport failed", exc_info=True)
        return False
    try:
        return bool(response.json().get("success", False))
    except Exception:
        logger.error("Turnstile verification response unparseable", exc_info=True)
        return False
