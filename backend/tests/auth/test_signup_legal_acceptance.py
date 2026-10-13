"""Tests for legal acceptance capture during email/password signup.

Covers two ordering/robustness contracts in ``src.auth.routes.sign_up``:

- the Terms & Conditions / Privacy Policy gate runs before any captcha or
  service work, so an unsigned-up visitor never reaches Turnstile,
- acceptance capture records the published versions with ``source="signup"``
  plus request audit fields, and can never fail an already-completed signup.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from limits.storage import MemoryStorage
from src.auth.models import SignUpRequest
from src.security.rate_limiter import limiter

TERMS_REJECTION_DETAIL = (
    "You must accept the Terms & Conditions and Privacy Policy to sign up."
)


@pytest.fixture(autouse=True)
def _fresh_rate_limit_bucket():
    """Give each test its own slowapi storage bucket.

    ``sign_up`` is rate limited to 5 requests/minute per client IP; without
    isolation the fixed test client IP exhausts the shared in-memory bucket
    part-way through the module.
    """
    fresh = MemoryStorage()
    with patch.object(limiter, "_storage", fresh), patch.object(
        limiter._limiter, "storage", fresh
    ):
        yield


def _signup_body(**overrides) -> SignUpRequest:
    data = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "first_name": "New",
        "last_name": "User",
        "terms_accepted": True,
    }
    data.update(overrides)
    return SignUpRequest(**data)


def _request():
    """Minimal Starlette request satisfying the slowapi wrapper."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/signup",
        "headers": [(b"user-agent", b"TestAgent/1.0")],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 50000),
    }
    return Request(scope)


class TestTermsGatePrecedence:
    @pytest.mark.asyncio
    async def test_rejection_precedes_captcha_and_service(self):
        from src.auth.routes import sign_up

        with patch("src.auth.routes.is_turnstile_configured", return_value=True), patch(
            "src.auth.routes.verify_turnstile_token", new=AsyncMock()
        ) as verify, patch("src.auth.routes.auth_service") as mock_auth, patch(
            "src.auth.routes.legal_service"
        ) as mock_legal, patch(
            "src.auth.routes.organization_service"
        ):
            mock_auth.sign_up = AsyncMock()
            mock_legal.record_user_acceptance = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await sign_up(
                    request=_request(), body=_signup_body(terms_accepted=False)
                )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == TERMS_REJECTION_DETAIL
        verify.assert_not_awaited()
        mock_auth.sign_up.assert_not_awaited()
        mock_legal.record_user_acceptance.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rejection_happens_even_with_captcha_passing(self):
        """The gate is checked first even when every later check would pass."""
        from src.auth.routes import sign_up

        with patch(
            "src.auth.routes.is_turnstile_configured", return_value=False
        ), patch("src.auth.routes.auth_service") as mock_auth, patch(
            "src.auth.routes.organization_service"
        ):
            mock_auth.sign_up = AsyncMock(return_value=(Mock(), None))
            with pytest.raises(HTTPException) as exc_info:
                await sign_up(
                    request=_request(), body=_signup_body(terms_accepted=False)
                )
        assert exc_info.value.status_code == 400


class TestSignupAcceptanceCapture:
    @pytest.mark.asyncio
    async def test_accepted_signup_records_source_and_audit_fields(self):
        from src.auth.routes import sign_up

        sentinel = Mock()
        sentinel.user.id = "user-1"
        with patch(
            "src.auth.routes.is_turnstile_configured", return_value=False
        ), patch(
            "src.auth.routes.is_signup_allowed",
            new=AsyncMock(return_value=(True, None)),
        ), patch(
            "src.auth.routes.auth_service"
        ) as mock_auth, patch(
            "src.auth.routes.legal_service"
        ) as mock_legal, patch(
            "src.auth.routes.organization_service"
        ):
            mock_auth.sign_up = AsyncMock(return_value=(sentinel, None))
            mock_legal.record_user_acceptance = AsyncMock(return_value=2)
            result = await sign_up(request=_request(), body=_signup_body())

        assert result is sentinel
        mock_legal.record_user_acceptance.assert_awaited_once_with(
            "user-1",
            source="signup",
            user_agent="TestAgent/1.0",
            ip_address="127.0.0.1",
        )

    @pytest.mark.asyncio
    async def test_acceptance_failure_never_fails_completed_signup(self):
        from src.auth.routes import sign_up

        sentinel = Mock()
        sentinel.user.id = "user-1"
        with patch(
            "src.auth.routes.is_turnstile_configured", return_value=False
        ), patch(
            "src.auth.routes.is_signup_allowed",
            new=AsyncMock(return_value=(True, None)),
        ), patch(
            "src.auth.routes.auth_service"
        ) as mock_auth, patch(
            "src.auth.routes.legal_service"
        ) as mock_legal, patch(
            "src.auth.routes.organization_service"
        ):
            mock_auth.sign_up = AsyncMock(return_value=(sentinel, None))
            mock_legal.record_user_acceptance = AsyncMock(
                side_effect=RuntimeError("acceptance store down")
            )
            result = await sign_up(request=_request(), body=_signup_body())

        assert result is sentinel
        mock_legal.record_user_acceptance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_signup_error_short_circuits_acceptance(self):
        """A failed signup must not record acceptance for a user that does not exist."""
        from fastapi import status as http_status
        from src.auth.routes import sign_up

        error = HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail={"message": "User already exists"},
        )
        with patch(
            "src.auth.routes.is_turnstile_configured", return_value=False
        ), patch(
            "src.auth.routes.is_signup_allowed",
            new=AsyncMock(return_value=(True, None)),
        ), patch(
            "src.auth.routes.auth_service"
        ) as mock_auth, patch(
            "src.auth.routes.legal_service"
        ) as mock_legal, patch(
            "src.auth.routes.organization_service"
        ):
            mock_auth.sign_up = AsyncMock(return_value=(None, error))
            mock_legal.record_user_acceptance = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await sign_up(request=_request(), body=_signup_body())

        assert exc_info.value is error
        mock_legal.record_user_acceptance.assert_not_awaited()
