"""Tests for durable low-credit notification outbox processing."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.billing.service import BillingService
from src.organization.member_models import MemberRole, OrganizationMember


@pytest.fixture
def billing_service(mock_supabase_client):
    """Return a billing service backed by the shared Supabase test double."""
    service = BillingService()
    service.supabase = mock_supabase_client
    return service


@pytest.mark.asyncio
async def test_enqueue_low_credit_notification_is_idempotent(
    billing_service, mock_supabase_client
):
    """Each successful debit creates at most one durable outbox row."""
    organization_id = uuid4()
    transaction_id = uuid4()
    table = mock_supabase_client.table.return_value
    table.upsert.return_value.execute.return_value = MagicMock(
        data=[{"id": str(uuid4())}]
    )

    result = await billing_service.enqueue_low_credit_notification(
        organization_id, transaction_id, -10
    )

    assert result is True
    payload = table.upsert.call_args.args[0]
    assert payload["organization_id"] == str(organization_id)
    assert payload["credit_transaction_id"] == str(transaction_id)
    assert payload["balance_after"] == -10
    assert table.upsert.call_args.kwargs["on_conflict"] == "credit_transaction_id"


@pytest.mark.asyncio
async def test_enqueue_low_credit_notification_failure_is_best_effort(
    billing_service, mock_supabase_client
):
    """An outbox outage is observable but does not turn a debit into a failure."""
    mock_supabase_client.table.side_effect = RuntimeError("schema unavailable")

    result = await billing_service.enqueue_low_credit_notification(uuid4(), uuid4(), 0)

    assert result is False


@pytest.mark.asyncio
async def test_process_low_credit_notification_outbox_marks_successful_row(
    billing_service, mock_supabase_client
):
    """A successfully delivered warning is marked processed for crash recovery."""
    organization_id = uuid4()
    table = mock_supabase_client.table.return_value
    table.select.return_value = table
    table.is_.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "organization_id": str(organization_id),
                "balance_after": 20,
                "attempt_count": 0,
            }
        ]
    )
    billing_service._maybe_notify_low_balance = AsyncMock(return_value=True)

    summary = await billing_service.process_low_credit_notification_outbox()

    assert summary == {"processed": 1, "succeeded": 1, "failed": 0, "skipped": 0}
    update_payload = table.update.call_args.args[0]
    assert update_payload["processed_at"]
    assert update_payload["last_error"] is None


@pytest.mark.asyncio
async def test_process_low_credit_notification_outbox_retries_failed_row(
    billing_service, mock_supabase_client
):
    """Provider failure leaves the row pending and records retry diagnostics."""
    table = mock_supabase_client.table.return_value
    table.select.return_value = table
    table.is_.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "organization_id": str(uuid4()),
                "balance_after": 5,
                "attempt_count": 2,
            }
        ]
    )
    billing_service._maybe_notify_low_balance = AsyncMock(return_value=False)

    summary = await billing_service.process_low_credit_notification_outbox()

    assert summary == {"processed": 1, "succeeded": 0, "failed": 1, "skipped": 0}
    update_payload = table.update.call_args.args[0]
    assert "processed_at" not in update_payload
    assert update_payload["attempt_count"] == 3
    assert update_payload["last_attempt_at"]
    assert update_payload["last_error"] == "notification delivery incomplete"


def _admin_member() -> OrganizationMember:
    """Build an organization owner recipient for low-balance evaluator tests."""
    return OrganizationMember(
        id=uuid4(),
        email="owner@example.com",
        first_name="Ada",
        last_name="Owner",
        is_verified=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        roles=[MemberRole(id=uuid4(), name="org_admin", description="Owner")],
    )


@pytest.mark.asyncio
async def test_low_balance_evaluator_delivers_to_org_admin_and_advances_marker(
    billing_service, mock_supabase_client
):
    """A threshold crossing sends the built-in warning and advances the marker."""
    table = mock_supabase_client.table.return_value
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.update.return_value = table
    table.execute.return_value = MagicMock(
        data=[{"name": "Acme", "low_credit_threshold_notified": None}]
    )
    owner = _admin_member()

    with (
        patch(
            "src.billing.service.credit_entitlement_service.get_included_credits_per_billing_period",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "src.rbac.user_roles.service.user_role_service.get_users_by_organization",
            new=AsyncMock(return_value=([owner], None)),
        ),
        patch(
            "src.notifications.service.notification_service.send_notification",
            new=AsyncMock(return_value=MagicMock(success=True)),
        ) as send_notification,
    ):
        result = await billing_service._maybe_notify_low_balance(uuid4(), 20)

    assert result is True
    send_notification.assert_awaited_once()
    assert table.update.call_args.args[0]["low_credit_threshold_notified"] == 20


@pytest.mark.asyncio
async def test_low_balance_evaluator_retries_when_provider_rejects_delivery(
    billing_service, mock_supabase_client
):
    """A provider rejection leaves the threshold marker unchanged for retry."""
    table = mock_supabase_client.table.return_value
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value = MagicMock(
        data=[{"name": "Acme", "low_credit_threshold_notified": None}]
    )
    owner = _admin_member()

    with (
        patch(
            "src.billing.service.credit_entitlement_service.get_included_credits_per_billing_period",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "src.rbac.user_roles.service.user_role_service.get_users_by_organization",
            new=AsyncMock(return_value=([owner], None)),
        ),
        patch(
            "src.notifications.service.notification_service.send_notification",
            new=AsyncMock(return_value=MagicMock(success=False)),
        ),
    ):
        result = await billing_service._maybe_notify_low_balance(uuid4(), 20)

    assert result is False
    table.update.assert_not_called()


@pytest.mark.asyncio
async def test_low_balance_evaluator_skips_already_sent_threshold(
    billing_service, mock_supabase_client
):
    """A threshold already sent in the cycle does not send another email."""
    table = mock_supabase_client.table.return_value
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value = MagicMock(
        data=[{"name": "Acme", "low_credit_threshold_notified": 20}]
    )

    with (
        patch(
            "src.billing.service.credit_entitlement_service.get_included_credits_per_billing_period",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "src.notifications.service.notification_service.send_notification",
            new=AsyncMock(),
        ) as send_notification,
    ):
        result = await billing_service._maybe_notify_low_balance(uuid4(), 20)

    assert result is True
    send_notification.assert_not_awaited()
