"""Tests for email verification token lifecycle."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.notifications.email_verification_service import EmailVerificationService

USER_ID = uuid4()


def _configure_select_chain(table_mock, *, rows):
    """Configure the select -> eq -> limit -> execute chain used by token lookups."""
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=rows
    )


@pytest.fixture
def verification_service(mock_supabase_client):
    with patch("src.notifications.email_verification_service.supabase_config") as cfg:
        cfg.service_client = mock_supabase_client
        cfg.is_configured.return_value = True
        yield EmailVerificationService()


class TestEmailVerificationService:
    """Verify token creation, Resend delivery, and Supabase confirmation."""

    @pytest.mark.asyncio
    async def test_create_and_send_verification_stores_token(
        self, verification_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        _configure_select_chain(table_mock, rows=[])
        table_mock.upsert.return_value.execute.return_value = MagicMock(data=[{}])

        with patch(
            "src.notifications.email_verification_service.notification_service.send_notification",
            new=AsyncMock(
                return_value=MagicMock(success=True, message="sent", status="sent")
            ),
        ) as send_mock, patch(
            "src.notifications.email_verification_service.platform_notification_settings_service.get_verification_sender",
            new=AsyncMock(return_value=(None, None)),
        ):
            success, error = await verification_service.create_and_send_verification(
                USER_ID, "user@example.com", "Test User"
            )

        assert success is True
        assert error is None
        table_mock.upsert.assert_called_once()
        send_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_and_send_reuses_active_token_without_upsert(
        self, verification_service, mock_supabase_client
    ):
        expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        _configure_select_chain(
            table_mock,
            rows=[
                {
                    "token": "existing-token",
                    "expires_at": expires_at.isoformat(),
                    "used_at": None,
                }
            ],
        )

        with patch(
            "src.notifications.email_verification_service.notification_service.send_notification",
            new=AsyncMock(
                return_value=MagicMock(success=True, message="sent", status="sent")
            ),
        ) as send_mock, patch(
            "src.notifications.email_verification_service.platform_notification_settings_service.get_verification_sender",
            new=AsyncMock(return_value=(None, None)),
        ):
            success, error = await verification_service.create_and_send_verification(
                USER_ID, "user@example.com", "Test User"
            )

        assert success is True
        assert error is None
        table_mock.upsert.assert_not_called()
        send_mock.assert_awaited_once()
        request = send_mock.await_args.args[0]
        assert "existing-token" in request.template_variables["verification_url"]

    @pytest.mark.asyncio
    async def test_create_and_send_with_sender_override_returns_false_on_resend_failure(
        self, verification_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        _configure_select_chain(table_mock, rows=[])
        table_mock.upsert.return_value.execute.return_value = MagicMock(data=[{}])

        with patch(
            "src.notifications.email_verification_service.notification_service.send_notification",
            new=AsyncMock(
                return_value=MagicMock(
                    success=False,
                    message="Failed to send notification: domain not verified",
                )
            ),
        ), patch(
            "src.notifications.email_verification_service.platform_notification_settings_service.get_verification_sender",
            new=AsyncMock(return_value=("onboarding@resend.dev", "Platform")),
        ):
            success, error = await verification_service.create_and_send_verification(
                USER_ID, "user@example.com", "Test User"
            )

        assert success is False
        assert error is not None
        assert "Failed to send" in error

    @pytest.mark.asyncio
    async def test_verify_token_confirms_user_and_marks_used(
        self, verification_service, mock_supabase_client, mock_supabase_auth
    ):
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token_row = {
            "user_id": str(USER_ID),
            "token": "valid-token",
            "expires_at": expires_at.isoformat(),
            "used_at": None,
        }

        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        _configure_select_chain(table_mock, rows=[token_row])
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase_client.auth = mock_supabase_auth

        success, message = await verification_service.verify_token("valid-token")

        assert success is True
        assert "verified" in message.lower()
        mock_supabase_auth.admin.update_user_by_id.assert_called_once_with(
            str(USER_ID),
            {"email_confirm": True},
        )

    @pytest.mark.asyncio
    async def test_verify_token_rejects_missing_token_row(
        self, verification_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        _configure_select_chain(table_mock, rows=[])

        success, message = await verification_service.verify_token("missing-token")

        assert success is False
        assert "outdated" in message.lower()

    @pytest.mark.asyncio
    async def test_verify_token_rejects_expired_token(
        self, verification_service, mock_supabase_client
    ):
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        token_row = {
            "user_id": str(USER_ID),
            "token": "expired-token",
            "expires_at": expires_at.isoformat(),
            "used_at": None,
        }

        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        _configure_select_chain(table_mock, rows=[token_row])

        success, message = await verification_service.verify_token("expired-token")

        assert success is False
        assert "expired" in message.lower()

    @pytest.mark.asyncio
    async def test_resend_verification_for_unverified_user(
        self, verification_service, mock_supabase_client
    ):
        user = MagicMock()
        user.id = str(USER_ID)
        user.email_confirmed_at = None
        user.user_metadata = {"first_name": "Test", "last_name": "User"}

        with patch(
            "src.auth.service.auth_service._find_auth_user_by_email",
            new=AsyncMock(return_value=user),
        ), patch.object(
            verification_service,
            "create_and_send_verification",
            new=AsyncMock(return_value=(True, None)),
        ) as create_mock:
            success, message = await verification_service.resend_verification(
                "user@example.com"
            )

        assert success is True
        create_mock.assert_awaited_once()
