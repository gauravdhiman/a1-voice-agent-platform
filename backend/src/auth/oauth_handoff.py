"""Short-lived signed handoff tokens for OAuth session delivery after redirects."""

from __future__ import annotations

import time
from typing import Any

import jwt

from shared.config import settings

from .models import AuthResponse

HANDOFF_PURPOSE = "oauth-session-handoff"
HANDOFF_TTL_SECONDS = 120


def create_session_handoff_token(auth_response: AuthResponse) -> str:
    """Create a signed, short-lived token carrying Supabase session credentials.

    HTTP redirects cannot reliably deliver URL fragments to the browser, so OAuth
    callbacks redirect with this query parameter instead. The frontend exchanges
    it once over HTTPS for the underlying session tokens.
    """
    if not settings.jwt_secret_key:
        raise ValueError("JWT secret is required for OAuth session handoff.")

    payload = {
        "purpose": HANDOFF_PURPOSE,
        "access_token": auth_response.access_token,
        "refresh_token": auth_response.refresh_token,
        "expires_in": auth_response.expires_in,
        "token_type": auth_response.token_type,
        "exp": int(time.time()) + HANDOFF_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def consume_session_handoff_token(handoff_token: str) -> dict[str, Any]:
    """Validate and decode a one-time OAuth session handoff token."""
    if not settings.jwt_secret_key:
        raise ValueError("JWT secret is required for OAuth session handoff.")

    payload = jwt.decode(
        handoff_token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )
    if payload.get("purpose") != HANDOFF_PURPOSE:
        raise jwt.InvalidTokenError("Invalid OAuth session handoff token.")

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not access_token or not refresh_token:
        raise jwt.InvalidTokenError("OAuth session handoff token is incomplete.")

    return payload
