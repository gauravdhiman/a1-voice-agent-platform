"""Tests for versioned plan listing and subscription activation."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.billing.plan_version_models import BillingMode
from src.billing.versioned_subscription_models import (
    FreePlanActivationRequest,
    SubscriptionActivationState,
    VersionedSubscriptionCheckoutRequest,
)
from src.billing.versioned_subscription_service import VersionedSubscriptionService

ORG_ID = UUID("00000000-0000-0000-0000-000000000101")
FREE_VERSION_ID = UUID("00000000-0000-0000-0000-000000000102")
PAID_VERSION_ID = UUID("00000000-0000-0000-0000-000000000103")
SUBSCRIPTION_ID = UUID("00000000-0000-0000-0000-000000000104")


def _result(data):
    """Create the minimal Supabase response object used by the service."""
    return SimpleNamespace(data=data)


def _query(data):
    """Create a chainable Supabase query mock."""
    query = MagicMock()
    for method in (
        "select",
        "eq",
        "in_",
        "order",
        "limit",
        "single",
        "insert",
        "update",
    ):
        getattr(query, method).return_value = query
    query.execute.return_value = _result(data)
    return query


def _free_version():
    """Return a published free plan version row."""
    return {
        "id": str(FREE_VERSION_ID),
        "plan_product_id": "00000000-0000-0000-0000-000000000105",
        "version_number": 1,
        "status": "published",
        "display_label": "Free",
        "billing_mode": "free",
        "price_amount_cents": 0,
        "currency": "USD",
        "billing_interval": "monthly",
        "trial_period_days": None,
        "stripe_product_id": None,
        "stripe_price_id": None,
        "is_current_for_signup": True,
        "legacy_subscription_plan_id": None,
        "plan_products": {
            "slug": "free",
            "display_name": "Free",
            "description": "Try the platform",
            "sort_order": 0,
        },
    }


def _paid_version():
    """Return a published paid plan version row."""
    return {
        **_free_version(),
        "id": str(PAID_VERSION_ID),
        "plan_product_id": "00000000-0000-0000-0000-000000000106",
        "display_label": "Growth",
        "billing_mode": "paid",
        "price_amount_cents": 2900,
        "stripe_product_id": "prod_growth",
        "stripe_price_id": "price_growth",
        "plan_products": {
            "slug": "growth",
            "display_name": "Growth",
            "description": "For growing teams",
            "sort_order": 10,
        },
    }


class TestVersionedSubscriptionService:
    """Unit tests for the versioned activation service."""

    @pytest.mark.asyncio
    async def test_lists_only_current_published_versions_with_entitlements(self):
        """Customer plan listing excludes drafts and includes catalog metadata."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        versions = _query([_free_version(), _paid_version()])
        entitlements = _query(
            [
                {
                    "plan_version_id": str(FREE_VERSION_ID),
                    "entitlement_key": "included_credits_monthly",
                    "value": {"type": "integer", "value": 100},
                }
            ]
        )
        service.supabase.table.side_effect = lambda name: {
            "plan_versions": versions,
            "plan_version_entitlements": entitlements,
        }[name]

        result = await service.list_available_plan_versions()

        assert [plan.id for plan in result] == [FREE_VERSION_ID, PAID_VERSION_ID]
        assert result[0].billing_mode is BillingMode.FREE
        assert result[0].stripe_price_id is None
        assert result[0].entitlements["included_credits_monthly"]["value"] == 100

    @pytest.mark.asyncio
    async def test_free_activation_creates_non_stripe_subscription(self):
        """Free activation binds the immutable version without touching Stripe."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        service._get_signup_plan_version = AsyncMock(return_value=_free_version())
        service._get_existing_subscription = AsyncMock(return_value=None)
        subscription_row = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "subscription_plan_id": None,
            "plan_version_id": str(FREE_VERSION_ID),
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "status": "active",
            "current_period_start": datetime.now(timezone.utc).isoformat(),
            "current_period_end": None,
            "trial_start": None,
            "trial_end": None,
            "cancel_at_period_end": False,
            "cancelled_at": None,
            "metadata": {"billing_mode": "free"},
        }
        subscriptions = _query([subscription_row])
        service.supabase.table.return_value = subscriptions

        with patch(
            "src.billing.versioned_subscription_service.stripe_service"
        ) as stripe:
            result = await service.activate_free_plan(ORG_ID, FREE_VERSION_ID)

        assert result.subscription.id == SUBSCRIPTION_ID
        assert result.created is True
        payload = subscriptions.insert.call_args.args[0]
        assert payload["plan_version_id"] == str(FREE_VERSION_ID)
        assert payload["stripe_customer_id"] is None
        stripe.create_customer.assert_not_called()
        service.credit_grant_service.grant_for_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_free_activation_is_idempotent_for_same_active_version(self):
        """Refreshing onboarding does not create a second subscription."""
        service = VersionedSubscriptionService()
        service._get_signup_plan_version = AsyncMock(return_value=_free_version())
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(FREE_VERSION_ID),
                "status": "active",
                "stripe_customer_id": None,
            }
        )

        result = await service.activate_free_plan(ORG_ID, FREE_VERSION_ID)

        assert result.created is False
        assert result.subscription.id == SUBSCRIPTION_ID

    @pytest.mark.asyncio
    async def test_free_activation_rejects_paid_version(self):
        """A paid version can never be activated through the free endpoint."""
        service = VersionedSubscriptionService()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())

        with pytest.raises(ValueError, match="free plan"):
            await service.activate_free_plan(ORG_ID, PAID_VERSION_ID)

    @pytest.mark.asyncio
    async def test_paid_checkout_uses_versioned_metadata(self):
        """Paid checkout carries immutable version metadata for webhook binding."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(return_value=None)
        service.supabase.table.return_value = _query(
            [{"id": str(ORG_ID), "name": "Acme", "slug": "acme"}]
        )
        session = SimpleNamespace(id="cs_versioned", url="https://stripe.test/session")

        with patch(
            "src.billing.versioned_subscription_service.stripe_service"
        ) as stripe:
            stripe.create_customer = AsyncMock(
                return_value=SimpleNamespace(id="cus_acme")
            )
            stripe.create_checkout_session = AsyncMock(return_value=session)

            result = await service.create_paid_checkout(
                VersionedSubscriptionCheckoutRequest(
                    organization_id=ORG_ID,
                    plan_version_id=PAID_VERSION_ID,
                    success_url="https://app.test/onboarding/complete",
                    cancel_url="https://app.test/onboarding/plan",
                )
            )

        assert result.session_id == "cs_versioned"
        kwargs = stripe.create_checkout_session.await_args.kwargs
        assert kwargs["price_id"] == "price_growth"
        assert kwargs["metadata"]["plan_version_id"] == str(PAID_VERSION_ID)
        assert kwargs["metadata"]["organization_id"] == str(ORG_ID)
        assert kwargs["metadata"]["type"] == "versioned_subscription"

    @pytest.mark.asyncio
    async def test_paid_checkout_requires_stripe_price(self):
        """Paid activation fails closed when a published version lacks a price."""
        service = VersionedSubscriptionService()
        version = {**_paid_version(), "stripe_price_id": None}
        service._get_signup_plan_version = AsyncMock(return_value=version)

        with pytest.raises(ValueError, match="Stripe Price"):
            await service.create_paid_checkout(
                VersionedSubscriptionCheckoutRequest(
                    organization_id=ORG_ID,
                    plan_version_id=PAID_VERSION_ID,
                    success_url="https://app.test/onboarding/complete",
                    cancel_url="https://app.test/onboarding/plan",
                )
            )

    @pytest.mark.asyncio
    async def test_status_is_unselected_without_subscription(self):
        """Organizations without a plan have an explicit onboarding state."""
        service = VersionedSubscriptionService()
        service._get_existing_subscription = AsyncMock(return_value=None)

        result = await service.get_activation_status(ORG_ID)

        assert result.state is SubscriptionActivationState.UNSELECTED
        assert result.plan_version_id is None


