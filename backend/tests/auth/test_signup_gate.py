"""Tests for the controlled-SaaS signup gate (Epic A: gated entry).

Covers ``src.auth.signup_gate`` unit behavior plus the ``POST /signup``
wiring in ``src.auth.routes``:

- Open gate (``PUBLIC_SIGNUP_ENABLED=true``) admits everyone.
- Closed gate admits allowlisted admins and usable invitation tokens only.
- Closed gate denies strangers and spent/unknown tokens with the same
  ``signup_disabled`` code (no token-validity oracle).
- The signup route denies before reaching ``auth_service.sign_up``.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from src.auth.models import SignUpRequest
from src.auth.signup_gate import (
    SIGNUP_DISABLED_CODE,
    invitation_token_usable,
    is_allowlisted,
    is_signup_allowed,
)


def _invitation_client(rows=None, explode=False):
    """Build a fake service-role client returning the given invitation rows."""
    response = MagicMock()
    response.data = rows if rows is not None else []
    execute = MagicMock(return_value=response)
    if explode:
        execute.side_effect = RuntimeError("db down")
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute = execute
    return client


def _pending_row():
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "pending",
        "expires_at": "2099-01-01T00:00:00Z",
    }


class TestIsAllowlisted:
    def test_match_is_case_insensitive(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.platform_admin_allowlist = ["boss@example.com"]
            assert is_allowlisted("BOSS@example.com") is True
            assert is_allowlisted("  boss@example.com  ") is True

    def test_stranger_is_not_allowlisted(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.platform_admin_allowlist = ["boss@example.com"]
            assert is_allowlisted("stranger@example.com") is False


class TestInvitationTokenUsable:
    @pytest.mark.asyncio
    async def test_pending_token_is_usable(self):
        assert await invitation_token_usable("tok", _invitation_client([_pending_row()])) is True

    @pytest.mark.asyncio
    async def test_missing_token_is_not_usable(self):
        assert await invitation_token_usable("tok", _invitation_client([])) is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["accepted", "expired", "revoked"])
    async def test_closed_status_is_not_usable(self, status):
        row = _pending_row()
        row["status"] = status
        assert await invitation_token_usable("tok", _invitation_client([row])) is False

    @pytest.mark.asyncio
    async def test_past_expiry_is_not_usable(self):
        row = _pending_row()
        row["expires_at"] = "2000-01-01T00:00:00Z"
        assert await invitation_token_usable("tok", _invitation_client([row])) is False

    @pytest.mark.asyncio
    async def test_lookup_failure_is_not_usable(self):
        assert await invitation_token_usable("tok", _invitation_client(explode=True)) is False


class TestIsSignupAllowed:
    @pytest.mark.asyncio
    async def test_open_gate_admits_stranger_without_lookup(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.public_signup_enabled = True
            mock_settings.platform_admin_allowlist = []
            client = _invitation_client()
            allowed, denial = await is_signup_allowed("x@y.com", supabase=client)
            assert (allowed, denial) == (True, None)
            client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_closed_gate_admits_allowlisted_admin(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.public_signup_enabled = False
            mock_settings.platform_admin_allowlist = ["boss@example.com"]
            allowed, denial = await is_signup_allowed("boss@example.com")
            assert (allowed, denial) == (True, None)

    @pytest.mark.asyncio
    async def test_closed_gate_denies_stranger(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.public_signup_enabled = False
            mock_settings.platform_admin_allowlist = []
            allowed, denial = await is_signup_allowed("x@y.com")
            assert allowed is False
            assert denial == SIGNUP_DISABLED_CODE

    @pytest.mark.asyncio
    async def test_closed_gate_admits_usable_invitation(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.public_signup_enabled = False
            mock_settings.platform_admin_allowlist = []
            client = _invitation_client([_pending_row()])
            allowed, denial = await is_signup_allowed(
                "x@y.com", invitation_token="tok", supabase=client
            )
            assert (allowed, denial) == (True, None)

    @pytest.mark.asyncio
    async def test_closed_gate_denies_spent_invitation_with_same_code(self):
        """Spent and unknown tokens share one code: no validity oracle."""
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.public_signup_enabled = False
            mock_settings.platform_admin_allowlist = []
            row = _pending_row()
            row["status"] = "accepted"
            allowed, denial = await is_signup_allowed(
                "x@y.com",
                invitation_token="tok",
                supabase=_invitation_client([row]),
            )
            assert allowed is False
            assert denial == SIGNUP_DISABLED_CODE

    @pytest.mark.asyncio
    async def test_token_without_client_cannot_pass_closed_gate(self):
        with patch("src.auth.signup_gate.settings") as mock_settings:
            mock_settings.public_signup_enabled = False
            mock_settings.platform_admin_allowlist = []
            allowed, denial = await is_signup_allowed("x@y.com", invitation_token="tok")
            assert allowed is False
            assert denial == SIGNUP_DISABLED_CODE


def _signup_body(**overrides):
    data = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "first_name": "New",
        "last_name": "User",
    }
    data.update(overrides)
    return SignUpRequest(**data)


class TestSignUpRouteGate:
    """POST /signup enforces the gate before touching auth_service."""

    @staticmethod
    def _request():
        """Minimal Starlette request satisfying the slowapi wrapper."""
        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/signup",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("127.0.0.1", 50000),
        }
        return Request(scope)

    @pytest.mark.asyncio
    async def test_denied_signup_raises_403_without_calling_service(self):
        from src.auth.routes import sign_up

        with patch(
            "src.auth.routes.is_signup_allowed",
            new=AsyncMock(return_value=(False, SIGNUP_DISABLED_CODE)),
        ), patch("src.auth.routes.auth_service") as mock_service, patch(
            "src.auth.routes.organization_service"
        ):
            mock_service.sign_up = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await sign_up(request=self._request(), body=_signup_body())
            assert exc_info.value.status_code == 403
            assert SIGNUP_DISABLED_CODE in str(exc_info.value.detail)
            mock_service.sign_up.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_signup_reaches_service(self):
        from src.auth.routes import sign_up

        sentinel = Mock()
        sentinel.user = Mock(id="user-1")
        with patch(
            "src.auth.routes.is_signup_allowed",
            new=AsyncMock(return_value=(True, None)),
        ), patch("src.auth.routes.auth_service") as mock_service, patch(
            "src.auth.routes.organization_service"
        ):
            mock_service.sign_up = AsyncMock(return_value=(sentinel, None))
            result = await sign_up(request=self._request(), body=_signup_body())
            assert result is sentinel
            mock_service.sign_up.assert_awaited_once()
