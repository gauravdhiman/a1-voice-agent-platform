"""Tests for backend email signup with Resend verification and admin alerts."""

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


def _build_admin_create_user_response() -> MagicMock:
    now = datetime.now(timezone.utc)
    user_mock = MagicMock()
    user_mock.id = str(USER_ID)
    user_mock.email = "newuser@example.com"
    user_mock.user_metadata = {"first_name": "New", "last_name": "User"}
    user_mock.email_confirmed_at = None
    user_mock.created_at = now
    user_mock.updated_at = now

    response_mock = MagicMock()
    response_mock.user = user_mock
    return response_mock


def _signup_patches(*, verification_required: bool = True):
    return patch(
        "src.notifications.platform_settings_service.platform_notification_settings_service.is_email_verification_required",
        new=AsyncMock(return_value=verification_required),
    ), patch(
        "src.notifications.email_verification_service.email_verification_service.create_and_send_verification",
        new=AsyncMock(return_value=(True, None)),
    ), patch(
        "src.notifications.signup_notifier.signup_notifier.notify_new_user",
        new=AsyncMock(),
    ), patch(
        "src.auth.service.ensure_default_organization_for_user",
        new=AsyncMock(return_value=(ORG_ID, None)),
    )


class TestAuthServiceSignUpFlow:
    """Signup creates unverified users, sends Resend email, and alerts admins."""

    @pytest.mark.asyncio
    async def test_sign_up_requires_email_verification_when_active(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        mock_supabase_auth.admin.create_user.return_value = (
            _build_admin_create_user_response()
        )

        settings_patch, verify_patch, notify_patch, provision_patch = _signup_patches(
            verification_required=True
        )
        with settings_patch, verify_patch as verify_mock, notify_patch as notify_mock, provision_patch:
            result, error = await auth_service.sign_up(sign_up_request)

        assert error is None
        assert result is not None
        assert result.email_verification_required is True
        assert result.access_token is None
        assert result.refresh_token is None
        verify_mock.assert_awaited_once()
        notify_mock.assert_awaited_once()
        create_kwargs = mock_supabase_auth.admin.create_user.call_args[0][0]
        assert create_kwargs["email_confirm"] is False

    @pytest.mark.asyncio
    async def test_sign_up_skips_verification_when_disabled(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        confirmed_response = _build_admin_create_user_response()
        confirmed_response.user.email_confirmed_at = datetime.now(timezone.utc)
        mock_supabase_auth.admin.create_user.return_value = confirmed_response

        session_mock = MagicMock()
        session_mock.access_token = "signup-access-token"
        session_mock.refresh_token = "signup-refresh-token"
        session_mock.expires_in = 3600
        sign_in_response = MagicMock()
        sign_in_response.session = session_mock
        sign_in_response.user = confirmed_response.user
        mock_supabase_auth.sign_in_with_password.return_value = sign_in_response

        settings_patch, verify_patch, notify_patch, provision_patch = _signup_patches(
            verification_required=False
        )
        with settings_patch, verify_patch as verify_mock, notify_patch, provision_patch:
            result, error = await auth_service.sign_up(sign_up_request)

        assert error is None
        assert result is not None
        assert result.email_verification_required is False
        assert result.access_token == "signup-access-token"
        assert result.refresh_token == "signup-refresh-token"
        verify_mock.assert_not_awaited()
        create_kwargs = mock_supabase_auth.admin.create_user.call_args[0][0]
        assert create_kwargs["email_confirm"] is True
        mock_supabase_auth.sign_in_with_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_up_sends_verification_email_via_resend(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        mock_supabase_auth.admin.create_user.return_value = (
            _build_admin_create_user_response()
        )

        settings_patch, verify_patch, notify_patch, provision_patch = _signup_patches()
        with settings_patch, verify_patch as verify_mock, notify_patch, provision_patch:
            await auth_service.sign_up(sign_up_request)

        verify_mock.assert_awaited_once_with(
            USER_ID,
            "newuser@example.com",
            "New User",
        )

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
        mock_supabase_auth.admin.create_user.return_value = (
            _build_admin_create_user_response()
        )

        invitation = MagicMock()
        invitation.organization_id = ORG_ID
        invitation.organization_name = "Acme Plumbing"

        settings_patch, verify_patch, notify_patch, _ = _signup_patches()
        with settings_patch, verify_patch, notify_patch as notify_mock, patch(
            "src.auth.service.organization_service.process_invitation",
            new=AsyncMock(return_value=(invitation, None)),
        ) as invite_mock, patch(
            "src.auth.service.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ) as provision_mock:
            result, error = await auth_service.sign_up(request)

        assert error is None
        assert result is not None
        assert result.joined_organization_id == ORG_ID
        assert result.joined_organization_name == "Acme Plumbing"
        invite_mock.assert_awaited_once_with("invite-token-123", USER_ID)
        provision_mock.assert_awaited_once()
        notify_mock.assert_awaited_once()
        assert notify_mock.await_args.kwargs["method"] == "invitation"
        assert notify_mock.await_args.kwargs["organization_name"] == "Acme Plumbing"

    @pytest.mark.asyncio
    async def test_sign_up_existing_user_returns_conflict(
        self,
        auth_service: AuthService,
        sign_up_request: SignUpRequest,
        mock_supabase_auth: MagicMock,
    ) -> None:
        mock_supabase_auth.admin.create_user.side_effect = AuthApiError(
            "User already registered", 422, "user_already_exists"
        )

        with patch(
            "src.notifications.platform_settings_service.platform_notification_settings_service.is_email_verification_required",
            new=AsyncMock(return_value=True),
        ):
            result, error = await auth_service.sign_up(sign_up_request)

        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_409_CONFLICT
