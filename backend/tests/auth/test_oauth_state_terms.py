"""Tests for the terms-acceptance flag inside the signed OAuth state.

The flag travels from the pre-provider consent page to the OAuth callback, so
it MUST be covered by the HMAC signature: a tampered payload (flag flipped
without the secret) must invalidate the whole state.
"""

import base64
import json

import pytest
from src.auth.oauth_state import (
    STATE_TTL_SECONDS,
    create_signed_state,
    validate_signed_state,
)

SECRET = "test-jwt-secret"
PURPOSE = "oauth_sign_in"
REDIRECT_URI = "https://app.example.com/auth/callback"


def _decode_state(state: str) -> dict:
    padded = state + "=" * (-len(state) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))


class TestTermsFlagRoundTrip:
    def test_accepted_flag_survives_validation(self):
        state = create_signed_state(
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
            terms_accepted=True,
        )
        payload = validate_signed_state(
            state,
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
        )
        assert payload["terms_accepted"] is True
        assert payload["purpose"] == PURPOSE
        assert payload["redirect_uri"] == REDIRECT_URI

    def test_flag_defaults_to_false(self):
        state = create_signed_state(
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
        )
        payload = validate_signed_state(
            state,
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
        )
        assert payload["terms_accepted"] is False

    def test_expiration_is_short_lived(self):
        import time

        state = create_signed_state(
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
            terms_accepted=True,
        )
        payload = _decode_state(state)
        now = int(time.time())
        # The TTL contract: expiry is bounded by STATE_TTL_SECONDS from now.
        assert now <= payload["expires_at"] <= now + STATE_TTL_SECONDS


class TestTermsFlagTampering:
    def test_flipping_the_flag_invalidates_the_state(self):
        state = create_signed_state(
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
            terms_accepted=False,
        )
        payload = _decode_state(state)
        payload["terms_accepted"] = True  # flip without re-signing
        forged = (
            base64.urlsafe_b64encode(
                json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
                    "utf-8"
                )
            )
            .rstrip(b"=")
            .decode("ascii")
        )
        with pytest.raises(ValueError, match="Invalid OAuth state"):
            validate_signed_state(
                forged,
                purpose=PURPOSE,
                redirect_uri=REDIRECT_URI,
                jwt_secret_key=SECRET,
            )

    def test_signature_bound_to_secret(self):
        state = create_signed_state(
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
            terms_accepted=True,
        )
        with pytest.raises(ValueError, match="Invalid OAuth state"):
            validate_signed_state(
                state,
                purpose=PURPOSE,
                redirect_uri=REDIRECT_URI,
                jwt_secret_key="wrong-secret",
            )

    def test_signature_bound_to_purpose(self):
        state = create_signed_state(
            purpose=PURPOSE,
            redirect_uri=REDIRECT_URI,
            jwt_secret_key=SECRET,
            terms_accepted=True,
        )
        with pytest.raises(ValueError, match="Invalid OAuth state"):
            validate_signed_state(
                state,
                purpose="password_reset",
                redirect_uri=REDIRECT_URI,
                jwt_secret_key=SECRET,
            )
