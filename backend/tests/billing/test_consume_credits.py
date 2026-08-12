"""Tests for two-pool credit consumption in BillingService.

Covers plan-first consumption (plan pool drained before purchased pool),
denial when the combined balance is insufficient, the static allocation
helper, atomic debit RPC integration, and the low-balance notification hook.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from src.billing.credit_entitlement_service import credit_entitlement_service
from src.billing.models import CreditConsumptionRequest, TransactionType
from src.billing.service import BillingService
from src.notifications.service import notification_service
from src.organization.member_models import MemberRole, OrganizationMember


@pytest.fixture
def billing_service(mock_supabase_client):
    service = BillingService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def sample_org_id():
    return uuid4()


def _event_response(cost: int = 10, name: str = "voice_call_minute"):
    """Build a credit_events query response for one enabled event."""
    event_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    return MagicMock(
        data=[
            {
                "id": str(event_id),
                "name": name,
                "credit_cost": cost,
                "is_active": True,
                "category": "voice",
                "description": "minute",
                "created_at": now,
                "updated_at": now,
            }
        ]
    )


def _debit_success(
    *,
    balance_after: int,
    plan_used: int,
    purchased_used: int,
    admin_used: int = 0,
    plan_balance: int | None = None,
    admin_balance: int | None = None,
    purchased_balance: int | None = None,
):
    """Build a debit_organization_credits RPC payload for a successful debit."""
    return {
        "success": True,
        "balance_after": balance_after,
        "plan_used": plan_used,
        "admin_used": admin_used,
        "purchased_used": purchased_used,
        "plan_balance": plan_balance,
        "admin_balance": admin_balance,
        "purchased_balance": purchased_balance,
    }


def _debit_denied(balance_after: int):
    """Build a debit_organization_credits RPC payload for insufficient balance."""
    return {"success": False, "balance_after": balance_after}


def _tx_response(org_id: UUID, amount: int, balance_after: int):
    """Build a credit_transactions insert response."""
    return MagicMock(
        data=[
            {
                "id": str(uuid4()),
                "organization_id": str(org_id),
                "transaction_type": "consumed",
                "amount": amount,
                "balance_after": balance_after,
                "source": "event_consumption",
                "source_id": str(uuid4()),
                "credit_event_id": str(uuid4()),
                "description": "test",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )


def _setup_consume_mocks(mock_supabase_client, table_effects, debit_payload):
    """Configure table execute chain and debit_organization_credits RPC."""
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.contains.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.side_effect = table_effects
    mock_supabase_client.table.return_value = table_mock

    rpc_mock = MagicMock()
    rpc_mock.execute.return_value = MagicMock(data=debit_payload)
    mock_supabase_client.rpc.return_value = rpc_mock
    return table_mock, rpc_mock


@pytest.mark.asyncio
async def test_consume_credits_reuses_idempotent_debit(
    billing_service, mock_supabase_client, sample_org_id
):
    """A retried purchase debit returns the original ledger transaction."""
    transaction_id = uuid4()
    table_mock, rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [_event_response(cost=200, name="phone_number_local_month")],
        {
            "success": True,
            "already_recorded": True,
            "transaction_id": str(transaction_id),
            "balance_after": 800,
        },
    )

    result = await billing_service.consume_credits(
        CreditConsumptionRequest(
            organization_id=sample_org_id,
            event_name="phone_number_local_month",
            idempotency_key="purchase-key",
        )
    )

    assert result.success is True
    assert result.credits_consumed == 200
    assert result.balance_after == 800
    rpc_mock.execute.assert_called_once()
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_refund_credits_writes_refunded_ledger_entry(
    billing_service, mock_supabase_client, sample_org_id
):
    """A failed phone purchase is returned as a typed, auditable refund."""
    transaction = {
        "id": str(uuid4()),
        "organization_id": str(sample_org_id),
        "transaction_type": "refunded",
        "amount": 200,
        "balance_after": 900,
        "source": "admin_adjustment",
        "description": "Phone-number purchase failed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.contains.return_value = table
    table.limit.return_value = table
    table.execute.return_value = MagicMock(data=[transaction])
    table.insert.return_value.execute.return_value = MagicMock(data=[transaction])
    mock_supabase_client.table.return_value = table
    mock_supabase_client.rpc.return_value = MagicMock(
        execute=MagicMock(
            return_value=MagicMock(
                data={
                    "success": True,
                    "balance_after": 900,
                    "plan_used": 0,
                    "admin_used": 0,
                    "purchased_used": 0,
                }
            )
        )
    )

    result = await billing_service.refund_credits(
        organization_id=sample_org_id,
        credits=200,
        reason="Phone-number purchase failed",
        metadata={"phone_number": "+14155550100"},
    )

    assert result.transaction_type == TransactionType.REFUNDED
    inserted = table.insert.call_args.args[0]
    assert inserted["transaction_type"] == "refunded"
    assert inserted["amount"] == 200


@pytest.mark.asyncio
async def test_consume_credits_drains_plan_pool_first(
    billing_service, mock_supabase_client, sample_org_id
):
    """Plan credits are consumed before purchased credits."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    table_mock, rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [_event_response(), _tx_response(sample_org_id, -10, 70)],
        _debit_success(
            balance_after=70,
            plan_used=10,
            purchased_used=0,
            plan_balance=20,
            purchased_balance=50,
        ),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert result.credits_consumed == 10
    assert result.balance_after == 70

    rpc_mock.execute.assert_called_once()
    assert mock_supabase_client.rpc.call_args[0][0] == "debit_organization_credits"
    assert mock_supabase_client.rpc.call_args[0][1]["p_credits_needed"] == 10

    tx_inserted = table_mock.insert.call_args[0][0]
    assert tx_inserted["metadata"]["plan_credits"] == 10
    assert tx_inserted["metadata"]["purchased_credits"] == 0


