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
    async def test_completed_checkout_activates_subscription_without_created_event(
        self, org_id, plan_version_id
    ):
        """Checkout completion itself persists the selected paid plan."""
        from src.billing.webhook_handler import handle_checkout_session_completed

        subscription = {
            "id": "sub_checkout_123",
            "customer": "cus_stripe_123",
            "status": "active",
            "metadata": {"organization_id": "stale-org"},
            "items": {"data": [{"price": {"id": "price_selected"}}]},
        }
        event = {
            "data": {
                "object": {
                    "id": "cs_completed",
                    "mode": "subscription",
                    "subscription": "sub_checkout_123",
                    "metadata": {
                        "organization_id": str(org_id),
                        "plan_version_id": str(plan_version_id),
                    },
                }
            }
        }

        with patch(
            "src.billing.webhook_handler.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value=subscription,
        ) as retrieve_subscription, patch(
            "src.billing.webhook_handler.handle_subscription_created",
            new_callable=AsyncMock,
        ) as activate_subscription:
            await handle_checkout_session_completed(event)

        retrieve_subscription.assert_awaited_once_with("sub_checkout_123")
        activated_event = activate_subscription.await_args.args[0]
        activated_subscription = activated_event["data"]["object"]
        assert activated_subscription["id"] == "sub_checkout_123"
        assert activated_subscription["metadata"]["organization_id"] == str(org_id)
        assert activated_subscription["metadata"]["plan_version_id"] == str(
            plan_version_id
        )

    @pytest.mark.asyncio
    async def test_completed_checkout_requires_organization_metadata(self):
        from src.billing.webhook_handler import handle_checkout_session_completed

        event = {
            "data": {
                "object": {
                    "id": "cs_completed",
                    "mode": "subscription",
                    "subscription": "sub_checkout_123",
                    "metadata": {},
                }
            }
        }

        with pytest.raises(ValueError, match="organization_id"):
            await handle_checkout_session_completed(event)

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
            assert mock_create.call_args.kwargs["grant_initial_credits"] is False

            update_kwargs = mock_update.call_args[0][1]
            assert update_kwargs.plan_version_id == plan_version_id
            assert update_kwargs.stripe_subscription_id == "sub_stripe_123"
            assert update_kwargs.stripe_customer_id == "cus_stripe_123"

    @pytest.mark.asyncio
    async def test_paid_checkout_replaces_free_billing_state_for_legacy_plan(
        self, org_id, plan_version_id, legacy_plan_id
    ):
        """Free-to-paid checkout persists the Stripe customer and paid state."""
        from src.billing.webhook_handler import handle_subscription_created

        event = _stripe_subscription_event(org_id, price_id="price_annual")
        event["data"]["object"]["items"]["data"][0]["price"] = {
            "id": "price_annual",
            "recurring": {"interval": "year"},
        }

        free_plan = MagicMock(included_credits=100, name="Free")
        existing_subscription = MagicMock(
            plan=free_plan,
            metadata={
                "activation_source": "onboarding",
                "billing_mode": "free",
                "credit_grant_policy": "recurring",
                "billing_interval": "monthly",
            },
        )
        paid_plan = MagicMock(id=legacy_plan_id, included_credits=2500, name="Starter")
        resolved = MagicMock(
            plan_version_id=plan_version_id,
            subscription_plan_id=legacy_plan_id,
            stripe_price_id="price_annual",
        )

        with patch(
            "src.billing.webhook_handler._resolve_plan_from_stripe_price",
            new_callable=AsyncMock,
            return_value=(resolved, paid_plan),
        ), patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=existing_subscription,
        ), patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_update:
            await handle_subscription_created(event)

        update = mock_update.await_args.args[1]
        assert update.stripe_subscription_id == "sub_stripe_123"
        assert update.stripe_customer_id == "cus_stripe_123"
        assert update.metadata["billing_mode"] == "paid"
        assert update.metadata["credit_grant_policy"] == "recurring"
        assert update.metadata["billing_interval"] == "annual"
        assert update.metadata["activation_source"] == "onboarding"
        assert update.metadata["organization_id"] == str(org_id)

    @pytest.mark.asyncio
    async def test_subscription_updated_marks_customer_and_paid_metadata(
        self, org_id, plan_version_id, legacy_plan_id
    ):
        """Subscription updates also repair older Free-to-paid rows."""
        from src.billing.webhook_handler import handle_subscription_updated

        event = _stripe_subscription_event(org_id, price_id="price_annual")
        event["data"]["object"]["items"]["data"][0]["price"] = {
            "id": "price_annual",
            "recurring": {"interval": "year"},
        }
        free_plan = MagicMock(id=uuid4(), included_credits=100, name="Free")
        current_sub = MagicMock(
            plan=free_plan,
            plan_version_id=uuid4(),
            metadata={"billing_mode": "free", "billing_interval": "monthly"},
        )
        paid_plan = MagicMock(id=legacy_plan_id, included_credits=2500, name="Starter")
        resolved = MagicMock(
            plan_version_id=plan_version_id,
            subscription_plan_id=legacy_plan_id,
            stripe_price_id="price_annual",
        )

        with patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=current_sub,
        ), patch(
            "src.billing.webhook_handler._resolve_plan_from_stripe_price",
            new_callable=AsyncMock,
            return_value=(resolved, paid_plan),
        ), patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_update:
            await handle_subscription_updated(event)

        update = mock_update.await_args.args[1]
        assert update.stripe_subscription_id == "sub_stripe_123"
        assert update.stripe_customer_id == "cus_stripe_123"
        assert update.metadata["billing_mode"] == "paid"
        assert update.metadata["billing_interval"] == "annual"
        assert update.plan_version_id == plan_version_id

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
    async def test_subscription_updated_binds_version_only_scheduled_plan_change(
        self, org_id
    ):
        """A Stripe schedule becoming effective updates version-only rows."""
        from src.billing.webhook_handler import handle_subscription_updated

        current_version_id = uuid4()
        target_version_id = uuid4()
        event = _stripe_subscription_event(org_id, price_id="price_scheduled_target")
        current_sub = MagicMock(
            plan=None,
            plan_version_id=current_version_id,
            subscription_plan_id=None,
            metadata={
                "billing_mode": "paid",
                "pending_plan_change": {
                    "transition_id": "scheduled_transition",
                    "target_plan_version_id": str(target_version_id),
                    "status": "scheduled",
                },
            },
            pending_plan_transition=None,
        )
        resolved = MagicMock(
            plan_version_id=target_version_id,
            subscription_plan_id=None,
            stripe_price_id="price_scheduled_target",
        )

        legacy_plan = MagicMock(id=None, included_credits=0)
        with patch(
            "src.billing.webhook_handler._resolve_plan_from_stripe_price",
            new_callable=AsyncMock,
            return_value=(resolved, legacy_plan),
        ), patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=current_sub,
        ), patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_update:
            await handle_subscription_updated(event)

        update_data = mock_update.await_args.args[1]
        assert update_data.plan_version_id == target_version_id
        assert update_data.subscription_plan_id is None
        assert update_data.cancel_at_period_end is False
        assert "pending_plan_change" not in update_data.metadata

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("target_billing_mode", "has_schedule", "cleared"),
        [
            (None, False, True),
            (None, True, False),
            ("paid", False, False),
            ("paid", True, False),
        ],
    )
    async def test_subscription_update_clears_free_marker_but_preserves_paid_schedule(
        self, org_id, target_billing_mode, has_schedule, cleared
    ):
        """The webhook clears legacy cancellation but keeps paid plan schedules."""
        from src.billing.webhook_handler import handle_subscription_updated

        current_version_id = uuid4()
        free_version_id = uuid4()
        event = _stripe_subscription_event(org_id, price_id="price_current")
        event["data"]["previous_attributes"] = {"cancel_at_period_end": True}
        if has_schedule:
            event["data"]["object"]["schedule"] = "sched_paid"
        pending_change = {
            "transition_id": "cancel_to_free",
            "target_plan_version_id": str(free_version_id),
            "status": "scheduled",
        }
        if target_billing_mode:
            pending_change["target_billing_mode"] = target_billing_mode
        current_sub = MagicMock(
            plan=None,
            plan_version_id=current_version_id,
            subscription_plan_id=None,
            metadata={
                "billing_mode": "paid",
                "pending_plan_change": pending_change,
            },
            pending_plan_transition=None,
        )
        resolved = MagicMock(
            plan_version_id=current_version_id,
            subscription_plan_id=None,
            stripe_price_id="price_current",
        )

        with patch(
            "src.billing.webhook_handler._resolve_plan_from_stripe_price",
            new_callable=AsyncMock,
            return_value=(resolved, None),
        ), patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=current_sub,
        ), patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as mock_update, patch(
            "src.billing.webhook_handler.versioned_subscription_service._get_customer_plan_version",
            new_callable=AsyncMock,
            side_effect=AssertionError("event history should resolve this marker"),
        ) as resolve_scheduled_target:
            await handle_subscription_updated(event)

        resolve_scheduled_target.assert_not_awaited()
        update_data = mock_update.await_args.args[1]
        assert update_data.cancel_at_period_end is False
        if cleared:
            assert "pending_plan_change" not in update_data.metadata
        else:
            assert update_data.metadata["pending_plan_change"] == pending_change

    @pytest.mark.asyncio
    async def test_deleted_subscription_releases_any_pending_transition(self, org_id):
        """A terminal Stripe cancellation releases the transition lock."""
        from src.billing.webhook_handler import handle_subscription_deleted

        subscription_id = uuid4()
        event = {
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": "sub_cancelled",
                    "customer": "cus_stripe_123",
                    "status": "canceled",
                    "canceled_at": int(datetime.now(timezone.utc).timestamp()),
                    "metadata": {"organization_id": str(org_id)},
                }
            },
        }
        local_subscription = MagicMock(
            id=subscription_id,
            pending_plan_transition={"transition_id": "transition_cancelled"},
            metadata={
                "billing_mode": "paid",
                "pending_plan_change": {
                    "transition_id": "transition_cancelled",
                    "status": "scheduled",
                },
            },
        )

        with patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as update_subscription, patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=local_subscription,
        ), patch(
            "src.billing.webhook_handler.versioned_subscription_service.clear_plan_transition",
            return_value=True,
        ) as clear_transition:
            await handle_subscription_deleted(event)

        clear_transition.assert_called_once_with(
            subscription_id, "transition_cancelled"
        )
        update_data = update_subscription.await_args.args[1]
        assert update_data.metadata == {"billing_mode": "paid"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        (
            "billing_reason",
            "interval_changed",
            "should_grant_credits",
            "local_binding_matches",
            "has_pending_transition",
        ),
        [
            ("subscription_cycle", False, True, True, False),
            ("subscription_update", False, False, True, False),
            ("subscription_update", False, False, True, True),
            ("subscription_update", True, True, True, True),
            ("subscription_update", True, True, False, True),
        ],
    )
    async def test_invoice_payment_grants_only_for_new_credit_period(
        self,
        org_id,
        plan_version_id,
        billing_reason,
        interval_changed,
        should_grant_credits,
        local_binding_matches,
        has_pending_transition,
    ):
        """Grant cycles and interval resets, but not same-period prorations."""
        from src.billing.webhook_handler import handle_invoice_payment_succeeded

        period_start = int(datetime.now(timezone.utc).timestamp())
        event = {
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": "in_renewal_123",
                    "customer": "cus_stripe_123",
                    "subscription": "sub_stripe_123",
                    "billing_reason": billing_reason,
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
            "current_period_start": period_start,
            "current_period_end": period_start + 86400,
        }
        pending_plan_transition = (
            {
                "transition_id": "transition_interval_change",
                "target_plan_version_id": str(plan_version_id),
                "billing_interval_changed": interval_changed,
                "status": "awaiting_invoice" if interval_changed else "applying",
            }
            if has_pending_transition
            else None
        )
        org_subscription = {
            "id": str(uuid4()),
            "organization_id": str(org_id),
            "plan_version_id": (
                str(plan_version_id) if local_binding_matches else str(uuid4())
            ),
            "stripe_subscription_id": "sub_stripe_123",
            "metadata": {},
            "pending_plan_transition": pending_plan_transition,
        }
        resolved_plan = MagicMock(
            plan_version_id=plan_version_id, subscription_plan_id=None
        )

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
            "src.billing.webhook_handler._resolve_plan_from_stripe_price",
            new_callable=AsyncMock,
            return_value=(resolved_plan, None),
        ), patch(
            "src.billing.webhook_handler.billing_service.get_subscription_plans",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.billing.webhook_handler.billing_service.update_organization_subscription",
            new_callable=AsyncMock,
        ) as update_subscription, patch(
            "src.billing.webhook_handler.credit_grant_service.grant_for_subscription",
            new_callable=AsyncMock,
        ) as grant, patch(
            "src.billing.webhook_handler.versioned_subscription_service.clear_plan_transition",
            return_value=True,
        ) as clear_transition:
            await handle_invoice_payment_succeeded(event)

        if should_grant_credits:
            grant.assert_awaited_once()
            assert grant.await_args.kwargs["grant_reason"] == "invoice_paid"
            expected_grant_key = (
                f"stripe-subscription-period:sub_stripe_123:{period_start}"
                if interval_changed
                else "stripe-invoice:in_renewal_123"
            )
            assert grant.await_args.kwargs["grant_key"] == expected_grant_key
        else:
            grant.assert_not_awaited()

        if interval_changed:
            clear_transition.assert_called_once_with(
                org_subscription["id"], "transition_interval_change"
            )
            if local_binding_matches:
                update_subscription.assert_not_awaited()
            else:
                update_subscription.assert_awaited_once()
                assert (
                    update_subscription.await_args.args[1].plan_version_id
                    == plan_version_id
                )
        else:
            update_subscription.assert_not_awaited()
            if has_pending_transition:
                clear_transition.assert_called_once_with(
                    org_subscription["id"], "transition_interval_change"
                )
            else:
                clear_transition.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_retries_until_local_subscription_is_persisted(self, org_id):
        """An early invoice event must not be acknowledged without its credit grant."""
        from src.billing.webhook_handler import handle_invoice_payment_succeeded

        event = {
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": "in_before_subscription_row",
                    "customer": "cus_stripe_123",
                    "subscription": "sub_stripe_123",
                    "amount_paid": 4900,
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

        with patch(
            "src.billing.webhook_handler.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value=stripe_subscription,
        ), patch(
            "src.billing.webhook_handler.billing_service.create_billing_history",
            new_callable=AsyncMock,
        ) as history, patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "src.billing.webhook_handler.billing_service.get_subscription_plans",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.billing.webhook_handler.credit_grant_service.grant_for_subscription",
            new_callable=AsyncMock,
        ) as grant:
            with pytest.raises(RuntimeError, match="not persisted"):
                await handle_invoice_payment_succeeded(event)

        history.assert_awaited_once()
        grant.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("local_stripe_subscription_id", "error_message"),
        [
            ("sub_old_free", "not synchronized"),
            ("sub_stripe_123", "not bound to the invoice plan"),
        ],
    )
    async def test_invoice_retries_until_local_paid_binding_matches_invoice(
        self,
        org_id,
        plan_version_id,
        local_stripe_subscription_id,
        error_message,
    ):
        """A stale Free row cannot receive a paid invoice's permanent grant."""
        from src.billing.webhook_handler import handle_invoice_payment_succeeded

        event = {
            "created": int(datetime.now(timezone.utc).timestamp()),
            "data": {
                "object": {
                    "id": "in_paid_before_free_row_updated",
                    "customer": "cus_stripe_123",
                    "subscription": "sub_stripe_123",
                    "amount_paid": 4900,
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
            "items": {"data": [{"price": {"id": "price_paid"}}]},
            "current_period_start": int(datetime.now(timezone.utc).timestamp()),
            "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 86400,
        }
        free_plan_version_id = uuid4()
        org_subscription = {
            "id": str(uuid4()),
            "organization_id": str(org_id),
            "subscription_plan_id": None,
            "plan_version_id": str(free_plan_version_id),
            "stripe_subscription_id": local_stripe_subscription_id,
        }
        resolved_plan = MagicMock(
            plan_version_id=plan_version_id, subscription_plan_id=None
        )

        with patch(
            "src.billing.webhook_handler.stripe_service.get_subscription",
            new_callable=AsyncMock,
            return_value=stripe_subscription,
        ), patch(
            "src.billing.webhook_handler.billing_service.create_billing_history",
            new_callable=AsyncMock,
        ) as history, patch(
            "src.billing.webhook_handler.billing_service.get_organization_subscription",
            new_callable=AsyncMock,
            return_value=org_subscription,
        ), patch(
            "src.billing.webhook_handler._resolve_plan_from_stripe_price",
            new_callable=AsyncMock,
            return_value=(resolved_plan, None),
        ) as resolve_plan, patch(
            "src.billing.webhook_handler.credit_grant_service.grant_for_subscription",
            new_callable=AsyncMock,
        ) as grant:
            with pytest.raises(RuntimeError, match=error_message):
                await handle_invoice_payment_succeeded(event)

        history.assert_awaited_once()
        grant.assert_not_awaited()
        if local_stripe_subscription_id == "sub_stripe_123":
            resolve_plan.assert_awaited_once_with("price_paid")
        else:
            resolve_plan.assert_not_awaited()
