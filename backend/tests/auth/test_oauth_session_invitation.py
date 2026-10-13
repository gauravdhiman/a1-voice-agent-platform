"""Tests that OAuth sign-in processes invitations before org provisioning."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from src.auth.oauth_identity import OAuthVerifiedIdentity
from src.auth.oauth_session import OAuthSessionService

USER_ID = UUID("12345678-1234-5678-1234-567812345678")
INVITED_ORG_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def identity_with_invite() -> OAuthVerifiedIdentity:
    return OAuthVerifiedIdentity(
        provider="google",
        email="invited@example.com",
        first_name="Inv",
        last_name="Ited",
        provider_sub="google-sub-invite",
        invitation_token="invite-token-abc",
        terms_accepted=True,
    )


@pytest.fixture
def identity_without_invite() -> OAuthVerifiedIdentity:
    return OAuthVerifiedIdentity(
        provider="google",
        email="founder@example.com",
        first_name="Found",
        last_name="Er",
        provider_sub="google-sub-founder",
        terms_accepted=True,
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
    user.email = "invited@example.com"
    user.user_metadata = {"first_name": "Inv", "last_name": "Ited"}
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


class TestOAuthSessionInvitationOrdering:
    """Invited OAuth users must join the invited org before personal-org creation."""

    @pytest.mark.asyncio
    async def test_processes_invitation_before_default_organization(
        self,
        identity_with_invite: OAuthVerifiedIdentity,
        mock_supabase: MagicMock,
    ) -> None:
        """Invitation processing must run before ensure_default_organization_for_user."""
        service = OAuthSessionService(auth_client_factory=lambda: mock_supabase)
        call_order: list[str] = []
        invitation = MagicMock()
        invitation.organization_id = INVITED_ORG_ID
        invitation.organization_name = "Acme Plumbing"

        async def track_invite(token: str, user_id: UUID, expected_email: str):
            call_order.append("invite")
            assert token == "invite-token-abc"
            assert user_id == USER_ID
            assert expected_email == "invited@example.com"
            return invitation, None

        async def track_provision(user_id: UUID, email: str, **kwargs):
            call_order.append("provision")
            return None, None

        with patch(
            "src.auth.oauth_session.organization_service.process_invitation",
            new=AsyncMock(side_effect=track_invite),
        ) as invite_mock, patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(side_effect=track_provision),
        ) as provision_mock, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            auth_response, error = await service.complete_oauth_sign_in(
                identity_with_invite
            )

        assert error is None
        assert auth_response is not None
        assert auth_response.joined_organization_id == INVITED_ORG_ID
        assert auth_response.joined_organization_name == "Acme Plumbing"
        invite_mock.assert_awaited_once_with(
            "invite-token-abc", USER_ID, "invited@example.com"
        )
        provision_mock.assert_not_awaited()
        assert call_order == ["invite"]

    @pytest.mark.asyncio
    async def test_invitation_failure_blocks_session_and_org_provisioning(
        self,
        identity_with_invite: OAuthVerifiedIdentity,
        mock_supabase: MagicMock,
    ) -> None:
        """A failed invite must not fall back to a personal organization."""
        service = OAuthSessionService(auth_client_factory=lambda: mock_supabase)

        with patch(
            "src.auth.oauth_session.organization_service.process_invitation",
            new=AsyncMock(return_value=(None, "Invitation expired")),
        ), patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(USER_ID, None)),
        ) as provision_mock, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            auth_response, error = await service.complete_oauth_sign_in(
                identity_with_invite
            )

        assert auth_response is None
        assert error is not None
        assert error.status_code == 400
        assert error.detail == {
            "code": "invitation_error",
            "message": "Invitation expired",
        }
        provision_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_invitation_processing_without_token(
        self,
        identity_without_invite: OAuthVerifiedIdentity,
        mock_supabase: MagicMock,
    ) -> None:
        """Self-signup OAuth must not call process_invitation."""
        mock_supabase.auth.verify_otp.return_value.user.email = "founder@example.com"
        service = OAuthSessionService(auth_client_factory=lambda: mock_supabase)

        with patch(
            "src.auth.oauth_session.organization_service.process_invitation",
            new=AsyncMock(return_value=(MagicMock(), None)),
        ) as invite_mock, patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(USER_ID, None)),
        ), patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            auth_response, error = await service.complete_oauth_sign_in(
                identity_without_invite
            )

        assert error is None
        assert auth_response is not None
        invite_mock.assert_not_awaited()
