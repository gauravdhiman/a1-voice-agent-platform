"""Tests for existing-account OAuth access when public signup is closed."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from starlette.requests import Request

from src.auth.models import AuthResponse, UserProfile
from src.auth.oauth_identity import OAuthVerifiedIdentity
from src.auth.signup_gate import SIGNUP_DISABLED_CODE

USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _request(provider: str) -> Request:
    """Build the Starlette request required by the rate-limit wrapper."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/api/v1/auth/{provider}/callback",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 8000),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


def _identity(
    provider: str, invitation_token: str | None = None
) -> OAuthVerifiedIdentity:
    """Build a verified provider identity for callback tests."""
    return OAuthVerifiedIdentity(
        provider=provider,  # type: ignore[arg-type]
        email=f"{provider}-user@example.com",
        first_name="OAuth",
        last_name="User",
        provider_sub=f"{provider}-subject",
        invitation_token=invitation_token,
    )


def _auth_response(email: str) -> AuthResponse:
    """Build a safe fake session response for callback tests."""
    return AuthResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_in=3600,
        user=UserProfile(
            id=USER_ID,
            email=email,
            first_name="OAuth",
            last_name="User",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        ),
    )


def _callback(provider: str):
    """Return the backend callback under test."""
    from src.auth.routes import google_callback, linkedin_callback

    callback = google_callback if provider == "google" else linkedin_callback
    return callback.__wrapped__


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "linkedin"])
async def test_existing_oauth_account_can_sign_in_when_signup_is_closed(
    provider: str,
) -> None:
    """Existing accounts bypass the new-account signup gate for both providers."""
    identity = _identity(provider)
    gate = AsyncMock(return_value=(False, SIGNUP_DISABLED_CODE))
    session_service = MagicMock()
    session_service.complete_oauth_sign_in = AsyncMock(
        return_value=(_auth_response(identity.email), None)
    )
    auth_service = MagicMock()
    auth_service.auth_user_exists = AsyncMock(return_value=True)
    oauth_service = MagicMock()
    oauth_service.exchange_code = AsyncMock(return_value=identity)
    callback = _callback(provider)

    with patch(f"src.auth.routes.{provider}_oauth_service", oauth_service), patch(
        "src.auth.routes.auth_service", auth_service
    ), patch("src.auth.routes.organization_service") as organization_service, patch(
        "src.auth.routes.is_signup_allowed", new=gate
    ), patch(
        "src.auth.routes.oauth_session_service", session_service
    ), patch(
        "src.auth.routes.oauth_session_redirect",
        return_value="https://app.example.com/auth/session?handoff=one-time",
    ), patch(
        "src.auth.routes.log_auth_event", new=AsyncMock()
    ):
        organization_service.supabase = MagicMock()
        response = await callback(
            request=_request(provider),
            code="oauth-code",
            state="oauth-state",
            error=None,
            error_description=None,
        )

    assert response.status_code == 302
    assert "handoff=one-time" in response.headers["location"]
    auth_service.auth_user_exists.assert_awaited_once_with(identity.email)
    gate.assert_awaited_once()
    session_service.complete_oauth_sign_in.assert_awaited_once_with(identity)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "linkedin"])
async def test_new_uninvited_oauth_account_remains_blocked(
    provider: str,
) -> None:
    """Unknown OAuth identities still receive the invite-only response."""
    identity = _identity(provider)
    gate = AsyncMock(return_value=(False, SIGNUP_DISABLED_CODE))
    session_service = MagicMock()
    session_service.complete_oauth_sign_in = AsyncMock()
    auth_service = MagicMock()
    auth_service.auth_user_exists = AsyncMock(return_value=False)
    oauth_service = MagicMock()
    oauth_service.exchange_code = AsyncMock(return_value=identity)
    callback = _callback(provider)

    with patch(f"src.auth.routes.{provider}_oauth_service", oauth_service), patch(
        "src.auth.routes.auth_service", auth_service
    ), patch("src.auth.routes.organization_service") as organization_service, patch(
        "src.auth.routes.is_signup_allowed", new=gate
    ), patch(
        "src.auth.routes.oauth_session_service", session_service
    ), patch(
        "src.auth.routes.oauth_error_redirect",
        return_value="https://app.example.com/auth/session?error=invite-only",
    ), patch(
        "src.auth.routes.log_auth_event", new=AsyncMock()
    ):
        organization_service.supabase = MagicMock()
        response = await callback(
            request=_request(provider),
            code="oauth-code",
            state="oauth-state",
            error=None,
            error_description=None,
        )

    assert response.status_code == 302
    assert "invite-only" in response.headers["location"]
    auth_service.auth_user_exists.assert_awaited_once_with(identity.email)
    session_service.complete_oauth_sign_in.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "linkedin"])