@pytest.mark.asyncio
async def test_zero_priced_event_is_successful_without_a_debit(
    billing_service, mock_supabase_client, sample_org_id
):
    """A zero system rate makes the activity free without calling the debit RPC."""
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.side_effect = [
        _event_response(cost=0),
        MagicMock(
            data=[
                {
                    "credit_balance": 8,
                    "admin_credit_balance": 2,
                    "purchased_credit_balance": 1,
                }
            ]
        ),
    ]
    mock_supabase_client.table.return_value = table_mock
    mock_supabase_client.rpc.return_value = MagicMock()

    result = await billing_service.consume_credits(
        CreditConsumptionRequest(
            organization_id=sample_org_id,
            event_name="voice_call_minute",
            quantity=1,
        )
    )

    assert result.success is True
    assert result.credits_consumed == 0
    assert result.balance_after == 11
    mock_supabase_client.rpc.assert_not_called()
    table_mock.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_consume_credits_drains_purchased_after_plan_exhausted(
    billing_service, mock_supabase_client, sample_org_id
):
    """Purchased credits cover the shortfall once the plan pool is empty."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    table_mock, _rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [_event_response(), _tx_response(sample_org_id, -10, 45)],
        _debit_success(
            balance_after=45,
            plan_used=5,
            purchased_used=5,
            plan_balance=0,
            purchased_balance=45,
        ),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert result.balance_after == 45

    tx_inserted = table_mock.insert.call_args[0][0]
    assert tx_inserted["metadata"]["plan_credits"] == 5
    assert tx_inserted["metadata"]["purchased_credits"] == 5


@pytest.mark.asyncio
async def test_consume_credits_purchased_only_when_plan_empty(
    billing_service, mock_supabase_client, sample_org_id
):
    """Consumption works from the purchased pool when the plan pool is empty."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    table_mock, _rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [_event_response(), _tx_response(sample_org_id, -10, 40)],
        _debit_success(
            balance_after=40,
            plan_used=0,
            purchased_used=10,
            plan_balance=0,
            purchased_balance=40,
        ),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert result.balance_after == 40

    tx_inserted = table_mock.insert.call_args[0][0]
    assert tx_inserted["metadata"]["plan_credits"] == 0
    assert tx_inserted["metadata"]["purchased_credits"] == 10


