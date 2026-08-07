"""Tests for LinkedIn -> Supabase session completion on the backend."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from gotrue.errors import AuthApiError

from src.auth.linkedin_oauth import LinkedInVerifiedIdentity
from src.auth.linkedin_supabase_session import LinkedInSupabaseSessionService


USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def identity() -> LinkedInVerifiedIdentity:
    return LinkedInVerifiedIdentity(
        email="member@example.com",
        first_name="Ada",
        last_name="Lovelace",
        linkedin_sub="linkedin-sub-123",
        picture="https://cdn.example/avatar.png",
    )


@pytest.fixture
def mock_supabase() -> MagicMock:
    client = MagicMock()
    session = MagicMock()
    session.access_token = "supabase-access-token"
    session.refresh_token = "supabase-refresh-token"
    session.expires_in = 3600

    user = MagicMock()
    user.id = str(USER_ID)
    user.email = "member@example.com"
    user.user_metadata = {"first_name": "Ada", "last_name": "Lovelace"}
    user.email_confirmed_at = "2026-01-01T00:00:00Z"
    user.created_at = "2026-01-01T00:00:00Z"
    user.updated_at = "2026-01-02T00:00:00Z"

    verify_response = MagicMock()
    verify_response.user = user
    verify_response.session = session
    client.auth.verify_otp.return_value = verify_response

    link_properties = MagicMock()
    link_properties.hashed_token = "hashed-magic-token"
    link_response = MagicMock()
    link_response.properties = link_properties
    client.auth.admin.generate_link.return_value = link_response

    return client


class TestLinkedInSupabaseSessionService:
    """Ensure LinkedIn identities become Supabase sessions server-side."""

    @pytest.mark.asyncio
    async def test_create_session_provisions_default_organization(
        self, identity: LinkedInVerifiedIdentity, mock_supabase: MagicMock
    ) -> None:
        service = LinkedInSupabaseSessionService(supabase_client=mock_supabase)

        with patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(USER_ID, None)),
        ) as provision, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            auth_response, error = await service.create_session(identity)

        assert error is None
        assert auth_response is not None
        provision.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_session_creates_user_when_missing(
        self, identity: LinkedInVerifiedIdentity, mock_supabase: MagicMock
    ) -> None:
        service = LinkedInSupabaseSessionService(supabase_client=mock_supabase)

        with patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ), patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            auth_response, error = await service.create_session(identity)

        assert error is None
        assert auth_response is not None
        assert auth_response.access_token == "supabase-access-token"
        assert auth_response.refresh_token == "supabase-refresh-token"
        assert auth_response.user.email == "member@example.com"
        mock_supabase.auth.admin.create_user.assert_called_once()
        mock_supabase.auth.admin.generate_link.assert_called_once()
        mock_supabase.auth.verify_otp.assert_called_once_with(
            {"token_hash": "hashed-magic-token", "type": "email"}
        )

    @pytest.mark.asyncio
    async def test_create_session_reuses_existing_user(
        self, identity: LinkedInVerifiedIdentity, mock_supabase: MagicMock
    ) -> None:
        mock_supabase.auth.admin.create_user.side_effect = AuthApiError(
            "User already registered", 422, "user_already_exists"
        )
        service = LinkedInSupabaseSessionService(supabase_client=mock_supabase)

        with patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ), patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            auth_response, error = await service.create_session(identity)

        assert error is None
        assert auth_response is not None
        mock_supabase.auth.admin.generate_link.assert_called_once()
