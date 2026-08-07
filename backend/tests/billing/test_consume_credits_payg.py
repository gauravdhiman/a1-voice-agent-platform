"""Tests for PAYG-aware credit consumption in BillingService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.billing.models import CreditConsumptionRequest
from src.billing.service import BillingService


@pytest.fixture
def billing_service(mock_supabase_client):
    service = BillingService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def sample_org_id():
    return uuid4()


@pytest.mark.asyncio
async def test_consume_credits_allows_payg_within_cap(
    billing_service, mock_supabase_client, sample_org_id
):
    """When balance is low but PAYG cap allows, consumption succeeds."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )

    event_id = uuid4()
    event_response = MagicMock(
        data=[
            {
                "id": str(event_id),
                "name": "voice_call_minute",
                "credit_cost": 10,
                "is_active": True,
                "category": "voice",
                "description": "minute",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    org_response = MagicMock(data=[{"credit_balance": 5}])
    update_response = MagicMock(data=[{"credit_balance": -5}])
    tx_response = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "transaction_type": "consumed",
                "amount": -10,
                "balance_after": -5,
                "source": "event_consumption",
                "source_id": str(event_id),
                "credit_event_id": str(event_id),
                "balance_after": -5,
                "description": "test",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.execute.side_effect = [
        event_response,
        org_response,
        update_response,
        tx_response,
    ]
    mock_supabase_client.table.return_value = table_mock

    with patch(
        "src.billing.service.credit_entitlement_service.evaluate_consumption",
        new=AsyncMock(
            return_value=MagicMock(allowed=True, used_payg=True, denial_message=None)
        ),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert result.balance_after == -5


@pytest.mark.asyncio
async def test_consume_credits_denied_when_payg_not_allowed(
    billing_service, mock_supabase_client, sample_org_id
):
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )

    event_response = MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "name": "voice_call_minute",
                "credit_cost": 10,
                "is_active": True,
                "category": "voice",
                "description": "minute",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    org_response = MagicMock(data=[{"credit_balance": 5}])
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.side_effect = [event_response, org_response]
    mock_supabase_client.table.return_value = table_mock

    with patch(
        "src.billing.service.credit_entitlement_service.evaluate_consumption",
        new=AsyncMock(
            return_value=MagicMock(
                allowed=False, used_payg=False, denial_message="Insufficient credits."
            )
        ),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is False
    assert result.balance_after == 5