@pytest.mark.asyncio
async def test_consume_credits_exact_combined_balance_allowed(
    billing_service, mock_supabase_client, sample_org_id
):
    """Consumption succeeds when the combined balance exactly covers the cost."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    _setup_consume_mocks(
        mock_supabase_client,
        [_event_response(), _tx_response(sample_org_id, -10, 0)],
        _debit_success(
            balance_after=0,
            plan_used=6,
            purchased_used=4,
            plan_balance=0,
            purchased_balance=0,
        ),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert result.balance_after == 0
    assert result.credits_consumed == 10


@pytest.mark.asyncio
async def test_consume_credits_denied_when_combined_balance_insufficient(
    billing_service, mock_supabase_client, sample_org_id
):
    """No PAYG: consumption is denied when both pools together are short."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    table_mock, _rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [_event_response()],
        _debit_denied(8),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is False
    assert result.credits_consumed == 0
    assert result.balance_after == 8
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_consume_credits_denied_when_zero_balance(
    billing_service, mock_supabase_client, sample_org_id
):
    """Zero balance denies consumption outright."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    _setup_consume_mocks(
        mock_supabase_client,
        [_event_response()],
        _debit_denied(0),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is False
    assert result.balance_after == 0


class TestAllocateConsumption:
    """Unit tests for the static plan-first allocation helper."""

    @pytest.mark.parametrize(
        "plan,purchased,needed,expected",
        [
            (30, 50, 60, (30, 30)),
            (0, 50, 60, (0, 50)),
            (100, 0, 60, (60, 0)),
            (0, 0, 10, (0, 0)),
            (25, 0, 10, (10, 0)),
            (5, 5, 10, (5, 5)),
        ],
    )
    def test_allocation(self, plan, purchased, needed, expected):
        assert BillingService.allocate_consumption(plan, purchased, needed) == expected

    def test_never_negative(self):
        assert BillingService.allocate_consumption(-5, 0, 10) == (0, 0)
        assert BillingService.allocate_consumption(0, -5, 10) == (0, 0)

    def test_admin_pool_is_drained_before_purchased_pool(self):
        """The three-pool allocator preserves the documented debit order."""
        assert BillingService.allocate_consumption_with_bonus(0, 20, 40, 40) == (
            0,
            20,
            20,
        )


@pytest.mark.asyncio
async def test_consume_credits_drains_admin_pool_before_purchased_pool(
    billing_service, mock_supabase_client, sample_org_id
):
    """Platform-granted credits are used before customer-purchased credits."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    table_mock, _rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [_event_response(), _tx_response(sample_org_id, -10, 55)],
        _debit_success(
            balance_after=55,
            plan_used=0,
            admin_used=10,
            purchased_used=0,
            plan_balance=0,
            admin_balance=15,
            purchased_balance=40,
        ),
    )

    with patch.object(
        credit_entitlement_service,
        "get_included_credits_per_billing_period",
        new=AsyncMock(return_value=0),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    tx_inserted = table_mock.insert.call_args[0][0]
    assert tx_inserted["metadata"]["admin_credits"] == 10
    assert tx_inserted["metadata"]["purchased_credits"] == 0


@pytest.mark.asyncio
async def test_consume_credits_enqueues_low_balance_notification(
    billing_service, mock_supabase_client, sample_org_id
):
    """Falling to 20% of included credits creates a durable warning task."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    admin = OrganizationMember(
        id=uuid4(),
        email="admin@example.com",
        first_name="Ada",
        last_name="Admin",
        is_verified=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        roles=[MemberRole(id=uuid4(), name="org_admin", description="Admin")],
    )
    table_mock, _rpc_mock = _setup_consume_mocks(
        mock_supabase_client,
        [
            _event_response(),
            _tx_response(sample_org_id, -10, 20),
            MagicMock(
                data=[{"name": "Acme Corp", "low_credit_threshold_notified": None}]
            ),
            MagicMock(data=[]),
        ],
        _debit_success(
            balance_after=20,
            plan_used=10,
            purchased_used=0,
            plan_balance=20,
            purchased_balance=0,
        ),
    )

    sent_requests: list = []
    with (
        patch.object(
            credit_entitlement_service,
            "get_included_credits_per_billing_period",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "src.rbac.user_roles.service.user_role_service.get_users_by_organization",
            new=AsyncMock(return_value=([admin], None)),
        ),
        patch.object(
            notification_service,
            "send_notification",
            new=AsyncMock(
                side_effect=lambda request: (
                    sent_requests.append(request) or MagicMock(success=True)
                )
            ),
        ),
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert sent_requests == []
    outbox_payload = table_mock.upsert.call_args.args[0]
    assert outbox_payload["balance_after"] == 20
    assert outbox_payload["organization_id"] == str(sample_org_id)
    assert table_mock.upsert.call_args.kwargs["on_conflict"] == "credit_transaction_id"


@pytest.mark.asyncio
async def test_consume_credits_does_not_resend_threshold(
    billing_service, mock_supabase_client, sample_org_id
):
    """No duplicate emails when the threshold was already notified this cycle."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    _setup_consume_mocks(
        mock_supabase_client,
        [
            _event_response(),
            _tx_response(sample_org_id, -10, 20),
            MagicMock(
                data=[{"name": "Acme Corp", "low_credit_threshold_notified": 20}]
            ),
        ],
        _debit_success(
            balance_after=20,
            plan_used=10,
            purchased_used=0,
        ),
    )

    with (
        patch.object(
            credit_entitlement_service,
            "get_included_credits_per_billing_period",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "src.rbac.user_roles.service.user_role_service.get_users_by_organization",
            new=AsyncMock(return_value=([], None)),
        ),
        patch.object(
            notification_service, "send_notification", new=AsyncMock()
        ) as mock_send,
    ):
        result = await billing_service.consume_credits(request)

    assert result.success is True
    mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_credits_notification_failure_does_not_break_consumption(
    billing_service, mock_supabase_client, sample_org_id
):
    """Outbox persistence failures are logged and never fail consumption."""
    request = CreditConsumptionRequest(
        organization_id=sample_org_id,
        event_name="voice_call_minute",
        quantity=1,
    )
    _setup_consume_mocks(
        mock_supabase_client,
        [
            _event_response(),
            _tx_response(sample_org_id, -10, 20),
        ],
        _debit_success(
            balance_after=20,
            plan_used=10,
            purchased_used=0,
        ),
    )

    with patch.object(
        billing_service,
        "enqueue_low_credit_notification",
        new=AsyncMock(return_value=False),
    ) as enqueue:
        result = await billing_service.consume_credits(request)

    assert result.success is True
    assert result.balance_after == 20
    enqueue.assert_awaited_once()
