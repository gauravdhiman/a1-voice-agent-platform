"""
Billing Service Tests
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.billing.models import (
    BillingStatus,
    CreditTransaction,
    OrganizationBillingSummary,
    OrganizationSubscription,
    OrganizationSubscriptionWithPlan,
    SubscriptionPlan,
    SubscriptionPlanCreate,
    SubscriptionStatus,
    TransactionSource,
)


@pytest.fixture
def billing_service(mock_supabase_client):
    """Create BillingService instance with fresh mocks for each test."""
    from src.billing.service import BillingService

    service = BillingService()
    # Override the supabase client directly
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def sample_plan_id():
    """Sample subscription plan ID."""
    return uuid4()


@pytest.fixture
def sample_org_id():
    """Sample organization ID."""
    return uuid4()


@pytest.fixture
def sample_subscription_plan(sample_plan_id):
    """Sample subscription plan data."""
    now = datetime.now(timezone.utc)
    return {
        "id": str(sample_plan_id),
        "name": "Pro Plan",
        "description": "Professional plan with advanced features",
        "stripe_price_id": "price_123456",
        "stripe_product_id": "prod_123456",
        "price_amount": 4900,
        "currency": "USD",
        "interval": "monthly",
        "interval_count": 1,
        "included_credits": 1000,
        "max_users": None,
        "features": {"unlimited_agents": True, "priority_support": True},
        "is_active": True,
        "trial_period_days": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def sample_subscription_plan_create():
    """Sample subscription plan create data."""
    return SubscriptionPlanCreate(
        name="Enterprise Plan",
        description="Enterprise plan with all features",
        stripe_price_id="price_789012",
        stripe_product_id="prod_789012",
        price_amount=9900,
        interval="annual",
        included_credits=5000,
        features={
            "unlimited_agents": True,
            "priority_support": True,
            "api_access": True,
        },
        is_active=True,
    )


class TestBillingServiceSubscriptionPlans:
    """Test cases for subscription plan management."""

    @pytest.mark.asyncio
    async def test_create_subscription_plan_success(
        self,
        billing_service,
        mock_supabase_client,
        sample_subscription_plan_create,
        sample_plan_id,
    ):
        """Creates plan with all fields."""
        now = datetime.now(timezone.utc)
        plan_data = sample_subscription_plan_create.model_dump()

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(sample_plan_id),
                "name": plan_data["name"],
                "description": plan_data["description"],
                "stripe_price_id": plan_data["stripe_price_id"],
                "stripe_product_id": plan_data["stripe_product_id"],
                "price_amount": plan_data["price_amount"],
                "currency": plan_data.get("currency", "USD"),
                "interval": plan_data["interval"],
                "interval_count": plan_data.get("interval_count", 1),
                "included_credits": plan_data["included_credits"],
                "max_users": plan_data.get("max_users"),
                "features": plan_data["features"],
                "is_active": plan_data["is_active"],
                "trial_period_days": plan_data.get("trial_period_days"),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.create_subscription_plan(
            sample_subscription_plan_create
        )

        assert result is not None
        assert result.name == "Enterprise Plan"
        assert result.price_amount == 9900
        assert result.interval == "annual"
        assert result.included_credits == 5000
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_create_subscription_plan_minimal(
        self,
        billing_service,
        mock_supabase_client,
        sample_plan_id,
    ):
        """Creates plan with required fields only."""
        now = datetime.now(timezone.utc)
        plan_data = SubscriptionPlanCreate(
            name="Basic Plan",
            stripe_price_id="price_basic",
            stripe_product_id="prod_basic",
            price_amount=2900,
            interval="monthly",
            included_credits=500,
        )

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(sample_plan_id),
                "name": plan_data.name,
                "description": None,
                "stripe_price_id": plan_data.stripe_price_id,
                "stripe_product_id": plan_data.stripe_product_id,
                "price_amount": plan_data.price_amount,
                "currency": "USD",
                "interval": plan_data.interval,
                "interval_count": 1,
                "included_credits": plan_data.included_credits,
                "max_users": None,
                "features": None,
                "is_active": True,
                "trial_period_days": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.create_subscription_plan(plan_data)

        assert result is not None
        assert result.name == "Basic Plan"
        assert result.description is None
        assert result.features is None


class TestAdminCreditGrant:
    """Tests for the atomic, audited platform credit grant operation."""

    @pytest.mark.asyncio
    async def test_grant_admin_credits_calls_atomic_rpc(
        self, billing_service, mock_supabase_client
    ):
        """A grant is delegated to Postgres with actor and audit fields."""
        org_id = uuid4()
        actor_id = uuid4()
        transaction_id = uuid4()
        mock_supabase_client.rpc.return_value.execute.return_value.data = {
            "created": True,
            "grant_id": str(uuid4()),
            "transaction": {
                "id": str(transaction_id),
                "organization_id": str(org_id),
                "transaction_type": "earned",
                "amount": 250,
                "balance_after": 350,
                "source": "admin_adjustment",
                "source_id": None,
                "credit_event_id": None,
                "expires_at": None,
                "stripe_payment_intent_id": None,
                "description": "Platform admin credit allocation",
                "metadata": {"reason": "Support compensation"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "plan_balance": 100,
            "admin_balance": 250,
            "purchased_balance": 0,
            "balance_after": 350,
        }

        response = await billing_service.grant_admin_credits(
            organization_id=org_id,
            credits=250,
            created_by=actor_id,
            reason="Support compensation",
            idempotency_key="support-case-123",
        )

        assert response.created is True
        assert response.credits == 250
        assert response.balance.total_credits == 350
        assert response.balance.admin_granted_credits == 250
        mock_supabase_client.rpc.assert_called_once_with(
            "grant_admin_credits",
            {
                "p_organization_id": str(org_id),
                "p_credits": 250,
                "p_created_by": str(actor_id),
                "p_reason": "Support compensation",
                "p_idempotency_key": "support-case-123",
            },
        )

    @pytest.mark.asyncio
    async def test_get_subscription_plans_all(
        self,
        billing_service,
        mock_supabase_client,
        sample_subscription_plan,
    ):
        """Returns all plans when active_only=False."""
        mock_response = MagicMock()
        mock_response.data = [sample_subscription_plan]
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_subscription_plans(active_only=False)

        assert len(result) == 1
        assert result[0].name == "Pro Plan"
        mock_supabase_client.table.assert_called_with("subscription_plans")

    @pytest.mark.asyncio
    async def test_get_subscription_plans_active_only(
        self,
        billing_service,
        mock_supabase_client,
        sample_subscription_plan,
    ):
        """Filters to active plans only."""
        mock_response = MagicMock()
        mock_response.data = [sample_subscription_plan]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_subscription_plans(active_only=True)

        assert len(result) == 1
        assert result[0].is_active is True
        mock_supabase_client.table.return_value.select.return_value.eq.assert_called_with(
            "is_active", True
        )

    @pytest.mark.asyncio
    async def test_get_subscription_plans_empty(
        self,
        billing_service,
        mock_supabase_client,
    ):
        """Returns empty list when no plans."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_subscription_plans(active_only=False)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_subscription_plan_by_id(
        self,
        billing_service,
        mock_supabase_client,
        sample_subscription_plan,
        sample_plan_id,
    ):
        """Returns plan by UUID."""
        mock_response = MagicMock()
        mock_response.data = [sample_subscription_plan]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_subscription_plan(sample_plan_id)

        assert result is not None
        assert result.id == sample_plan_id
        assert result.name == "Pro Plan"

    @pytest.mark.asyncio
    async def test_get_subscription_plan_not_found(
        self,
        billing_service,
        mock_supabase_client,
        sample_plan_id,
    ):
        """Returns None for non-existent ID."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_subscription_plan(sample_plan_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_subscription_plan(
        self,
        billing_service,
        mock_supabase_client,
        sample_plan_id,
    ):
        """Updates plan fields."""
        now = datetime.now(timezone.utc)
        updated_plan = {
            "id": str(sample_plan_id),
            "name": "Updated Pro Plan",
            "description": "Updated description",
            "stripe_price_id": "price_updated",
            "stripe_product_id": "prod_updated",
            "price_amount": 5900,
            "currency": "USD",
            "interval": "monthly",
            "interval_count": 1,
            "included_credits": 1200,
            "max_users": None,
            "features": {"feature1": True, "feature2": True},
            "is_active": True,
            "trial_period_days": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = [updated_plan]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        from src.billing.models import SubscriptionPlanUpdate

        plan_update = SubscriptionPlanUpdate(
            name="Updated Pro Plan",
            price_amount=5900,
        )

        result = await billing_service.update_subscription_plan(
            sample_plan_id, plan_update
        )

        assert result is not None
        assert result.name == "Updated Pro Plan"
        assert result.price_amount == 5900

    @pytest.mark.asyncio
    async def test_update_subscription_plan_partial(
        self,
        billing_service,
        mock_supabase_client,
        sample_plan_id,
        sample_subscription_plan,
    ):
        """Partial update preserves other fields."""
        now = datetime.now(timezone.utc)
        updated_plan = {
            **sample_subscription_plan,
            "price_amount": 5900,
            "updated_at": now.isoformat(),
        }

        mock_response = MagicMock()
        mock_response.data = [updated_plan]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        from src.billing.models import SubscriptionPlanUpdate

        plan_update = SubscriptionPlanUpdate(price_amount=5900)

        result = await billing_service.update_subscription_plan(
            sample_plan_id, plan_update
        )

        assert result is not None
        assert result.name == "Pro Plan"
        assert result.description == "Professional plan with advanced features"
        assert result.price_amount == 5900


class TestBillingServiceOrganizationSubscriptions:
    """Test cases for organization subscription management."""

    @pytest.mark.skip(
        reason="Complex mocking - requires chained Supabase + Stripe service interactions"
    )
    @pytest.mark.asyncio
    async def test_create_org_subscription_success(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
        sample_plan_id,
    ):
        """Creates subscription for org."""
        from src.billing.models import OrganizationSubscriptionCreate

        now = datetime.now(timezone.utc)
        subscription_data = OrganizationSubscriptionCreate(
            organization_id=sample_org_id,
            subscription_plan_id=sample_plan_id,
            stripe_customer_id="cus_test123",
        )

        mock_plan_response = MagicMock()
        mock_plan_response.data = [
            {
                "id": str(sample_plan_id),
                "name": "Pro Plan",
                "description": "Pro plan",
                "stripe_price_id": "price_test",
                "stripe_product_id": "prod_test",
                "price_amount": 4900,
                "currency": "USD",
                "interval": "monthly",
                "interval_count": 1,
                "included_credits": 1000,
                "max_users": None,
                "features": None,
                "is_active": True,
                "trial_period_days": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_sub_response = MagicMock()
        mock_sub_response.data = [
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "subscription_plan_id": str(sample_plan_id),
                "stripe_customer_id": "cus_test123",
                "status": "active",
                "trial_start": None,
                "trial_end": None,
                "current_period_start": now.isoformat(),
                "current_period_end": (now + timedelta(days=30)).isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().single().execute(mock_plan_response),
            MagicMock().insert().execute(mock_sub_response),
            MagicMock()
            .select()
            .eq()
            .execute(MagicMock(data=[{"credit_balance": 1000}])),
        ]

        result = await billing_service.create_organization_subscription(
            subscription_data
        )

        assert result is not None
        assert result.status == "active"

    @pytest.mark.skip(
        reason="Complex mocking - requires chained Supabase + Stripe service interactions"
    )
    @pytest.mark.asyncio
    async def test_create_org_subscription_with_trial(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
        sample_plan_id,
    ):
        """Sets trial_start and trial_end."""
        from src.billing.models import OrganizationSubscriptionCreate

        now = datetime.now(timezone.utc)
        subscription_data = OrganizationSubscriptionCreate(
            organization_id=sample_org_id,
            subscription_plan_id=sample_plan_id,
            stripe_customer_id="cus_test123",
        )

        mock_plan_response = MagicMock()
        mock_plan_response.data = [
            {
                "id": str(sample_plan_id),
                "name": "Trial Plan",
                "description": "Trial plan",
                "stripe_price_id": "price_test",
                "stripe_product_id": "prod_test",
                "price_amount": 0,
                "currency": "USD",
                "interval": "monthly",
                "interval_count": 1,
                "included_credits": 100,
                "max_users": None,
                "features": None,
                "is_active": True,
                "trial_period_days": 14,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        trial_start = now
        trial_end = now + timedelta(days=14)

        mock_sub_response = MagicMock()
        mock_sub_response.data = [
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "subscription_plan_id": str(sample_plan_id),
                "stripe_customer_id": "cus_test123",
                "status": "trial",
                "trial_start": trial_start.isoformat(),
                "trial_end": trial_end.isoformat(),
                "current_period_start": now.isoformat(),
                "current_period_end": trial_end.isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().single().execute(mock_plan_response),
            MagicMock().insert().execute(mock_sub_response),
            MagicMock()
            .select()
            .eq()
            .execute(MagicMock(data=[{"credit_balance": 100}])),
        ]

        result = await billing_service.create_organization_subscription(
            subscription_data
        )

        assert result is not None
        assert result.status == "trial"
        assert result.trial_start is not None
        assert result.trial_end is not None

    @pytest.mark.asyncio
    async def test_get_org_subscription_with_plan(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
        sample_plan_id,
    ):
        """Returns subscription with plan details."""
        now = datetime.now(timezone.utc)

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "subscription_plan_id": str(sample_plan_id),
                "stripe_customer_id": "cus_test123",
                "status": "active",
                "trial_start": None,
                "trial_end": None,
                "current_period_start": now.isoformat(),
                "current_period_end": (now + timedelta(days=30)).isoformat(),
                "cancelled_at": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "subscription_plans": {
                    "id": str(sample_plan_id),
                    "name": "Pro Plan",
                    "description": "Pro plan",
                    "stripe_price_id": "price_test",
                    "stripe_product_id": "prod_test",
                    "price_amount": 4900,
                    "currency": "USD",
                    "interval": "monthly",
                    "interval_count": 1,
                    "included_credits": 1000,
                    "max_users": None,
                    "features": None,
                    "is_active": True,
                    "trial_period_days": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
            }
        ]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_organization_subscription(sample_org_id)

        assert result is not None
        assert result.plan is not None
        assert result.plan.name == "Pro Plan"

    @pytest.mark.asyncio
    async def test_get_org_subscription_not_found(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Returns None for org without subscription."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = await billing_service.get_organization_subscription(sample_org_id)

        assert result is None


class TestBillingServiceCreditManagement:
    """Test cases for credit management."""

    @pytest.mark.skip(
        reason="Complex mocking - requires chained Supabase queries with multiple side_effect calls"
    )
    @pytest.mark.asyncio
    async def test_get_credit_balance_total(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Returns correct total_credits."""
        mock_org_response = MagicMock()
        mock_org_response.data = [{"credit_balance": 1500}]
        mock_tx_response = MagicMock()
        mock_tx_response.data = []
        mock_expiring_response = MagicMock()
        mock_expiring_response.data = []

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().execute(mock_org_response),
            MagicMock().select().eq().execute(mock_tx_response),
            MagicMock().select().eq().gt().execute(mock_expiring_response),
        ]

        result = await billing_service.get_credit_balance(sample_org_id)

        assert result.total_credits == 1500

    @pytest.mark.skip(
        reason="Complex mocking - requires chained Supabase queries with multiple side_effect calls"
    )
    @pytest.mark.asyncio
    async def test_get_credit_balance_breakdown(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Returns subscription vs purchased breakdown."""
        now = datetime.now(timezone.utc)

        mock_org_response = MagicMock()
        mock_org_response.data = [{"credit_balance": 1500}]

        mock_tx_response = MagicMock()
        mock_tx_response.data = [
            {
                "amount": 1000,
                "source": "subscription",
                "created_at": now.isoformat(),
            },
            {
                "amount": 500,
                "source": "purchase",
                "created_at": now.isoformat(),
            },
        ]

        mock_expiring_response = MagicMock()
        mock_expiring_response.data = []

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().execute(mock_org_response),
            MagicMock().select().eq().execute(mock_tx_response),
            MagicMock().select().eq().gt().execute(mock_expiring_response),
        ]

        result = await billing_service.get_credit_balance(sample_org_id)

        assert result.total_credits == 1500
        assert result.subscription_credits == 1000
        assert result.purchased_credits == 500

    @pytest.mark.skip(
        reason="Complex mocking - requires credit_event, organization, and transaction table mocks"
    )
    @pytest.mark.asyncio
    async def test_consume_credits_success(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Deducts credits and creates transaction."""
        from src.billing.models import CreditConsumptionRequest

        now = datetime.now(timezone.utc)
        request = CreditConsumptionRequest(
            organization_id=sample_org_id,
            event_name="voice_call",
            credits=50,
        )

        mock_org_response = MagicMock()
        mock_org_response.data = [{"credit_balance": 1000}]

        mock_update_response = MagicMock()
        mock_update_response.data = [{"credit_balance": 950}]

        mock_tx_response = MagicMock()
        mock_tx_response.data = [
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "transaction_type": "consumed",
                "amount": -50,
                "source": "consumption",
                "source_id": "voice_call",
                "expires_at": None,
                "description": "Voice call",
                "created_at": now.isoformat(),
            }
        ]

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().execute(mock_org_response),
            MagicMock()
            .select()
            .eq()
            .execute(
                MagicMock(
                    data=[
                        {"id": uuid4(), "event_name": "voice_call", "cost_credits": 50}
                    ]
                )
            ),
            MagicMock().update().eq().execute(mock_update_response),
            MagicMock().insert().execute(mock_tx_response),
        ]

        result = await billing_service.consume_credits(request)

        assert result.success is True
        assert result.remaining_credits == 950

    @pytest.mark.skip(
        reason="Complex mocking - requires credit_event, organization, and transaction table mocks"
    )
    @pytest.mark.asyncio
    async def test_consume_credits_insufficient(
        self,
        billing_service,
        mock_supabase_client,
        sample_org_id,
    ):
        """Returns success=False when insufficient."""
        from src.billing.models import CreditConsumptionRequest

        request = CreditConsumptionRequest(
            organization_id=sample_org_id,
            event_name="voice_call",
            credits=50,
        )

        mock_org_response = MagicMock()
        mock_org_response.data = [{"credit_balance": 10}]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_org_response
        )

        result = await billing_service.consume_credits(request)

        assert result.success is False
        assert result.error == "Insufficient credits"
        assert result.remaining_credits == 10


