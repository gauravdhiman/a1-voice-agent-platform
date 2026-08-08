"""
Tests for Stripe webhook plan_version_id binding.

Phase 2: new subscriptions and explicit Stripe plan changes must bind
``organization_subscriptions.plan_version_id`` from the Stripe price ID.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.billing.models import SubscriptionStatus


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def plan_version_id():
    return uuid4()


@pytest.fixture
def legacy_plan_id():
    return uuid4()


def _stripe_subscription_event(org_id, price_id="price_new", status="active"):
    return {
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "customer": "cus_stripe_123",
                "status": status,
                "metadata": {"organization_id": str(org_id)},
                "items": {"data": [{"price": {"id": price_id}}]},
                "current_period_start": int(datetime.now(timezone.utc).timestamp()),
                "current_period_end": int(datetime.now(timezone.utc).timestamp())
                + 86400,
                "cancel_at_period_end": False,
            }
        }
    }


class TestWebhookPlanVersionBinding:
    """Webhook handlers set plan_version_id from Stripe price."""

    @pytest.mark.asyncio
    async def test_subscription_created_sets_plan_version_id(
        self, org_id, plan_version_id, legacy_plan_id
    ):
        from src.billing.webhook_handler import handle_subscription_created

        event = _stripe_subscription_event(org_id, price_id="price_new")

        resolved = MagicMock()
        resolved.plan_version_id = plan_version_id
        resolved.subscription_plan_id = legacy_plan_id
        resolved.stripe_price_id = "price_new"

        legacy_plan = MagicMock()
        legacy_plan.id = legacy_plan_id
        legacy_plan.included_credits = 500

        with patch(
            "src.billing.webhook_handler.plan_version_service.resolve_checkout_plan",
            new_callable=AsyncMock,
            return_value=resolved,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_subscription_plan",
            new_callable=AsyncMock,
            return_value=legacy_plan,
        ), patch(
            "src.billing.webhook_handler.billing_service.create_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_create, patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_update:
            created_sub = MagicMock(id=uuid4(), organization_id=org_id)
            mock_create.return_value = created_sub

            await handle_subscription_created(event)

            create_kwargs = mock_create.call_args[0][0]
            assert create_kwargs.subscription_plan_id == legacy_plan_id

            update_kwargs = mock_update.call_args[0][1]
            assert update_kwargs.plan_version_id == plan_version_id

    @pytest.mark.asyncio
    async def test_subscription_created_supports_version_without_legacy_plan(
        self, org_id, plan_version_id
    ):
        """A new catalog version can be activated even without a legacy plan row."""
        from src.billing.webhook_handler import handle_subscription_created

        event = _stripe_subscription_event(org_id, price_id="price_new")
        resolved = MagicMock(
            plan_version_id=plan_version_id,
            subscription_plan_id=None,
            stripe_price_id="price_new",
        )

        with patch(
            "src.billing.webhook_handler.plan_version_service.resolve_checkout_plan",
            new_callable=AsyncMock,
            return_value=resolved,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_subscription_plan",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "src.billing.webhook_handler.versioned_subscription_service.record_paid_subscription_from_stripe",
            new_callable=AsyncMock,
        ) as mock_record:
            await handle_subscription_created(event)

        mock_record.assert_awaited_once_with(org_id, resolved, event["data"]["object"])

    @pytest.mark.asyncio
    async def test_subscription_updated_price_change_updates_plan_version(
        self, org_id, plan_version_id, legacy_plan_id
    ):
        from src.billing.webhook_handler import handle_subscription_updated

        event = _stripe_subscription_event(org_id, price_id="price_upgraded")

        resolved = MagicMock()
        resolved.plan_version_id = plan_version_id
        resolved.subscription_plan_id = legacy_plan_id

        current_plan = MagicMock()
        current_plan.id = uuid4()
        current_plan.included_credits = 500
        current_plan.name = "Starter"

        current_sub = MagicMock()
        current_sub.plan = current_plan
        current_sub.plan_version_id = uuid4()

        new_plan = MagicMock()
        new_plan.id = legacy_plan_id
        new_plan.included_credits = 1000
        new_plan.name = "Growth"

        with patch(
            "src.billing.webhook_handler.plan_version_service.resolve_checkout_plan",
            new_callable=AsyncMock,
            return_value=resolved,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=current_sub,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_subscription_plan",
            new_callable=AsyncMock,
            return_value=new_plan,
        ), patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_update:
            await handle_subscription_updated(event)

            update_data = mock_update.call_args[0][1]
            assert update_data.plan_version_id == plan_version_id
            assert update_data.subscription_plan_id == legacy_plan_id

    @pytest.mark.asyncio
    async def test_invoice_payment_uses_idempotent_plan_credit_grant(
        self, org_id, plan_version_id
    ):
        """Paid invoice renewals grant through the shared policy service."""
        from src.billing.webhook_handler import handle_invoice_payment_succeeded

        event = {
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": "in_renewal_123",
                    "customer": "cus_stripe_123",
                    "subscription": "sub_stripe_123",
                    "amount_paid": 2900,
                    "currency": "usd",
                    "status_transitions": {
                        "paid_at": int(datetime.now(timezone.utc).timestamp())
                    },
                }
            },
        }
        stripe_subscription = {
            "id": "sub_stripe_123",
            "metadata": {"organization_id": str(org_id)},
            "items": {"data": [{"price": {"id": "price_growth"}}]},
            "current_period_start": int(datetime.now(timezone.utc).timestamp()),
            "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 86400,
        }
        org_subscription = {
            "id": str(uuid4()),
            "organization_id": str(org_id),
            "plan_version_id": str(plan_version_id),
        }

        with patch(
            "src.billing.webhook_handler.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value=stripe_subscription,
        ), patch(
            "src.billing.webhook_handler.billing_service.create_billing_history",
            new_callable=AsyncMock,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=org_subscription,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_subscription_plans",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.billing.webhook_handler.credit_grant_service.grant_for_subscription",
            new_callable=AsyncMock,
        ) as grant:
            await handle_invoice_payment_succeeded(event)

        grant.assert_awaited_once()
        assert grant.await_args.kwargs["grant_reason"] == "invoice_paid"
        assert grant.await_args.kwargs["grant_key"] == "stripe-invoice:in_renewal_123"
