"""Tests for idempotent notification delivery and retry behavior."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.leads.models import InterestLead
from src.notifications.email_providers import EmailSendResult
from src.notifications.lead_notifier import build_interest_lead_template_variables
from src.notifications.models import NotificationEvent, SendNotificationRequest
from src.notifications.service import NotificationService


class FakeEmailProvider:
    """Small provider double implementing the production adapter contract."""

    name = "resend"

    def __init__(self) -> None:
        self.sent = []

    async def send(self, message):
        self.sent.append(message)
        return EmailSendResult(provider=self.name, provider_message_id="msg-1")


def _low_balance_event() -> NotificationEvent:
    now = datetime.now(timezone.utc)
    return NotificationEvent(
        id=uuid4(),
        name="Low Credit Balance",
        description="Low balance",
        event_key="credits.low_balance",
        category="billing",
        is_enabled=True,
        default_template_id=None,
        metadata=None,
        created_at=now,
        updated_at=now,
    )


def _interest_lead_event() -> NotificationEvent:
    now = datetime.now(timezone.utc)
    return NotificationEvent(
        id=uuid4(),
        name="Interest Lead Submitted",
        description="A public visitor submitted an interest request",
        event_key="lead.interest_submitted",
        category="system",
        is_enabled=True,
        default_template_id=None,
        metadata=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_sent_idempotency_key_skips_provider_duplicate(mock_supabase_client):
    """A successful delivery is returned without calling the provider again."""
    provider = FakeEmailProvider()
    with patch("src.notifications.service.supabase_config") as config, patch(
        "src.notifications.service.settings"
    ) as settings:
        config.client = mock_supabase_client
        settings.resend_from_email = "noreply@example.com"
        settings.resend_from_name = "24x7 AI"
        service = NotificationService(email_provider=provider)

    service.get_notification_event_by_key = AsyncMock(return_value=_low_balance_event())
    service._find_notification_log_by_idempotency_key = AsyncMock(
        return_value={
            "id": str(uuid4()),
            "status": "sent",
            "attempt_count": 1,
        }
    )

    response = await service.send_notification(
        SendNotificationRequest(
            event_key="credits.low_balance",
            recipient_email="owner@example.com",
            template_variables={
                "user_name": "Owner",
                "current_credits": "20",
                "threshold_percent": "20",
                "organization_name": "Acme",
                "purchase_credits_url": "https://247ai.live/billing",
            },
            idempotency_key="low-credit:org:20:user",
        )
    )

    assert response.success is True
    assert provider.sent == []


@pytest.mark.asyncio
async def test_failed_idempotency_key_retries_and_marks_delivery_sent(
    mock_supabase_client,
):
    """A failed log can be retried without creating another delivery record."""
    provider = FakeEmailProvider()
    with patch("src.notifications.service.supabase_config") as config, patch(
        "src.notifications.service.settings"
    ) as settings:
        config.client = mock_supabase_client
        settings.resend_from_email = "noreply@example.com"
        settings.resend_from_name = "24x7 AI"
        service = NotificationService(email_provider=provider)

    service.get_notification_event_by_key = AsyncMock(return_value=_low_balance_event())
    service._find_notification_log_by_idempotency_key = AsyncMock(
        return_value={
            "id": str(uuid4()),
            "status": "failed",
            "attempt_count": 1,
        }
    )
    table = mock_supabase_client.table.return_value
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )

    response = await service.send_notification(
        SendNotificationRequest(
            event_key="credits.low_balance",
            recipient_email="owner@example.com",
            template_variables={
                "user_name": "Owner",
                "current_credits": "20",
                "threshold_percent": "20",
                "organization_name": "Acme",
                "purchase_credits_url": "https://247ai.live/billing",
            },
            idempotency_key="low-credit:org:20:user",
        )
    )

    assert response.success is True
    assert len(provider.sent) == 1
    assert provider.sent[0].idempotency_key == "low-credit:org:20:user"
    assert table.update.call_args_list[-1].args[0]["status"] == "sent"


@pytest.mark.asyncio
async def test_interest_lead_email_escapes_submission_once_before_rendering(
    mock_supabase_client,
):
    provider = FakeEmailProvider()
    with patch("src.notifications.service.supabase_config") as config, patch(
        "src.notifications.service.settings"
    ) as settings:
        config.client = mock_supabase_client
        settings.resend_from_email = "noreply@example.com"
        settings.resend_from_name = "24x7 AI"
        service = NotificationService(email_provider=provider)

    service.get_notification_event_by_key = AsyncMock(
        return_value=_interest_lead_event()
    )
    service._find_notification_log_by_idempotency_key = AsyncMock(
        return_value={"id": str(uuid4()), "status": "failed", "attempt_count": 1}
    )
    table = mock_supabase_client.table.return_value
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{}]
    )
    lead = InterestLead(
        id=uuid4(),
        name="Sam Owner",
        business_name="Bright Smiles Dental",
        email="sam@example.com",
        phone="+14805550100",
        vertical="dental",
        message='<img src=x onerror="alert(1)">',
        source="contact-form",
        status="new",
        created_at=datetime.now(timezone.utc),
    )

    response = await service.send_notification(
        SendNotificationRequest(
            event_key="lead.interest_submitted",
            recipient_email="admin@example.com",
            template_variables=build_interest_lead_template_variables(lead),
            idempotency_key=f"interest-lead:{lead.id}:email",
        )
    )

    assert response.success is True
    rendered = provider.sent[0].html_content
    assert '<img src=x onerror="alert(1)">' not in rendered
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in rendered
    assert "&amp;lt;img" not in rendered


@pytest.mark.asyncio
async def test_retry_failed_notifications_reuses_the_original_log_key(
    mock_supabase_client,
):
    """The retry pass asks the service to resend a logged failed delivery."""
    with patch("src.notifications.service.supabase_config") as config, patch(
        "src.notifications.service.settings"
    ) as settings:
        config.client = mock_supabase_client
        settings.resend_from_email = "noreply@example.com"
        settings.resend_from_name = "24x7 AI"
        service = NotificationService(email_provider=FakeEmailProvider())

    log_id = uuid4()
    table = mock_supabase_client.table.return_value
    table.select.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": str(log_id),
                "status": "failed",
                "last_attempt_at": None,
                "notification_event_id": str(uuid4()),
                "notification_template_id": None,
                "organization_id": str(uuid4()),
                "user_id": str(uuid4()),
                "recipient_email": "owner@example.com",
                "recipient_name": "Owner",
                "metadata": {"user_name": "Owner"},
                "idempotency_key": "low-credit:org:20:user",
                "notification_events": {"event_key": "credits.low_balance"},
            }
        ]
    )
    service.send_notification = AsyncMock(return_value=MagicMock(success=True))

    result = await service.retry_failed_notifications()

    assert result.succeeded == 1
    retry_request = service.send_notification.call_args.args[0]
    assert retry_request.idempotency_key == "low-credit:org:20:user"


@pytest.mark.asyncio
async def test_retry_interest_notification_rehydrates_lead_without_pii_metadata(
    mock_supabase_client,
):
    """Lead retries use the private lead row rather than stored contact fields."""
    with patch("src.notifications.service.supabase_config") as config, patch(
        "src.notifications.service.settings"
    ) as settings:
        config.client = mock_supabase_client
        settings.resend_from_email = "noreply@example.com"
        settings.resend_from_name = "24x7 AI"
        service = NotificationService(email_provider=FakeEmailProvider())

    log_id = uuid4()
    lead_id = uuid4()
    table = mock_supabase_client.table.return_value
    table.select.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": str(log_id),
                "status": "failed",
                "last_attempt_at": None,
                "notification_event_id": str(uuid4()),
                "notification_template_id": None,
                "organization_id": None,
                "user_id": None,
                "recipient_email": "admin@example.com",
                "recipient_name": "Platform admin",
                "metadata": {
                    "kind": "interest_lead",
                    "lead_id": str(lead_id),
                    "source": "request-demo",
                    "from_email": "alerts@example.com",
                    "from_name": "24x7 AI",
                },
                "idempotency_key": f"interest-lead:{lead_id}:email",
                "notification_events": {"event_key": "lead.interest_submitted"},
            }
        ]
    )
    service.send_notification = AsyncMock(return_value=MagicMock(success=True))
    lead = InterestLead(
        id=lead_id,
        name="Sam Owner",
        business_name="Bright Smiles Dental",
        email="sam@example.com",
        source="request-demo",
        status="new",
        created_at=datetime.now(timezone.utc),
    )
    with patch(
        "src.leads.service.lead_service.get_lead",
        new=AsyncMock(return_value=(lead, None)),
    ):
        result = await service.retry_failed_notifications()

    assert result.succeeded == 1
    request = service.send_notification.call_args.args[0]
    assert request.template_variables["lead_name"] == "Sam Owner"
    assert request.log_metadata["lead_id"] == str(lead_id)
