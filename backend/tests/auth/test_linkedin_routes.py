"""Tests for direct LinkedIn OAuth API routes."""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from src.auth.models import AuthResponse, LinkedInCodeExchangeRequest, UserProfile
from src.auth.oauth_identity import OAuthVerifiedIdentity
from starlette.requests import Request


USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _request() -> Request:
    """Create the Starlette request object required by slowapi."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/linkedin",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 8000),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


@pytest.mark.asyncio
async def test_linkedin_authorize_redirects_to_provider() -> None:
    """The authorization endpoint redirects the browser to LinkedIn."""
    from src.auth.routes import linkedin_authorize

    with patch("src.auth.routes.linkedin_oauth_service") as service:
        service.create_authorization_url.return_value = (
            "https://www.linkedin.com/oauth/v2/authorization?state=signed",
            "signed",
        )

        response = await linkedin_authorize(request=_request())

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://www.linkedin.com/")


@pytest.mark.asyncio
async def test_linkedin_exchange_returns_supabase_session() -> None:
    """The exchange route returns a Supabase session for the frontend."""
    from src.auth.routes import linkedin_exchange

    identity = OAuthVerifiedIdentity(
        provider="linkedin",
        email="person@example.com",
        first_name="Person",
        last_name="Example",
        provider_sub="linkedin-user-id",
    )
    auth_response = AuthResponse(
        access_token="supabase-access-token",
        refresh_token="supabase-refresh-token",
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

    with patch("src.auth.routes.linkedin_oauth_service") as oauth_service, patch(
        "src.auth.routes.oauth_session_service"
    ) as session_service:
        oauth_service.exchange_code = AsyncMock(return_value=identity)
        session_service.complete_oauth_sign_in = AsyncMock(
            return_value=(auth_response, None)
        )

        response = await linkedin_exchange(
            request=_request(),
            body=LinkedInCodeExchangeRequest(code="code", state="state"),
        )

    assert response.access_token == "supabase-access-token"
    assert response.refresh_token == "supabase-refresh-token"
    assert response.user.email == "person@example.com"
    oauth_service.exchange_code.assert_awaited_once_with("code", "state")
    session_service.complete_oauth_sign_in.assert_awaited_once_with(identity)


@pytest.mark.asyncio
async def test_linkedin_exchange_maps_invalid_state_to_bad_request() -> None:
    """Forged state is reported as a client error without leaking details."""
    from src.auth.linkedin_oauth import LinkedInOAuthError
    from src.auth.routes import linkedin_exchange

    with patch("src.auth.routes.linkedin_oauth_service") as service:
        service.exchange_code = AsyncMock(
            side_effect=LinkedInOAuthError("Invalid LinkedIn OAuth state.")
        )

        with pytest.raises(HTTPException) as error:
            await linkedin_exchange(
                request=_request(),
                body=LinkedInCodeExchangeRequest(code="code", state="state"),
            )

    assert error.value.status_code == 400
    assert error.value.detail == "LinkedIn authentication could not be completed."