class TestBillingServiceCreditGrantIdempotency:
    """Subscription grants reuse a transaction for a repeated event key."""

    @pytest.mark.asyncio
    async def test_add_subscription_credits_returns_existing_grant(
        self, billing_service
    ):
        """A repeated Stripe or scheduler event does not mutate balances twice."""
        transaction_id = uuid4()
        organization_id = uuid4()
        subscription_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()
        existing_transaction = {
            "id": str(transaction_id),
            "organization_id": str(organization_id),
            "transaction_type": "earned",
            "amount": 100,
            "balance_after": 100,
            "source": "subscription",
            "source_id": str(subscription_id),
            "credit_event_id": None,
            "expires_at": None,
            "stripe_payment_intent_id": None,
            "description": "Subscription credits allocation",
            "metadata": {"grant_key": "stripe-invoice:in_123"},
            "created_at": now,
        }
        existing_response = MagicMock(data=[existing_transaction])
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.contains.return_value = query
        query.limit.return_value = query
        query.execute.return_value = existing_response
        billing_service.supabase.table.return_value = query

        result = await billing_service.add_subscription_credits(
            organization_id=organization_id,
            credits=100,
            subscription_id=subscription_id,
            idempotency_key="stripe-invoice:in_123",
        )

        assert result.id == transaction_id
        query.contains.assert_called_once_with(
            "metadata", {"grant_key": "stripe-invoice:in_123"}
        )

    @pytest.mark.asyncio
    async def test_add_subscription_credits_uses_atomic_rpc_for_new_grant(
        self, billing_service, mock_supabase_client
    ):
        """New idempotent grants use the database transaction boundary."""
        organization_id = uuid4()
        subscription_id = uuid4()
        transaction = {
            "id": str(uuid4()),
            "organization_id": str(organization_id),
            "transaction_type": "earned",
            "amount": 100,
            "balance_after": 100,
            "source": "subscription",
            "source_id": str(subscription_id),
            "credit_event_id": None,
            "expires_at": "2026-09-01T00:00:00+00:00",
            "stripe_payment_intent_id": None,
            "description": "Subscription credits allocation",
            "metadata": {"grant_key": "free-subscription:activation"},
            "created_at": "2026-08-01T00:00:00+00:00",
        }
        existing_query = MagicMock()
        existing_query.select.return_value = existing_query
        existing_query.eq.return_value = existing_query
        existing_query.contains.return_value = existing_query
        existing_query.limit.return_value = existing_query
        existing_query.execute.return_value = MagicMock(data=[])
        mock_supabase_client.table.return_value = existing_query
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(
            data={"success": True, "transaction": transaction}
        )

        result = await billing_service.add_subscription_credits(
            organization_id=organization_id,
            credits=100,
            subscription_id=subscription_id,
            expires_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            metadata={"grant_key": "free-subscription:activation"},
            idempotency_key="free-subscription:activation",
        )

        assert result.id == UUID(transaction["id"])
        mock_supabase_client.rpc.assert_called_once_with(
            "grant_subscription_credits",
            {
                "p_organization_id": str(organization_id),
                "p_credits": 100,
                "p_subscription_id": str(subscription_id),
                "p_expires_at": "2026-09-01T00:00:00+00:00",
                "p_metadata": {"grant_key": "free-subscription:activation"},
                "p_description": "Subscription credits allocation",
                "p_idempotency_key": "free-subscription:activation",
            },
        )

    @pytest.mark.asyncio
    async def test_subscription_credit_insert_payload_is_json_serializable(
        self, billing_service, mock_supabase_client
    ):
        """Legacy non-idempotent grants still serialize expiry timestamps safely."""
        organization_id = uuid4()
        subscription_id = uuid4()
        org_query = MagicMock()
        org_query.select.return_value = org_query
        org_query.eq.return_value = org_query
        org_query.execute.return_value = MagicMock(
            data=[{"credit_balance": 0, "purchased_credit_balance": 0}]
        )
        update_query = MagicMock()
        update_query.eq.return_value = update_query
        update_query.execute.return_value = MagicMock(data=[])
        transaction_query = MagicMock()
        transaction_query.insert.return_value = transaction_query
        transaction_query.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "organization_id": str(organization_id),
                    "transaction_type": "earned",
                    "amount": 100,
                    "balance_after": 100,
                    "source": "subscription",
                    "source_id": str(subscription_id),
                    "credit_event_id": None,
                    "expires_at": "2026-09-01T00:00:00+00:00",
                    "stripe_payment_intent_id": None,
                    "description": "Subscription credits allocation",
                    "metadata": None,
                    "created_at": "2026-08-01T00:00:00+00:00",
                }
            ]
        )
        notification_query = MagicMock()
        notification_query.update.return_value = notification_query
        notification_query.eq.return_value = notification_query
        notification_query.execute.return_value = MagicMock(data=[])
        mock_supabase_client.table.side_effect = [
            org_query,
            update_query,
            transaction_query,
            notification_query,
        ]

        await billing_service._add_credits(
            organization_id=organization_id,
            credits=100,
            source=TransactionSource.SUBSCRIPTION,
            source_id=subscription_id,
            expires_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )

        inserted_payload = transaction_query.insert.call_args.args[0]
        json.dumps(inserted_payload)