async def test_new_invited_oauth_account_can_complete_signup(
    provider: str,
) -> None:
    """A new OAuth identity with a usable invitation still signs up."""
    identity = _identity(provider, invitation_token="invitation-token")
    gate = AsyncMock(return_value=(True, None))
    session_service = MagicMock()
    session_service.complete_oauth_sign_in = AsyncMock(
        return_value=(_auth_response(identity.email), None)
    )
    auth_service = MagicMock()
    auth_service.auth_user_exists = AsyncMock()
    oauth_service = MagicMock()
    oauth_service.exchange_code = AsyncMock(return_value=identity)
    callback = _callback(provider)

    with patch(f"src.auth.routes.{provider}_oauth_service", oauth_service), patch(
        "src.auth.routes.auth_service", auth_service
    ), patch("src.auth.routes.organization_service") as organization_service, patch(
        "src.auth.routes.is_signup_allowed", new=gate
    ), patch(
        "src.auth.routes.oauth_session_service", session_service
    ), patch(
        "src.auth.routes.oauth_session_redirect",
        return_value="https://app.example.com/auth/session?handoff=invited",
    ), patch(
        "src.auth.routes.log_auth_event", new=AsyncMock()
    ):
        organization_service.supabase = MagicMock()
        response = await callback(
            request=_request(provider),
            code="oauth-code",
            state="oauth-state",
            error=None,
            error_description=None,
        )

    assert response.status_code == 302
    assert "handoff=invited" in response.headers["location"]
    auth_service.auth_user_exists.assert_not_awaited()
    session_service.complete_oauth_sign_in.assert_awaited_once_with(identity)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "linkedin"])
async def test_oauth_account_lookup_failure_fails_closed(
    provider: str,
) -> None:
    """An unavailable Auth lookup must not create or sign in an account."""
    identity = _identity(provider)
    gate = AsyncMock(return_value=(False, SIGNUP_DISABLED_CODE))
    session_service = MagicMock()
    session_service.complete_oauth_sign_in = AsyncMock()
    auth_service = MagicMock()
    auth_service.auth_user_exists = AsyncMock(
        side_effect=RuntimeError("auth service unavailable")
    )
    oauth_service = MagicMock()
    oauth_service.exchange_code = AsyncMock(return_value=identity)
    callback = _callback(provider)

    with patch(f"src.auth.routes.{provider}_oauth_service", oauth_service), patch(
        "src.auth.routes.auth_service", auth_service
    ), patch("src.auth.routes.organization_service") as organization_service, patch(
        "src.auth.routes.is_signup_allowed", new=gate
    ), patch(
        "src.auth.routes.oauth_session_service", session_service
    ), patch(
        "src.auth.routes.oauth_error_redirect",
        return_value="https://app.example.com/auth/session?error=auth-failed",
    ), patch(
        "src.auth.routes.log_auth_event", new=AsyncMock()
    ):
        organization_service.supabase = MagicMock()
        response = await callback(
            request=_request(provider),
            code="oauth-code",
            state="oauth-state",
            error=None,
            error_description=None,
        )

    assert response.status_code == 302
    assert "auth-failed" in response.headers["location"]
    session_service.complete_oauth_sign_in.assert_not_awaited()
