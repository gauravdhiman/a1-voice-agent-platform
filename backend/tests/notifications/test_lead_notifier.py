"""Tests for platform-admin interest lead email and Telegram alerts."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from src.leads.models import InterestLead
from src.notifications.lead_notifier import (
    InterestLeadNotifier,
    build_interest_lead_template_variables,
)
from src.notifications.models import NotificationStatus, SendNotificationResponse
from src.notifications.platform_settings_models import PlatformNotificationSettings

LEAD_ID = uuid4()


def _lead() -> InterestLead:
    return InterestLead(
        id=LEAD_ID,
        name="Sam Owner",
        business_name="Bright Smiles Dental",
        email="sam@example.com",
        phone="+14805550100",
        vertical="dental",
        message="Miss after-hours calls",
        source="outcome-form",
        demo_slug="dental-demo",
        status="new",
        created_at=datetime(2026, 9, 10, 12, 30, tzinfo=timezone.utc),
    )


def _settings(
    *,
    admin_email="admin@example.com",
    telegram_enabled=False,
    whatsapp_enabled=False,
) -> PlatformNotificationSettings:
    now = datetime.now(timezone.utc)
    return PlatformNotificationSettings(
        id=uuid4(),
        platform_admin_email=admin_email,
        verification_from_email="alerts@example.com",
        verification_from_name="24x7 AI",
        email_verification_active=True,
        telegram_chat_id="-100123" if telegram_enabled else None,
        telegram_notifications_enabled=telegram_enabled,
        telegram_bot_token_configured=telegram_enabled,
        telegram_bot_id="123" if telegram_enabled else None,
        platform_admin_whatsapp_phone="+15551234567" if whatsapp_enabled else None,
        platform_admin_whatsapp_notifications_enabled=whatsapp_enabled,
        created_at=now,
        updated_at=now,
    )


def _email_response() -> SendNotificationResponse:
    return SendNotificationResponse(
        success=True,
        notification_log_id=uuid4(),
        status=NotificationStatus.SENT,
        message="Notification sent successfully",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("admin_email", "telegram_enabled", "expect_email", "expect_telegram"),
    [
        ("admin@example.com", False, True, False),
        (None, True, False, True),
        ("admin@example.com", True, True, True),
        (None, False, False, False),
    ],
)
async def test_notify_interest_lead_selects_configured_channels(
    admin_email, telegram_enabled, expect_email, expect_telegram
):
    notifier = InterestLeadNotifier()
    with patch("src.notifications.lead_notifier.settings") as app_settings, patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(
            return_value=_settings(
                admin_email=admin_email, telegram_enabled=telegram_enabled
            )
        ),
    ), patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_telegram_credentials",
        new=AsyncMock(return_value=("bot-token", "-100123", True)),
    ), patch(
        "src.notifications.lead_notifier.notification_service.send_notification",
        new=AsyncMock(return_value=_email_response()),
    ) as email_mock, patch(
        "src.notifications.lead_notifier.telegram_service.send_message",
        new=AsyncMock(return_value=True),
    ) as telegram_mock:
        app_settings.resend_api_key = "re_test"
        app_settings.resend_from_email = "noreply@example.com"
        app_settings.resend_from_name = "24x7 AI"
        app_settings.app_base_url = "https://247ai.live"
        app_settings.app_name = "24x7 AI"

        await notifier.notify_interest_lead(_lead())

    assert email_mock.await_count == int(expect_email)
    assert telegram_mock.await_count == int(expect_telegram)
    if expect_telegram:
        message = telegram_mock.await_args.args[2]
        assert "Bright Smiles Dental" in message
        assert "https://247ai.live/platform/interest" in message


@pytest.mark.asyncio
async def test_email_alert_uses_recipient_and_retry_safe_metadata():
    notifier = InterestLeadNotifier()
    with patch("src.notifications.lead_notifier.settings") as app_settings, patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(return_value=_settings()),
    ), patch(
        "src.notifications.lead_notifier.notification_service.send_notification",
        new=AsyncMock(return_value=_email_response()),
    ) as email_mock:
        app_settings.resend_api_key = "re_test"
        app_settings.resend_from_email = "noreply@example.com"
        app_settings.resend_from_name = "24x7 AI"
        app_settings.app_base_url = "https://247ai.live"
        app_settings.app_name = "24x7 AI"

        await notifier.notify_interest_lead(_lead())

    request = email_mock.await_args.args[0]
    assert request.recipient_email == "admin@example.com"
    assert request.event_key == "lead.interest_submitted"
    assert request.idempotency_key == f"interest-lead:{LEAD_ID}:email"
    assert request.log_metadata == {
        "kind": "interest_lead",
        "lead_id": str(LEAD_ID),
        "source": "outcome-form",
        "from_email": "alerts@example.com",
        "from_name": "24x7 AI",
    }
    assert "sam@example.com" not in request.log_metadata.values()


@pytest.mark.asyncio
async def test_incomplete_telegram_configuration_skips_provider_call():
    notifier = InterestLeadNotifier()
    with patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(return_value=_settings(admin_email=None, telegram_enabled=True)),
    ), patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_telegram_credentials",
        new=AsyncMock(return_value=(None, "-100123", True)),
    ), patch(
        "src.notifications.lead_notifier.telegram_service.send_message",
        new=AsyncMock(return_value=True),
    ) as telegram_mock:
        await notifier.notify_interest_lead(_lead())

    telegram_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_notify_interest_lead_swallows_channel_failures():
    notifier = InterestLeadNotifier()
    with patch("src.notifications.lead_notifier.settings") as app_settings, patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(return_value=_settings(telegram_enabled=True)),
    ), patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_telegram_credentials",
        new=AsyncMock(return_value=("bot-token", "-100123", True)),
    ), patch(
        "src.notifications.lead_notifier.notification_service.send_notification",
        new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
    ), patch(
        "src.notifications.lead_notifier.telegram_service.send_message",
        new=AsyncMock(side_effect=RuntimeError("telegram unavailable")),
    ):
        app_settings.resend_api_key = "re_test"
        app_settings.resend_from_email = "noreply@example.com"
        app_settings.resend_from_name = "24x7 AI"
        app_settings.app_base_url = "https://247ai.live"
        app_settings.app_name = "24x7 AI"
        await notifier.notify_interest_lead(_lead())


@pytest.mark.asyncio
async def test_whatsapp_alert_receives_all_submitted_lead_fields():
    notifier = InterestLeadNotifier()
    with patch("src.notifications.lead_notifier.settings") as app_settings, patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(return_value=_settings(admin_email=None, whatsapp_enabled=True)),
    ), patch(
        "src.notifications.lead_notifier.whatsapp_service.is_configured",
        return_value=True,
    ), patch(
        "src.notifications.lead_notifier.whatsapp_service.send_template_message",
        new=AsyncMock(return_value=True),
    ) as whatsapp_mock:
        app_settings.app_base_url = "https://247ai.live"
        app_settings.app_name = "24x7 AI"
        await notifier.notify_interest_lead(_lead())

    recipient, variables = whatsapp_mock.await_args.args
    assert recipient == "+15551234567"
    assert variables == {
        "1": "Sam Owner",
        "2": "Bright Smiles Dental",
        "3": "sam@example.com",
        "4": "+14805550100",
        "5": "dental",
        "6": "Miss after-hours calls",
        "7": "outcome-form",
        "8": "dental-demo",
        "9": "2026-09-10 12:30 UTC",
        "10": "https://247ai.live/platform/interest",
    }


def test_interest_template_variables_are_allowlisted_and_formatted():
    with patch("src.notifications.lead_notifier.settings") as app_settings:
        app_settings.app_base_url = "https://247ai.live/"
        app_settings.app_name = "24x7 AI"
        variables = build_interest_lead_template_variables(_lead())

    assert variables["lead_email"] == "sam@example.com"
    assert variables["submitted_at"] == "2026-09-10 12:30 UTC"
    assert variables["interests_url"] == "https://247ai.live/platform/interest"
    assert "captcha" not in variables


def test_interest_template_variables_use_placeholders_for_missing_values():
    lead = _lead().model_copy(update={"phone": None, "message": "   "})
    with patch("src.notifications.lead_notifier.settings") as app_settings:
        app_settings.app_base_url = "https://247ai.live"
        app_settings.app_name = "24x7 AI"
        variables = build_interest_lead_template_variables(lead)

    assert variables["lead_phone"] == "—"
    assert variables["message"] == "—"


@pytest.mark.asyncio
async def test_settings_lookup_failure_is_swallowed():
    notifier = InterestLeadNotifier()
    with patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(side_effect=RuntimeError("settings unavailable")),
    ):
        await notifier.notify_interest_lead(_lead())


@pytest.mark.asyncio
async def test_email_provider_rejection_is_swallowed():
    notifier = InterestLeadNotifier()
    with patch("src.notifications.lead_notifier.settings") as app_settings, patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(return_value=_settings()),
    ), patch(
        "src.notifications.lead_notifier.notification_service.send_notification",
        new=AsyncMock(
            return_value=SendNotificationResponse(
                success=False,
                notification_log_id=uuid4(),
                status=NotificationStatus.FAILED,
                message="provider rejected",
            )
        ),
    ):
        app_settings.resend_api_key = "re_test"
        app_settings.resend_from_email = "noreply@example.com"
        app_settings.resend_from_name = "24x7 AI"
        app_settings.app_base_url = "https://247ai.live"
        app_settings.app_name = "24x7 AI"
        await notifier.notify_interest_lead(_lead())


@pytest.mark.asyncio
async def test_telegram_provider_rejection_is_swallowed():
    notifier = InterestLeadNotifier()
    with patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_settings",
        new=AsyncMock(return_value=_settings(admin_email=None, telegram_enabled=True)),
    ), patch(
        "src.notifications.lead_notifier.platform_notification_settings_service.get_telegram_credentials",
        new=AsyncMock(return_value=("bot-token", "-100123", True)),
    ), patch(
        "src.notifications.lead_notifier.telegram_service.send_message",
        new=AsyncMock(return_value=False),
    ):
        await notifier.notify_interest_lead(_lead())
