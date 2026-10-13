"""Tests for the terms gate and acceptance capture in OAuth sign-in.

``complete_oauth_sign_in`` MUST refuse to create brand-new accounts that have
not accepted the legal documents, while never blocking existing users from
signing in. For new users created with acceptance, the published versions are
recorded with ``source="oauth"``, and that capture can never fail a completed
sign-in.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from src.auth.oauth_identity import OAuthVerifiedIdentity
from src.auth.oauth_session import OAuthSessionService

try:
    from supabase_auth.errors import AuthApiError
except ImportError:  # pragma: no cover
    from gotrue.errors import AuthApiError

USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TERMS_REJECTION_DETAIL = (
    "You must accept the Terms & Conditions and Privacy Policy to create an account."
)


def _identity(**overrides) -> OAuthVerifiedIdentity:
    data = {
        "provider": "google",
        "email": "founder@example.com",
        "first_name": "Found",
        "last_name": "Er",
        "provider_sub": "google-sub-founder",
    }
    data.update(overrides)
    return OAuthVerifiedIdentity(**data)


def _mock_supabase() -> MagicMock:
    client = MagicMock()
    session = MagicMock()
    session.access_token = "supabase-access-token"
    session.refresh_token = "supabase-refresh-token"
    session.expires_in = 3600

    user = MagicMock()
    user.id = str(USER_ID)
    user.email = "founder@example.com"
    user.user_metadata = {"first_name": "Found", "last_name": "Er"}
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


class TestTermsGate:
    @pytest.mark.asyncio
    async def test_new_user_without_acceptance_is_rejected_before_account_creation(
        self,
    ):
        client = _mock_supabase()
        factory = MagicMock(return_value=client)
        service = OAuthSessionService(auth_client_factory=factory)

        with patch(
            "src.auth.service.auth_service.auth_user_exists",
            new=AsyncMock(return_value=False),
        ) as user_exists, patch(
            "src.legal.service.legal_service.record_user_acceptance",
            new=AsyncMock(),
        ) as record:
            auth_response, error = await service.complete_oauth_sign_in(
                _identity(terms_accepted=False)
            )

        assert auth_response is None
        assert isinstance(error, HTTPException)
        assert error.status_code == 403
        assert error.detail == TERMS_REJECTION_DETAIL
        factory.assert_not_called()
        user_exists.assert_awaited_once_with("founder@example.com")
        record.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_existing_user_without_acceptance_still_signs_in(self):
        """Existing accounts predate the legal feature and must never be blocked."""
        client = _mock_supabase()
        client.auth.admin.create_user.side_effect = AuthApiError(
            "User already registered", 422, "user_already_exists"
        )
        service = OAuthSessionService(auth_client_factory=lambda: client)

        with patch(
            "src.auth.service.auth_service.auth_user_exists",
            new=AsyncMock(return_value=True),
        ), patch(
            "src.legal.service.legal_service.record_user_acceptance",
            new=AsyncMock(),
        ) as record, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ), patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ):
            auth_response, error = await service.complete_oauth_sign_in(
                _identity(terms_accepted=False)
            )

        assert error is None
        assert auth_response is not None
        assert auth_response.user.id == USER_ID
        record.assert_not_awaited()


class TestOAuthAcceptanceCapture:
    @pytest.mark.asyncio
    async def test_new_user_acceptance_records_source_oauth(self):
        client = _mock_supabase()
        service = OAuthSessionService(auth_client_factory=lambda: client)

        with patch("src.legal.service.legal_service") as mock_legal, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ), patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ):
            mock_legal.record_user_acceptance = AsyncMock(return_value=2)
            auth_response, error = await service.complete_oauth_sign_in(
                _identity(terms_accepted=True)
            )

        assert error is None
        assert auth_response is not None
        mock_legal.record_user_acceptance.assert_awaited_once_with(
            USER_ID, source="oauth"
        )

    @pytest.mark.asyncio
    async def test_acceptance_failure_never_fails_completed_sign_in(self):
        client = _mock_supabase()
        service = OAuthSessionService(auth_client_factory=lambda: client)

        with patch("src.legal.service.legal_service") as mock_legal, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ), patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ):
            mock_legal.record_user_acceptance = AsyncMock(
                side_effect=RuntimeError("acceptance store down")
            )
            auth_response, error = await service.complete_oauth_sign_in(
                _identity(terms_accepted=True)
            )

        assert error is None
        assert auth_response is not None
        mock_legal.record_user_acceptance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_existing_user_signup_records_no_acceptance(self):
        """Acceptance rows are captured at account creation, not on every sign-in."""
        client = _mock_supabase()
        client.auth.admin.create_user.side_effect = AuthApiError(
            "User already registered", 422, "user_already_exists"
        )
        service = OAuthSessionService(auth_client_factory=lambda: client)

        with patch("src.legal.service.legal_service") as mock_legal, patch(
            "src.notifications.signup_notifier.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ), patch(
            "src.auth.oauth_session.ensure_default_organization_for_user",
            new=AsyncMock(return_value=(None, None)),
        ):
            mock_legal.record_user_acceptance = AsyncMock()
            auth_response, error = await service.complete_oauth_sign_in(
                _identity(terms_accepted=True)
            )

        assert error is None
        assert auth_response is not None
        mock_legal.record_user_acceptance.assert_not_awaited()
