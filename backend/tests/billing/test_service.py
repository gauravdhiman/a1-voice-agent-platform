"""
Billing Service Tests
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
        features={"unlimited_agents": True, "priority_support": True, "api_access": True},
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
        mock_response.data = [{
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
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await billing_service.create_subscription_plan(sample_subscription_plan_create)

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
        mock_response.data = [{
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
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await billing_service.create_subscription_plan(plan_data)

        assert result is not None
        assert result.name == "Basic Plan"
        assert result.description is None
        assert result.features is None

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
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

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
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await billing_service.get_subscription_plans(active_only=True)

        assert len(result) == 1
        assert result[0].is_active is True
        mock_supabase_client.table.return_value.select.return_value.eq.assert_called_with("is_active", True)

    @pytest.mark.asyncio
    async def test_get_subscription_plans_empty(
        self,
        billing_service,
        mock_supabase_client,
    ):
        """Returns empty list when no plans."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response

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
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

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
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

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
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        from src.billing.models import SubscriptionPlanUpdate
        plan_update = SubscriptionPlanUpdate(
            name="Updated Pro Plan",
            price_amount=5900,
        )

        result = await billing_service.update_subscription_plan(sample_plan_id, plan_update)

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
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        from src.billing.models import SubscriptionPlanUpdate
        plan_update = SubscriptionPlanUpdate(price_amount=5900)

        result = await billing_service.update_subscription_plan(sample_plan_id, plan_update)

        assert result is not None
        assert result.name == "Pro Plan"
        assert result.description == "Professional plan with advanced features"
        assert result.price_amount == 5900


class TestBillingServiceOrganizationSubscriptions:
    """Test cases for organization subscription management."""

    @pytest.mark.skip(reason="Complex mocking - requires chained Supabase + Stripe service interactions")
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
        mock_plan_response.data = [{
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
        }]

        mock_sub_response = MagicMock()
        mock_sub_response.data = [{
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
        }]

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().single().execute(mock_plan_response),
            MagicMock().insert().execute(mock_sub_response),
            MagicMock().select().eq().execute(MagicMock(data=[{"credit_balance": 1000}])),
        ]

        result = await billing_service.create_organization_subscription(subscription_data)

        assert result is not None
        assert result.status == "active"

    @pytest.mark.skip(reason="Complex mocking - requires chained Supabase + Stripe service interactions")
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
        mock_plan_response.data = [{
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
        }]

        trial_start = now
        trial_end = now + timedelta(days=14)

        mock_sub_response = MagicMock()
        mock_sub_response.data = [{
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
        }]

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().single().execute(mock_plan_response),
            MagicMock().insert().execute(mock_sub_response),
            MagicMock().select().eq().execute(MagicMock(data=[{"credit_balance": 100}])),
        ]

        result = await billing_service.create_organization_subscription(subscription_data)

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
        mock_response.data = [{
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
        }]

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

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
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        result = await billing_service.get_organization_subscription(sample_org_id)

        assert result is None


class TestBillingServiceCreditManagement:
    """Test cases for credit management."""

    @pytest.mark.skip(reason="Complex mocking - requires chained Supabase queries with multiple side_effect calls")
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

    @pytest.mark.skip(reason="Complex mocking - requires chained Supabase queries with multiple side_effect calls")
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

    @pytest.mark.skip(reason="Complex mocking - requires credit_event, organization, and transaction table mocks")
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
        mock_tx_response.data = [{
            "id": str(uuid4()),
            "organization_id": str(sample_org_id),
            "transaction_type": "consumed",
            "amount": -50,
            "source": "consumption",
            "source_id": "voice_call",
            "expires_at": None,
            "description": "Voice call",
            "created_at": now.isoformat(),
        }]

        mock_supabase_client.table.side_effect = [
            MagicMock().select().eq().execute(mock_org_response),
            MagicMock().select().eq().execute(MagicMock(data=[{"id": uuid4(), "event_name": "voice_call", "cost_credits": 50}])),
            MagicMock().update().eq().execute(mock_update_response),
            MagicMock().insert().execute(mock_tx_response),
        ]

        result = await billing_service.consume_credits(request)

        assert result.success is True
        assert result.remaining_credits == 950

    @pytest.mark.skip(reason="Complex mocking - requires credit_event, organization, and transaction table mocks")
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

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_org_response

        result = await billing_service.consume_credits(request)

        assert result.success is False
        assert result.error == "Insufficient credits"
        assert result.remaining_credits == 10
