"""Tests for platform notification settings singleton."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from src.notifications.platform_settings_models import (
    PLATFORM_SETTINGS_SINGLETON_ID,
    PlatformNotificationSettingsUpdate,
    extract_telegram_bot_id,
    verification_sender_configured,
)
from src.notifications.platform_settings_service import (
    PlatformNotificationSettingsService,
)

ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def settings_service(mock_supabase_client):
    with patch("src.notifications.platform_settings_service.supabase_config") as cfg:
        cfg.client = mock_supabase_client
        cfg.is_configured.return_value = True
        yield PlatformNotificationSettingsService()


def _settings_row(**overrides):
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(PLATFORM_SETTINGS_SINGLETON_ID),
        "platform_admin_email": "admin@example.com",
        "verification_from_email": "verify@example.com",
        "verification_from_name": "Platform",
        "telegram_chat_id": "-100123",
        "telegram_notifications_enabled": True,
        "telegram_bot_token_encrypted": "encrypted-value",
        "updated_by": str(ADMIN_ID),
        "created_at": now,
        "updated_at": now,
    }
    row.update(overrides)
    return row


class TestPlatformNotificationSettingsService:
    """CRUD for platform notification settings."""

    @pytest.mark.asyncio
    async def test_get_settings_masks_bot_token(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row()
        )

        settings = await settings_service.get_settings()

        assert settings.verification_from_email == "verify@example.com"
        assert settings.platform_admin_email == "admin@example.com"
        assert settings.telegram_bot_token_configured is True

    @pytest.mark.asyncio
    async def test_get_settings_returns_telegram_bot_id(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row()
        )

        with patch.object(
            settings_service,
            "_read_telegram_bot_id",
            return_value="123456",
        ):
            settings = await settings_service.get_settings()

        assert settings.telegram_bot_id == "123456"

    @pytest.mark.asyncio
    async def test_is_email_verification_required_when_sender_configured(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row(
                verification_from_email="verify@example.com",
                verification_from_name="Platform",
            )
        )

        assert await settings_service.is_email_verification_required() is True

    @pytest.mark.asyncio
    async def test_is_email_verification_required_false_when_sender_incomplete(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row(
                verification_from_email="verify@example.com",
                verification_from_name=None,
            )
        )

        assert await settings_service.is_email_verification_required() is False
        assert verification_sender_configured("verify@example.com", None) is False

    @pytest.mark.asyncio
    async def test_update_settings_clears_explicitly_null_fields(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        table_mock.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row(
                verification_from_email=None,
                verification_from_name=None,
                telegram_chat_id=None,
                telegram_bot_token_encrypted=None,
            )
        )

        payload = PlatformNotificationSettingsUpdate(
            platform_admin_email=None,
            verification_from_email=None,
            verification_from_name=None,
            telegram_chat_id=None,
            telegram_bot_token=None,
        )

        result = await settings_service.update_settings(payload, ADMIN_ID)

        update_data = table_mock.update.call_args.args[0]
        assert update_data["verification_from_email"] is None
        assert update_data["platform_admin_email"] is None
        assert update_data["verification_from_name"] is None
        assert update_data["telegram_chat_id"] is None
        assert update_data["telegram_bot_token_encrypted"] is None
        assert result.email_verification_active is False

    @pytest.mark.asyncio
    async def test_update_settings_leaves_omitted_optional_fields_unchanged(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        table_mock.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row()
        )

        payload = PlatformNotificationSettingsUpdate(
            telegram_notifications_enabled=False,
        )

        await settings_service.update_settings(payload, ADMIN_ID)

        update_data = table_mock.update.call_args.args[0]
        assert "verification_from_email" not in update_data
        assert "platform_admin_email" not in update_data
        assert "verification_from_name" not in update_data
        assert "telegram_chat_id" not in update_data
        assert "telegram_bot_token_encrypted" not in update_data
        assert update_data["telegram_notifications_enabled"] is False

    @pytest.mark.asyncio
    async def test_update_settings_saves_e164_platform_sms_opt_in(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        table_mock.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row(
                platform_admin_sms_phone="+15551234567",
                platform_admin_sms_notifications_enabled=True,
            )
        )

        payload = PlatformNotificationSettingsUpdate(
            platform_admin_sms_phone="+15551234567",
            platform_admin_sms_notifications_enabled=True,
        )
        result = await settings_service.update_settings(payload, ADMIN_ID)

        update_data = table_mock.update.call_args.args[0]
        assert update_data["platform_admin_sms_phone"] == "+15551234567"
        assert update_data["platform_admin_sms_notifications_enabled"] is True
        assert result.platform_admin_sms_phone == "+15551234567"
        assert result.platform_admin_sms_notifications_enabled is True

    def test_sms_destination_must_be_e164(self):
        with pytest.raises(ValueError):
            PlatformNotificationSettingsUpdate(platform_admin_sms_phone="5551234567")


class TestExtractTelegramBotId:
    def test_extracts_numeric_prefix(self) -> None:
        assert extract_telegram_bot_id("8895264981:AAEx-token") == "8895264981"

    def test_invalid_token_returns_none(self) -> None:
        assert extract_telegram_bot_id("not-a-token") is None

    @pytest.mark.asyncio
    async def test_update_settings_encrypts_bot_token(
        self, settings_service, mock_supabase_client
    ):
        table_mock = MagicMock()
        mock_supabase_client.table.return_value = table_mock
        table_mock.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )
        settings_query = table_mock.select.return_value.eq.return_value.single
        settings_query.return_value.execute.return_value = MagicMock(
            data=_settings_row(telegram_bot_token_encrypted="new-encrypted")
        )

        payload = PlatformNotificationSettingsUpdate(
            verification_from_email="noreply@example.com",
            telegram_bot_token="123456:ABC",
            telegram_notifications_enabled=True,
        )

        with patch(
            "src.notifications.platform_settings_service.encrypt_data",
            return_value="new-encrypted",
        ) as encrypt_mock:
            result = await settings_service.update_settings(payload, ADMIN_ID)

        encrypt_mock.assert_called_once_with(
            {"token": "123456:ABC", "bot_id": "123456"}
        )
        assert result.verification_from_email == "verify@example.com"
