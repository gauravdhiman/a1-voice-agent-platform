"""Tests for versioned plan listing and subscription activation."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from src.billing.plan_version_models import BillingMode
from src.billing.stripe_service import StripeService
from src.billing.versioned_subscription_models import (
    FreePlanActivationRequest,
    PlanChangeConfirmRequest,
    PlanChangePreviewRequest,
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
        "display_label": "Starter",
        "billing_mode": "paid",
        "price_amount_cents": 2900,
        "stripe_product_id": "prod_growth",
        "stripe_price_id": "price_growth",
        "plan_products": {
            "slug": "starter",
            "display_name": "Starter",
            "description": "For growing teams",
            "sort_order": 10,
        },
    }


class TestVersionedSubscriptionService:
    """Unit tests for the versioned activation service."""

    def test_catalog_tier_rank_orders_scale_above_pro(self):
        assert (
            VersionedSubscriptionService._catalog_tier_rank(
                {"slug": "scale", "sort_order": 10}
            )
            == 30
        )
        assert (
            VersionedSubscriptionService._catalog_tier_rank(
                {"slug": "pro", "sort_order": 10}
            )
            == 20
        )

    @pytest.mark.asyncio
    async def test_activate_default_free_plan_selects_current_free_version(self):
        """Platform provisioning resolves and activates the published free plan."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        plan_versions = _query([{"id": str(FREE_VERSION_ID)}])
        service.supabase.table.return_value = plan_versions
        service.activate_free_plan = AsyncMock(return_value="activated")

        result = await service.activate_default_free_plan(ORG_ID)

        assert result == "activated"
        service.activate_free_plan.assert_awaited_once_with(ORG_ID, FREE_VERSION_ID)

    @pytest.mark.asyncio
    async def test_activate_default_free_plan_rejects_missing_catalog_plan(self):
        """Platform provisioning fails safely when no published free plan exists."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.table.return_value = _query([])

        with pytest.raises(ValueError, match="No published free plan"):
            await service.activate_default_free_plan(ORG_ID)

    @pytest.mark.asyncio
    async def test_platform_admin_can_assign_a_published_paid_plan(self):
        """Controlled provisioning records an explicitly selected paid plan."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(return_value=None)

        subscription_row = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "subscription_plan_id": None,
            "plan_version_id": str(PAID_VERSION_ID),
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "status": "active",
            "current_period_start": "2026-09-09T00:00:00+00:00",
            "current_period_end": "2026-10-09T00:00:00+00:00",
            "metadata": {"activation_source": "platform_admin"},
        }
        query = _query([subscription_row])
        service.supabase.table.return_value = query

        result = await service.assign_plan_for_platform_admin(ORG_ID, PAID_VERSION_ID)

        assert result.created is True
        assert result.subscription.plan_version_id == PAID_VERSION_ID
        payload = query.insert.call_args.args[0]
        assert payload["metadata"]["activation_source"] == "platform_admin"
        assert payload["metadata"]["billing_mode"] == BillingMode.PAID.value
        service.credit_grant_service.grant_for_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_platform_admin_assignment_rejects_different_active_plan(self):
        """An active subscription cannot be silently replaced by provisioning."""
        service = VersionedSubscriptionService()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "plan_version_id": str(FREE_VERSION_ID),
                "status": "active",
            }
        )

        with pytest.raises(ValueError, match="already has an active subscription"):
            await service.assign_plan_for_platform_admin(ORG_ID, PAID_VERSION_ID)

    @pytest.mark.asyncio
    async def test_platform_admin_assignment_retries_existing_admin_grant(self):
        """Retrying the same admin assignment repairs a missing credit grant."""
        service = VersionedSubscriptionService()
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(PAID_VERSION_ID),
                "status": "active",
                "current_period_start": "2026-09-01T00:00:00+00:00",
                "current_period_end": "2026-10-01T00:00:00+00:00",
                "metadata": {"activation_source": "platform_admin"},
            }
        )

        result = await service.assign_plan_for_platform_admin(ORG_ID, PAID_VERSION_ID)

        assert result.created is False
        service.credit_grant_service.grant_for_subscription.assert_awaited_once()
        grant = service.credit_grant_service.grant_for_subscription.await_args
        assert grant.kwargs["grant_reason"] == "activation"
        assert grant.kwargs["grant_key"].startswith("platform-admin-assignment:")

    @pytest.mark.asyncio
    async def test_platform_admin_assignment_rejects_unexpected_existing_status(self):
        """Provisioning does not overwrite subscriptions in an unknown state."""
        service = VersionedSubscriptionService()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "plan_version_id": str(PAID_VERSION_ID),
                "status": "past_due",
            }
        )

        with pytest.raises(ValueError, match="already has an active subscription"):
            await service.assign_plan_for_platform_admin(ORG_ID, PAID_VERSION_ID)

    @pytest.mark.asyncio
    async def test_platform_admin_assignment_updates_cancelled_subscription(self):
        """A cancelled subscription can be reactivated with the selected plan."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(FREE_VERSION_ID),
                "status": "cancelled",
            }
        )
        updated_row = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "plan_version_id": str(PAID_VERSION_ID),
            "status": "active",
            "current_period_start": "2026-09-09T00:00:00+00:00",
            "current_period_end": "2026-10-09T00:00:00+00:00",
            "metadata": {"activation_source": "platform_admin"},
        }
        query = _query([updated_row])
        service.supabase.table.return_value = query

        result = await service.assign_plan_for_platform_admin(ORG_ID, PAID_VERSION_ID)

        assert result.created is False
        query.update.assert_called_once()
        service.credit_grant_service.grant_for_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_platform_admin_assignment_rejects_empty_subscription_write(self):
        """Provisioning reports a safe error when the subscription write returns no row."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(return_value=None)
        service.supabase.table.return_value = _query([])

        with pytest.raises(ValueError, match="Failed to assign organization plan"):
            await service.assign_plan_for_platform_admin(ORG_ID, PAID_VERSION_ID)

        service.credit_grant_service.grant_for_subscription.assert_not_awaited()

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
                    "entitlement_key": "max_agents",
                    "value": {"type": "integer", "value": 1},
                    "display_order": 1,
                    "entitlement_definitions": {
                        "display_name": "Maximum agents",
                        "description": "Agents available to the organization.",
                    },
                },
                {
                    "plan_version_id": str(FREE_VERSION_ID),
                    "entitlement_key": "included_credits_monthly",
                    "value": {"type": "integer", "value": 100},
                    "display_order": 0,
                    "entitlement_definitions": {
                        "display_name": "Included credits",
                        "description": "Credits granted each billing period.",
                    },
                },
            ]
        )
        service.supabase.table.side_effect = lambda name: {
            "plan_versions": versions,
            "plan_version_entitlements": entitlements,
        }[name]

        result = await service.list_available_plan_versions()

        assert [plan.id for plan in result] == [FREE_VERSION_ID, PAID_VERSION_ID]
        assert result[0].billing_mode is BillingMode.FREE
        assert result[0].tier_rank == 0
        assert result[1].tier_rank == 10
        assert result[0].stripe_price_id is None
        assert result[0].entitlements["included_credits_monthly"]["value"] == 100
        assert list(result[0].entitlements) == [
            "included_credits_monthly",
            "max_agents",
        ]
        assert (
            result[0].entitlement_metadata["included_credits_monthly"].display_name
            == "Included credits"
        )
        assert (
            result[0].entitlement_metadata["included_credits_monthly"].description
            == "Credits granted each billing period."
        )

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

    def test_legacy_tier_slug_repairs_default_catalog_rank(self):
        """Known legacy slugs still render in the intended tier order."""
        service = VersionedSubscriptionService()
        legacy_enterprise = {
            **_paid_version(),
            "plan_products": {
                "slug": "enterprise-plan-month",
                "display_name": "Enterprise Plan:Month",
                "description": "For enterprise teams",
                "sort_order": 10,
            },
        }

        result = service._to_customer_plan_version(legacy_enterprise, {})

        assert result.tier_rank == 30

    def test_customer_metadata_extraction_handles_embedded_relation_shapes(self):
        """Joined entitlement metadata remains safe across Supabase row shapes."""
        row = {
            "entitlement_key": "max_agents",
            "entitlement_definitions": [
                {
                    "display_name": "Maximum agents",
                    "description": "Voice agents available to the organization.",
                    "enforcement_handler": "internal.only",
                }
            ],
        }

        metadata = VersionedSubscriptionService._embedded_entitlement_definition(row)

        assert metadata == {
            "display_name": "Maximum agents",
            "description": "Voice agents available to the organization.",
        }
        assert (
            VersionedSubscriptionService._embedded_entitlement_definition(
                {"entitlement_key": "missing"}
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_free_activation_is_idempotent_for_same_active_version(self):
        """Refreshing onboarding retries a missing grant without a new subscription."""
        service = VersionedSubscriptionService()
        service._get_signup_plan_version = AsyncMock(return_value=_free_version())
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(FREE_VERSION_ID),
                "status": "active",
                "stripe_customer_id": None,
                "current_period_start": "2026-08-01T00:00:00+00:00",
                "current_period_end": "2026-09-01T00:00:00+00:00",
            }
        )

        result = await service.activate_free_plan(ORG_ID, FREE_VERSION_ID)

        assert result.created is False
        assert result.subscription.id == SUBSCRIPTION_ID
        service.credit_grant_service.grant_for_subscription.assert_awaited_once()
        grant = service.credit_grant_service.grant_for_subscription.await_args
        assert grant.kwargs["grant_reason"] == "activation"
        assert grant.kwargs["grant_key"] == (
            f"free-subscription:{SUBSCRIPTION_ID}:activation"
        )

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
                ),
                customer_email="owner@erp-cosmos.com",
            )

        assert result.session_id == "cs_versioned"
        assert stripe.create_customer.await_args.kwargs["email"] == (
            "owner@erp-cosmos.com"
        )
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
                ),
                customer_email="owner@erp-cosmos.com",
            )

    @pytest.mark.asyncio
    async def test_paid_checkout_reconciles_and_blocks_a_pending_transition(self):
        """An expired row cannot start a second checkout during a transition."""
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        service = VersionedSubscriptionService()
        service._get_signup_plan_version = AsyncMock(return_value=_paid_version())
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "status": "expired",
                "pending_plan_transition": {"transition_id": "transition_unpaid"},
                "metadata": {"billing_mode": "paid"},
            }
        )
        service.reconcile_pending_plan_transition = AsyncMock(return_value=False)

        with pytest.raises(PlanChangeInProgressError, match="still being processed"):
            await service.create_paid_checkout(
                VersionedSubscriptionCheckoutRequest(
                    organization_id=ORG_ID,
                    plan_version_id=PAID_VERSION_ID,
                    success_url="https://app.test/success",
                    cancel_url="https://app.test/cancel",
                ),
                customer_email="owner@example.com",
            )

        service.reconcile_pending_plan_transition.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_confirm_reconciles_pending_transition_before_preview(self):
        """Terminal subscriptions release their stale transition before preview."""
        service = VersionedSubscriptionService()
        terminal_subscription = {
            "id": str(SUBSCRIPTION_ID),
            "plan_version_id": str(PAID_VERSION_ID),
            "status": "expired",
            "pending_plan_transition": {"transition_id": "transition_unpaid"},
        }
        service._get_existing_subscription = AsyncMock(
            return_value=terminal_subscription
        )
        service.reconcile_pending_plan_transition = AsyncMock(return_value=True)
        service.preview_plan_change = AsyncMock()

        with pytest.raises(ValueError, match="does not have an active subscription"):
            await service.confirm_plan_change(
                PlanChangeConfirmRequest(
                    organization_id=ORG_ID,
                    transition_id=UUID("00000000-0000-0000-0000-000000000108"),
                    target_plan_version_id=UUID("00000000-0000-0000-0000-000000000107"),
                ),
                customer_email="owner@example.com",
            )

        service.reconcile_pending_plan_transition.assert_awaited_once()
        service.preview_plan_change.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_version_only_stripe_trial_maps_to_application_trial_status(self):
        """Stripe's trialing status maps to the platform's trial enum value."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service._get_existing_subscription = AsyncMock(return_value=None)
        service.credit_grant_service.grant_for_subscription = AsyncMock()
        row = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "subscription_plan_id": None,
            "plan_version_id": str(PAID_VERSION_ID),
            "stripe_subscription_id": "sub_trial",
            "stripe_customer_id": "cus_trial",
            "status": "trial",
            "current_period_start": "2026-09-01T00:00:00+00:00",
            "current_period_end": "2026-10-01T00:00:00+00:00",
            "metadata": {"billing_mode": "paid"},
        }
        query = _query([row])
        service.supabase.table.return_value = query
        stripe_subscription = {
            "id": "sub_trial",
            "customer": "cus_trial",
            "status": "trialing",
            "current_period_start": 1_788_220_800,
            "current_period_end": 1_790_812_800,
            "metadata": {"organization_id": str(ORG_ID)},
        }
        resolved_plan = SimpleNamespace(plan_version_id=PAID_VERSION_ID)

        result = await service.record_paid_subscription_from_stripe(
            ORG_ID, resolved_plan, stripe_subscription
        )

        assert result.status.value == "trial"
        assert query.insert.call_args.args[0]["status"] == "trial"


class TestStripePlanChanges:
    """Tests for Stripe-backed subscription plan transitions."""

    @pytest.mark.asyncio
    async def test_period_end_price_change_starts_target_phase_at_renewal(self):
        """A scheduled price change must join phases at the current period end."""
        service = StripeService()
        subscription = {
            "id": "sub_growth",
            "current_period_end": 1_800_000_000,
            "items": {
                "data": [
                    {
                        "id": "si_growth",
                        "price": {"id": "price_growth"},
                    }
                ]
            },
        }
        schedule = MagicMock()
        schedule.id = "sched_growth"
        schedule.get.side_effect = lambda key, default=None: {
            "phases": [
                {
                    "items": [{"price": {"id": "price_growth"}}],
                    "end_date": 1_800_000_000,
                }
            ]
        }.get(key, default)

        with patch("src.billing.stripe_service.stripe") as stripe:
            stripe.Subscription.retrieve.return_value = subscription
            stripe.SubscriptionSchedule.create.return_value = schedule

            await service.change_subscription_price(
                "sub_growth",
                "price_pro",
                at_period_end=True,
            )

        stripe.SubscriptionSchedule.modify.assert_called_once()
        phases = stripe.SubscriptionSchedule.modify.call_args.kwargs["phases"]
        assert phases[0]["end_date"] == 1_800_000_000
        assert phases[1]["start_date"] == 1_800_000_000
        assert phases[1]["items"][0]["price"] == "price_pro"

    @pytest.mark.asyncio
    async def test_plan_change_preview_uses_catalog_rank_for_timing(self):
        """A higher-ranked target is previewed as an immediate upgrade."""
        service = VersionedSubscriptionService()
        current = service._to_customer_plan_version(_paid_version(), {})
        target_row = {
            **_paid_version(),
            "id": str(UUID("00000000-0000-0000-0000-000000000107")),
            "plan_version_id": None,
            "price_amount_cents": 9900,
            "stripe_price_id": "price_pro",
            "plan_products": {
                "slug": "pro",
                "display_name": "Pro",
                "description": "For larger teams",
                "sort_order": 20,
            },
        }
        target = service._to_customer_plan_version(target_row, {})
        service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(PAID_VERSION_ID),
                "stripe_subscription_id": "sub_acme",
                "status": "active",
                "current_period_end": "2026-09-01T00:00:00+00:00",
            }
        )
        service._get_customer_plan_version = AsyncMock(side_effect=[current, target])

        result = await service.preview_plan_change(
            ORG_ID, UUID("00000000-0000-0000-0000-000000000107")
        )

        assert result.current_plan.tier_rank == 10
        assert result.target_plan.tier_rank == 20
        assert result.effective_mode.value == "immediate"
        assert result.proration_behavior == "create_prorations"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_interval", ["monthly", "annual"])
    async def test_confirm_plan_change_updates_local_version_after_stripe_success(
        self, target_interval
    ):
        """An immediate paid change updates local state only after Stripe succeeds."""
        service = VersionedSubscriptionService()
        current = service._to_customer_plan_version(_paid_version(), {})
        target_row = {
            **_paid_version(),
            "id": str(UUID("00000000-0000-0000-0000-000000000107")),
            "price_amount_cents": 9900,
            "billing_interval": target_interval,
            "stripe_price_id": "price_pro",
            "plan_products": {
                "slug": "pro",
                "display_name": "Pro",
                "description": "For larger teams",
                "sort_order": 20,
            },
        }
        target = service._to_customer_plan_version(target_row, {})
        existing = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "plan_version_id": str(PAID_VERSION_ID),
            "stripe_subscription_id": "sub_acme",
            "status": "active",
            "metadata": {"billing_mode": "paid"},
        }
        service._get_existing_subscription = AsyncMock(return_value=existing)
        service._get_customer_plan_version = AsyncMock(side_effect=[current, target])
        service.supabase = MagicMock()
        service.supabase.rpc.return_value.execute.return_value = _result(True)
        updates = _query([])
        service.supabase.table.return_value = updates

        with patch(
            "src.billing.versioned_subscription_service.stripe_service"
        ) as stripe:

            async def assert_interval_change_marker(*args, **kwargs):
                if target_interval == "annual":
                    rpc_name, rpc_args = service.supabase.rpc.call_args_list[0].args
                    assert rpc_name == "claim_subscription_plan_transition"
                    assert rpc_args["p_transition"]["billing_interval_changed"] is True

            stripe.change_subscription_price = AsyncMock(
                side_effect=assert_interval_change_marker
            )
            result = await service.confirm_plan_change(
                PlanChangeConfirmRequest(
                    organization_id=ORG_ID,
                    transition_id=UUID("00000000-0000-0000-0000-000000000108"),
                    target_plan_version_id=UUID("00000000-0000-0000-0000-000000000107"),
                ),
                customer_email="owner@example.com",
            )

        assert result.status == "applied"
        stripe.change_subscription_price.assert_awaited_once_with(
            "sub_acme",
            "price_pro",
            proration_behavior="create_prorations",
        )
        assert updates.update.call_args.args[0]["plan_version_id"] == str(
            UUID("00000000-0000-0000-0000-000000000107")
        )
        if target_interval == "annual":
            assert len(updates.update.call_args_list) == 1
            assert [call.args[0] for call in service.supabase.rpc.call_args_list] == [
                "claim_subscription_plan_transition"
            ]
        else:
            assert len(updates.update.call_args_list) == 1
            assert [call.args[0] for call in service.supabase.rpc.call_args_list] == [
                "claim_subscription_plan_transition",
                "clear_subscription_plan_transition",
            ]

    @pytest.mark.asyncio
    async def test_plan_change_is_blocked_until_interval_invoice_is_confirmed(self):
        """A follow-up action cannot replace the transition awaiting its invoice."""
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        service = VersionedSubscriptionService()
        current = service._to_customer_plan_version(_paid_version(), {})
        target = service._to_customer_plan_version(
            {
                **_paid_version(),
                "id": "00000000-0000-0000-0000-000000000107",
                "price_amount_cents": 9900,
                "stripe_price_id": "price_pro",
                "plan_products": {
                    "slug": "pro",
                    "display_name": "Pro",
                    "description": "For larger teams",
                    "sort_order": 20,
                },
            },
            {},
        )
        existing = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "plan_version_id": str(PAID_VERSION_ID),
            "stripe_subscription_id": "sub_acme",
            "status": "active",
            "metadata": {"billing_mode": "paid"},
            "pending_plan_transition": {
                "transition_id": "transition_waiting_for_invoice",
                "target_plan_version_id": str(target.id),
                "billing_interval_changed": True,
                "status": "awaiting_invoice",
            },
        }
        service._get_existing_subscription = AsyncMock(side_effect=[existing, existing])
        service._get_customer_plan_version = AsyncMock(side_effect=[current, target])
        service.supabase = MagicMock()

        with patch(
            "src.billing.versioned_subscription_service.stripe_service"
        ) as stripe:
            stripe.change_subscription_price = AsyncMock()
            with pytest.raises(
                PlanChangeInProgressError, match="still being processed"
            ):
                await service.confirm_plan_change(
                    PlanChangeConfirmRequest(
                        organization_id=ORG_ID,
                        transition_id=UUID("00000000-0000-0000-0000-000000000108"),
                        target_plan_version_id=target.id,
                    ),
                    customer_email="owner@example.com",
                )

        stripe.change_subscription_price.assert_not_awaited()
        service.supabase.rpc.assert_not_called()

    def test_plan_transition_release_is_guarded_by_transition_id(self):
        """A stale completion cannot clear a newer transition's lock."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.rpc.return_value.execute.return_value = _result(False)

        cleared = service.clear_plan_transition(
            SUBSCRIPTION_ID,
            UUID("00000000-0000-0000-0000-000000000108"),
        )

        assert cleared is False
        service.supabase.rpc.assert_called_once_with(
            "clear_subscription_plan_transition",
            {
                "p_subscription_id": str(SUBSCRIPTION_ID),
                "p_transition_id": "00000000-0000-0000-0000-000000000108",
            },
        )

    def test_competing_plan_transition_claim_fails_closed(self):
        """The database's atomic claim result blocks a concurrent Stripe call."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.rpc.return_value.execute.return_value = _result(False)
        transition = {
            "transition_id": "transition_competing",
            "target_plan_version_id": str(PAID_VERSION_ID),
            "billing_interval_changed": True,
            "status": "awaiting_invoice",
        }

        claimed = service.claim_plan_transition(SUBSCRIPTION_ID, transition)

        assert claimed is False
        service.supabase.rpc.assert_called_once_with(
            "claim_subscription_plan_transition",
            {
                "p_subscription_id": str(SUBSCRIPTION_ID),
                "p_transition": transition,
            },
        )

    @pytest.mark.asyncio
    async def test_reconcile_releases_transition_when_stripe_kept_source_price(self):
        """A failed Stripe request can be retried after source state is verified."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.rpc.return_value.execute.return_value = _result(True)
        subscription = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "stripe_subscription_id": "sub_acme",
            "metadata": {},
            "pending_plan_transition": {
                "transition_id": "transition_failed_before_mutation",
                "source_price_id": "price_source",
                "target_price_id": "price_target",
                "source_plan_version_id": str(PAID_VERSION_ID),
                "target_plan_version_id": "00000000-0000-0000-0000-000000000107",
                "billing_interval_changed": True,
                "effective_mode": "immediate",
            },
        }

        with patch(
            "src.billing.versioned_subscription_service.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value={
                "status": "active",
                "items": {"data": [{"price": {"id": "price_source"}}]},
            },
        ):
            reconciled = await service.reconcile_pending_plan_transition(subscription)

        assert reconciled is True
        service.supabase.rpc.assert_called_once_with(
            "clear_subscription_plan_transition",
            {
                "p_subscription_id": str(SUBSCRIPTION_ID),
                "p_transition_id": "transition_failed_before_mutation",
            },
        )

    @pytest.mark.asyncio
    async def test_reconcile_clears_unpaid_terminal_transition(self):
        """An unpaid Stripe subscription releases its lock and local marker."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.rpc.return_value.execute.return_value = _result(True)
        service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = _result(
            []
        )
        subscription = {
            "id": str(SUBSCRIPTION_ID),
            "stripe_subscription_id": "sub_acme",
            "metadata": {
                "billing_mode": "paid",
                "pending_plan_change": {
                    "transition_id": "transition_unpaid",
                    "status": "scheduled",
                },
            },
            "pending_plan_transition": {
                "transition_id": "transition_unpaid",
                "source_price_id": "price_source",
                "target_price_id": "price_target",
                "billing_interval_changed": True,
            },
        }

        with patch(
            "src.billing.versioned_subscription_service.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value={"status": "unpaid"},
        ):
            reconciled = await service.reconcile_pending_plan_transition(subscription)

        assert reconciled is True
        update_fields = service.supabase.table.return_value.update.call_args.args[0]
        assert update_fields["status"] == "expired"
        assert "pending_plan_change" not in update_fields["metadata"]
        service.supabase.rpc.assert_called_once_with(
            "clear_subscription_plan_transition",
            {
                "p_subscription_id": str(SUBSCRIPTION_ID),
                "p_transition_id": "transition_unpaid",
            },
        )

    @pytest.mark.asyncio
    async def test_reconcile_keeps_interval_transition_until_invoice_credit_grant(self):
        """An applied interval reset stays claimed until its invoice is granted."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = _result(
            []
        )
        subscription = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "stripe_subscription_id": "sub_acme",
            "metadata": {},
            "pending_plan_transition": {
                "transition_id": "transition_waiting_for_invoice",
                "source_price_id": "price_source",
                "target_price_id": "price_target",
                "source_plan_version_id": str(PAID_VERSION_ID),
                "target_plan_version_id": "00000000-0000-0000-0000-000000000107",
                "billing_interval_changed": True,
                "effective_mode": "immediate",
            },
        }

        with patch(
            "src.billing.versioned_subscription_service.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value={
                "status": "active",
                "items": {"data": [{"price": {"id": "price_target"}}]},
            },
        ):
            reconciled = await service.reconcile_pending_plan_transition(subscription)

        assert reconciled is False
        service.supabase.table.assert_called_once_with("organization_subscriptions")
        service.supabase.rpc.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_recovers_scheduled_change_and_preserves_schedule_marker(
        self,
    ):
        """A scheduled Stripe change is restored locally after a lost response."""
        service = VersionedSubscriptionService()
        service.supabase = MagicMock()
        service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = _result(
            []
        )
        service.supabase.rpc.return_value.execute.return_value = _result(True)
        subscription = {
            "id": str(SUBSCRIPTION_ID),
            "organization_id": str(ORG_ID),
            "stripe_subscription_id": "sub_acme",
            "metadata": {},
            "pending_plan_transition": {
                "transition_id": "transition_scheduled",
                "source_price_id": "price_source",
                "target_price_id": "price_target",
                "source_plan_version_id": str(PAID_VERSION_ID),
                "target_plan_version_id": "00000000-0000-0000-0000-000000000107",
                "billing_interval_changed": False,
                "effective_mode": "period_end",
                "effective_at": "2026-11-01T00:00:00+00:00",
            },
        }

        with (
            patch(
                "src.billing.versioned_subscription_service.stripe_service.get_subscription",
                new_callable=AsyncMock,
                return_value={
                    "status": "active",
                    "schedule": "sched_123",
                    "items": {"data": [{"price": {"id": "price_source"}}]},
                },
            ),
            patch(
                "src.billing.versioned_subscription_service.stripe_service.get_subscription_schedule",
                new_callable=AsyncMock,
                return_value={
                    "phases": [
                        {"items": [{"price": "price_source"}]},
                        {"items": [{"price": "price_target"}]},
                    ]
                },
            ),
        ):
            reconciled = await service.reconcile_pending_plan_transition(subscription)

        assert reconciled is False
        update = service.supabase.table.return_value.update.call_args.args[0]
        assert update["metadata"]["pending_plan_change"] == {
            "transition_id": "transition_scheduled",
            "target_plan_version_id": "00000000-0000-0000-0000-000000000107",
            "effective_at": "2026-11-01T00:00:00+00:00",
            "status": "scheduled",
        }
        service.supabase.rpc.assert_called_once_with(
            "clear_subscription_plan_transition",
            {
                "p_subscription_id": str(SUBSCRIPTION_ID),
                "p_transition_id": "transition_scheduled",
            },
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
        profile = MagicMock(email="owner@erp-cosmos.com")
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
        service.create_paid_checkout.assert_awaited_once_with(
            request, customer_email="owner@erp-cosmos.com"
        )

    @pytest.mark.asyncio
    async def test_paid_checkout_maps_pending_transition_to_conflict(self):
        """A duplicate checkout during plan transition returns HTTP 409."""
        from fastapi import HTTPException
        from src.billing.routes import create_versioned_subscription_checkout
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        request = VersionedSubscriptionCheckoutRequest(
            organization_id=ORG_ID,
            plan_version_id=PAID_VERSION_ID,
            success_url="https://app.test/onboarding/complete",
            cancel_url="https://app.test/onboarding/plan",
        )
        profile = MagicMock(email="owner@erp-cosmos.com")
        with (
            patch("src.billing.routes.assert_billing_access"),
            patch("src.billing.routes.versioned_subscription_service") as service,
        ):
            service.create_paid_checkout = AsyncMock(
                side_effect=PlanChangeInProgressError("plan change is processing")
            )
            with pytest.raises(HTTPException) as exc_info:
                await create_versioned_subscription_checkout(
                    request, (UUID(int=1), profile)
                )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "plan change is processing"

    @pytest.mark.asyncio
    async def test_plan_change_preview_requires_billing_access(self):
        """Plan previews cannot disclose billing details without org access."""
        from fastapi import HTTPException
        from src.billing.routes import preview_plan_change

        request = PlanChangePreviewRequest(
            organization_id=ORG_ID,
            target_plan_version_id=PAID_VERSION_ID,
        )
        with (
            patch(
                "src.billing.routes.assert_billing_access",
                side_effect=HTTPException(status_code=403, detail="forbidden"),
            ),
            patch("src.billing.routes.versioned_subscription_service") as service,
        ):
            service.preview_plan_change = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await preview_plan_change(request, (UUID(int=1), MagicMock()))

        assert exc_info.value.status_code == 403
        service.preview_plan_change.assert_not_called()

    @pytest.mark.asyncio
    async def test_plan_change_confirmation_passes_authenticated_email(self):
        """Confirmation uses the authenticated profile for Checkout identity."""
        from src.billing.routes import confirm_plan_change

        request = PlanChangeConfirmRequest(
            organization_id=ORG_ID,
            transition_id=UUID("00000000-0000-0000-0000-000000000108"),
            target_plan_version_id=PAID_VERSION_ID,
        )
        response = {"status": "scheduled", "target_plan_version_id": PAID_VERSION_ID}
        profile = MagicMock(email="owner@erp-cosmos.com")
        with (
            patch("src.billing.routes.assert_billing_access"),
            patch("src.billing.routes.versioned_subscription_service") as service,
        ):
            service.confirm_plan_change = AsyncMock(return_value=response)

            result = await confirm_plan_change(request, (UUID(int=1), profile))

        assert result == response
        service.confirm_plan_change.assert_awaited_once_with(
            request, customer_email="owner@erp-cosmos.com"
        )

    @pytest.mark.asyncio
    async def test_plan_change_conflict_returns_http_409(self):
        """A pending Stripe transition is surfaced as a retryable conflict."""
        from fastapi import HTTPException
        from src.billing.routes import confirm_plan_change
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        request = PlanChangeConfirmRequest(
            organization_id=ORG_ID,
            transition_id=UUID("00000000-0000-0000-0000-000000000108"),
            target_plan_version_id=PAID_VERSION_ID,
        )
        profile = MagicMock(email="owner@erp-cosmos.com")
        with (
            patch("src.billing.routes.assert_billing_access"),
            patch("src.billing.routes.versioned_subscription_service") as service,
        ):
            service.confirm_plan_change = AsyncMock(
                side_effect=PlanChangeInProgressError("transition is processing")
            )
            with pytest.raises(HTTPException) as exc_info:
                await confirm_plan_change(request, (UUID(int=1), profile))

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "transition is processing"