class TestVersionedSubscriptionRoutes:
    """Route-level tests for activation permission and error contracts."""

    @pytest.mark.asyncio
    async def test_free_activation_requires_billing_access(self):
        """A user without org billing access cannot activate a plan."""
        from fastapi import HTTPException

        from src.billing.routes import activate_free_plan

        request = FreePlanActivationRequest(
            organization_id=ORG_ID, plan_version_id=FREE_VERSION_ID
        )
        with (
            patch(
                "src.billing.routes.assert_billing_access",
                side_effect=HTTPException(status_code=403, detail="forbidden"),
            ),
            patch("src.billing.routes.versioned_subscription_service") as service,
        ):
            service.activate_free_plan = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await activate_free_plan(request, (UUID(int=1), MagicMock()))

        assert exc_info.value.status_code == 403
        service.activate_free_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_paid_checkout_maps_catalog_validation_to_bad_request(self):
        """Catalog validation errors are returned as a client-facing 400."""
        from fastapi import HTTPException

        from src.billing.routes import create_versioned_subscription_checkout

        request = VersionedSubscriptionCheckoutRequest(
            organization_id=ORG_ID,
            plan_version_id=PAID_VERSION_ID,
            success_url="https://app.test/onboarding/complete",
            cancel_url="https://app.test/onboarding/plan",
        )
        profile = MagicMock()
        with (
            patch("src.billing.routes.assert_billing_access"),
            patch("src.billing.routes.versioned_subscription_service") as service,
        ):
            service.create_paid_checkout = AsyncMock(
                side_effect=ValueError("Stripe Price is required")
            )
            with pytest.raises(HTTPException) as exc_info:
                await create_versioned_subscription_checkout(
                    request, (UUID(int=1), profile)
                )

        assert exc_info.value.status_code == 400
        assert "Stripe Price" in exc_info.value.detail
