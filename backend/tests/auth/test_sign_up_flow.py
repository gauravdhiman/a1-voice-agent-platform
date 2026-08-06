"""Tests for backend email signup with org provisioning and verification gating."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

try:
    from supabase_auth.errors import AuthApiError
except ImportError:  # pragma: no cover
    from gotrue.errors import AuthApiError

from src.auth.models import SignUpRequest
from src.auth.service import AuthService

USER_ID = uuid4()
ORG_ID = uuid4()


@pytest.fixture
def sign_up_request() -> SignUpRequest:
    return SignUpRequest(
        email="newuser@example.com",
        password="Password123!",
        password_confirm="Password123!",
        first_name="New",
        last_name="User",
    )


@pytest.fixture
def auth_service(mock_supabase_client, mock_supabase_auth) -> AuthService:
    mock_supabase_client.auth = mock_supabase_auth
    with patch("src.auth.service.supabase_config") as mock_config, patch(
        "src.auth.service.create_isolated_supabase_client",
        return_value=mock_supabase_client,
    ):
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True

        service = AuthService()
        service.supabase_config = mock_config
        yield service


def _build_supabase_signup_response(*, with_session: bool) -> MagicMock:
    now = datetime.now(timezone.utc)
    user_mock = MagicMock()
    user_mock.id = str(USER_ID)
    user_mock.email = "newuser@example.com"
    user_mock.user_metadata = {"first_name": "New", "last_name": "User"}
    user_mock.email_confirmed_at = now if with_session else None
    user_mock.created_at = now
    user_mock.updated_at = now

    response_mock = MagicMock()
    response_mock.user = user_mock
    if with_session:
        session_mock = MagicMock()
        session_mock.access_token = "test-access-token"
        session_mock.refresh_token = "test-refresh-token"
        session_mock.expires_in = 3600
        response_mock.session = session_mock
    else:
        response_mock.session = None
    return response_mock


class TestAuthServiceSignUpFlow:
    """Signup provisions organizations and exposes verification requirements."""

    @pytest.mark.asyncio
    async def test_sign_up_with_session_allows_immediate_sign_in(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        mock_supabase_auth.sign_up.return_value = _build_supabase_signup_response(
            with_session=True
        )

        with patch(
            "src.auth.service.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(ORG_ID, None)),
        ) as provision_mock:
            result, error = await auth_service.sign_up(sign_up_request)

        assert error is None
        assert result is not None
        assert result.email_verification_required is False
        assert result.access_token == "test-access-token"
        assert result.refresh_token == "test-refresh-token"
        provision_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sign_up_without_session_requires_email_verification(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        mock_supabase_auth.sign_up.return_value = _build_supabase_signup_response(
            with_session=False
        )

        with patch(
            "src.auth.service.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(ORG_ID, None)),
        ) as provision_mock:
            result, error = await auth_service.sign_up(sign_up_request)

        assert error is None
        assert result is not None
        assert result.email_verification_required is True
        assert result.access_token is None
        assert result.refresh_token is None
        provision_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sign_up_processes_invitation_before_default_org(
        self,
        auth_service: AuthService,
        mock_supabase_auth: MagicMock,
    ) -> None:
        request = SignUpRequest(
            email="invited@example.com",
            password="Password123!",
            password_confirm="Password123!",
            first_name="Inv",
            last_name="ited",
            invitation_token="invite-token-123",
        )
        mock_supabase_auth.sign_up.return_value = _build_supabase_signup_response(
            with_session=True
        )

        with patch(
            "src.auth.service.organization_service.process_invitation",
            new=AsyncMock(return_value=(MagicMock(), None)),
        ) as invite_mock, patch(
            "src.auth.service.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ) as provision_mock:
            result, error = await auth_service.sign_up(request)

        assert error is None
        assert result is not None
        invite_mock.assert_awaited_once_with("invite-token-123", USER_ID)
        provision_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sign_up_existing_user_returns_conflict(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        mock_supabase_auth.sign_up.side_effect = AuthApiError(
            "User already registered", 422, "user_already_exists"
        )

        result, error = await auth_service.sign_up(sign_up_request)

        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_409_CONFLICT
