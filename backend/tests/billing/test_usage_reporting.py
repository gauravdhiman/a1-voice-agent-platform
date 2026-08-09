"""Tests for organization credit usage reporting and voice call metering."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.billing.models import CreditUsageResponse
from src.billing.service import BillingService

from shared.billing.voice_call_metering import calculate_voice_call_credits


def _transaction_row(org_id: str, *, amount: int = -20) -> dict:
    """Build a Supabase row with an embedded credit event."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid4()),
        "organization_id": org_id,
        "transaction_type": "consumed",
        "amount": amount,
        "balance_after": 80,
        "source": "event_consumption",
        "source_id": str(uuid4()),
        "credit_event_id": str(uuid4()),
        "description": "Consumed 2x voice_call_minute",
        "metadata": {"call_log_id": str(uuid4())},
        "created_at": now,
        "credit_events": {
            "id": str(uuid4()),
            "name": "voice_call_minute",
            "description": "Voice call minute",
            "credit_cost": 10,
            "category": "voice",
            "is_active": True,
            "metadata": None,
            "created_at": now,
            "updated_at": now,
        },
    }


def test_voice_call_credits_rounds_up_to_billable_minutes() -> None:
    """A call lasting one second is billed as one minute."""
    assert calculate_voice_call_credits(1, 10) == 10
    assert calculate_voice_call_credits(60, 10) == 10
    assert calculate_voice_call_credits(61, 10) == 20


def test_credit_usage_response_exposes_balance_and_period_usage() -> None:
    """The reporting response has the fields the dashboard needs."""
    response = CreditUsageResponse(
        organization_id=uuid4(),
        balance={
            "total_credits": 100,
            "subscription_credits": 75,
            "purchased_credits": 25,
            "expiring_soon": 0,
            "expires_at": None,
        },
        period_start=None,
        period_end=None,
        period_credits_granted=100,
        period_credits_used=20,
        period_credits_remaining=80,
        usage_by_category=[],
        transactions=[],
    )
    assert response.period_credits_remaining == 80


@pytest.mark.asyncio
async def test_get_credit_transactions_includes_event_details(mock_supabase_client):
    """Ledger queries return event metadata needed to explain consumption."""
    service = BillingService()
    service.supabase = mock_supabase_client
    org_id = uuid4()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = MagicMock(
        data=[_transaction_row(str(org_id))], count=1
    )
    mock_supabase_client.table.return_value = query

    result = await service.get_credit_transactions(org_id, page=1, page_size=25)

    assert result.total == 1
    assert result.items[0].credit_event is not None
    assert result.items[0].credit_event.name == "voice_call_minute"
