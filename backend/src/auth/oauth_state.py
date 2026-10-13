"""Signed OAuth state helpers shared by provider brokers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Mapping

STATE_TTL_SECONDS = 10 * 60


def create_signed_state(
    *,
    purpose: str,
    redirect_uri: str,
    jwt_secret_key: str,
    invitation_token: str | None = None,
    terms_accepted: bool = False,
) -> str:
    """Create a signed, short-lived OAuth state payload.

    ``terms_accepted`` records that the visitor acknowledged the Terms &
    Conditions and Privacy Policy before leaving for the provider. The flag is
    covered by the HMAC signature, so the callback can trust it.
    """
    payload: dict[str, Any] = {
        "purpose": purpose,
        "redirect_uri": redirect_uri,
        "csrf": secrets.token_urlsafe(24),
        "expires_at": int(time.time()) + STATE_TTL_SECONDS,
        "terms_accepted": bool(terms_accepted),
    }
    if invitation_token:
        payload["invitation_token"] = invitation_token

    encoded_payload = _encode_state_payload(payload)
    signature = hmac.new(
        jwt_secret_key.encode("utf-8"),
        encoded_payload,
        hashlib.sha256,
    ).hexdigest()
    payload["signature"] = signature
    return _encode_state_payload(payload).decode("ascii")


def validate_signed_state(
    state: str,
    *,
    purpose: str,
    redirect_uri: str,
    jwt_secret_key: str,
) -> dict[str, Any]:
    """Validate state signature, purpose, redirect URI, and expiration."""
    try:
        encoded_state = state.encode("ascii")
        padding = b"=" * (-len(encoded_state) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(encoded_state + padding).decode("utf-8")
        )
        signature = payload.pop("signature")
        unsigned_payload = _encode_state_payload(payload)
        expected_signature = hmac.new(
            jwt_secret_key.encode("utf-8"),
            unsigned_payload,
            hashlib.sha256,
        ).hexdigest()
        is_valid_signature = hmac.compare_digest(signature, expected_signature)
        is_valid_payload = (
            payload.get("purpose") == purpose
            and payload.get("redirect_uri") == redirect_uri
            and int(payload.get("expires_at", 0)) >= int(time.time())
        )
    except (TypeError, ValueError, KeyError, UnicodeError, json.JSONDecodeError):
        is_valid_signature = False
        is_valid_payload = False

    if not is_valid_signature or not is_valid_payload:
        raise ValueError("Invalid OAuth state.")

    return payload


def _encode_state_payload(payload: Mapping[str, Any]) -> bytes:
    """Serialize a state payload deterministically for HMAC signing."""
    encoded_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    return base64.urlsafe_b64encode(encoded_json).rstrip(b"=")
