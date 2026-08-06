"""Tests for OAuth session handoff tokens."""

import time

import jwt
import pytest
from src.auth.models import AuthResponse, UserProfile
from src.auth.oauth_handoff import (
    HANDOFF_PURPOSE,
    consume_session_handoff_token,
    create_session_handoff_token,
)
from uuid import UUID


USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class FakeSettings:
    jwt_secret_key = "test-jwt-secret"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.auth.oauth_handoff.settings", FakeSettings)


def _auth_response() -> AuthResponse:
    return AuthResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        token_type="bearer",
        expires_in=3600,
        user=UserProfile(
            id=USER_ID,
            email="person@example.com",
            first_name="Person",
            last_name="Example",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ),
    )


def test_create_and_consume_session_handoff_token() -> None:
    token = create_session_handoff_token(_auth_response())
    payload = consume_session_handoff_token(token)

    assert payload["access_token"] == "access-token"
    assert payload["refresh_token"] == "refresh-token"


def test_rejects_expired_session_handoff_token() -> None:
    token = jwt.encode(
        {
            "purpose": HANDOFF_PURPOSE,
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "exp": int(time.time()) - 10,
        },
        FakeSettings.jwt_secret_key,
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        consume_session_handoff_token(token)
