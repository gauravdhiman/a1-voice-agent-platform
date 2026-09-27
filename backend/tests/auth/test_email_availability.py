"""Tests for signup email availability checks."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from src.auth.models import SignUpRequest
from src.auth.service import AuthService


@pytest.fixture
def auth_service(mock_supabase_client, mock_supabase_auth) -> AuthService:
    mock_supabase_client.auth = mock_supabase_auth
    with patch("src.auth.service.supabase_config") as mock_config, patch(
        "src.auth.service.create_isolated_supabase_client",
        return_value=mock_supabase_client,
    ), patch(
        "src.notifications.platform_settings_service."
        "platform_notification_settings_service.is_email_verification_required",
        new=AsyncMock(return_value=False),
    ):
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True
        service = AuthService()
        service.supabase_config = mock_config
        yield service


class TestCheckEmailAvailability:
    """Public email availability endpoint backing logic."""

    @pytest.mark.asyncio
    async def test_returns_available_for_new_email(
        self, auth_service: AuthService
    ) -> None:
        with patch.object(
            auth_service, "_find_auth_user_by_email", new=AsyncMock(return_value=None)
        ):
            result, error = await auth_service.check_email_availability(
                "new@example.com"
            )

        assert error is None
        assert result.exists is False
        assert result.sign_in_methods == []

    @pytest.mark.asyncio
    async def test_returns_methods_for_existing_email(
        self, auth_service: AuthService
    ) -> None:
        existing_user = SimpleNamespace(
            identities=[SimpleNamespace(provider="google")],
            user_metadata={"google_sub": "sub-1"},
            encrypted_password=None,
        )

        with patch.object(
            auth_service,
            "_find_auth_user_by_email",
            new=AsyncMock(return_value=existing_user),
        ), patch.object(
            auth_service,
            "_hydrate_auth_user",
            side_effect=lambda user: user,
        ):
            result, error = await auth_service.check_email_availability(
                "existing@example.com"
            )

        assert error is None
        assert result.exists is True
        assert result.sign_in_methods == ["google"]
        assert "Google" in (result.message or "")


class TestAuthUserExists:
    """Internal existence checks used by verified OAuth callbacks."""

    @pytest.mark.asyncio
    async def test_returns_true_for_existing_auth_user(
        self, auth_service: AuthService
    ) -> None:
        with patch.object(
            auth_service,
            "_find_auth_user_by_email",
            new=AsyncMock(return_value=object()),
        ) as lookup:
            assert await auth_service.auth_user_exists("existing@example.com") is True

        lookup.assert_awaited_once_with("existing@example.com")

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_auth_user(
        self, auth_service: AuthService
    ) -> None:
        with patch.object(
            auth_service,
            "_find_auth_user_by_email",
            new=AsyncMock(return_value=None),
        ) as lookup:
            assert await auth_service.auth_user_exists("new@example.com") is False

        lookup.assert_awaited_once_with("new@example.com")


class TestSignUpExistingUserConflict:
    """Signup conflicts should include structured sign-in guidance."""

    @pytest.mark.asyncio
    async def test_sign_up_conflict_includes_sign_in_methods(
        self,
        auth_service: AuthService,
        mock_supabase_auth: MagicMock,
    ) -> None:
        try:
            from supabase_auth.errors import AuthApiError
        except ImportError:  # pragma: no cover
            from gotrue.errors import AuthApiError

        mock_supabase_auth.admin.create_user.side_effect = AuthApiError(
            "User already registered", 422, "user_already_exists"
        )

        request = SignUpRequest(
            email="existing@example.com",
            password="Password123!",
            password_confirm="Password123!",
            first_name="Existing",
            last_name="User",
        )

        with patch.object(
            auth_service,
            "_find_auth_user_by_email",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    id="user-1",
                    identities=[SimpleNamespace(provider="email")],
                    user_metadata={"google_sub": "sub-1"},
                    encrypted_password=None,
                )
            ),
        ):
            result, error = await auth_service.sign_up(request)

        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_409_CONFLICT
        assert isinstance(error.detail, dict)
        assert error.detail["sign_in_methods"] == ["google"]
        assert "Google" in error.detail["message"]
