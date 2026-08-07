"""Tests for signup Telegram notifier."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.notifications.signup_notifier import SignupNotifier

USER_ID = uuid4()


class TestSignupNotifier:
    """Platform admin Telegram alerts on signup events."""

    @pytest.mark.asyncio
    async def test_notify_new_user_sends_when_enabled(self):
        notifier = SignupNotifier()

        with patch(
            "src.notifications.signup_notifier.platform_notification_settings_service.get_telegram_credentials",
            new=AsyncMock(return_value=("bot-token", "chat-123", True)),
        ), patch(
            "src.notifications.signup_notifier.telegram_service.send_message",
            new=AsyncMock(return_value=True),
        ) as send_mock:
            await notifier.notify_new_user(
                email="user@example.com",
                user_id=USER_ID,
                method="email",
                first_name="New",
                last_name="User",
            )

        send_mock.assert_awaited_once()
        message = send_mock.await_args.args[2]
        assert "user@example.com" in message
        assert "email" in message

    @pytest.mark.asyncio
    async def test_notify_new_user_skips_when_disabled(self):
        notifier = SignupNotifier()

        with patch(
            "src.notifications.signup_notifier.platform_notification_settings_service.get_telegram_credentials",
            new=AsyncMock(return_value=(None, None, False)),
        ), patch(
            "src.notifications.signup_notifier.telegram_service.send_message",
            new=AsyncMock(return_value=True),
        ) as send_mock:
            await notifier.notify_new_user(
                email="user@example.com",
                user_id=USER_ID,
                method="google",
            )

        send_mock.assert_not_awaited()
