"""
Stripe webhook event handler.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

import stripe

from shared.config import settings

from .credit_grant_service import credit_grant_service
from .models import (
    BillingHistoryCreate,
    BillingStatus,
    OrganizationSubscriptionUpdate,
    SubscriptionStatus,
    TransactionSource,
    TransactionType,
)
from .plan_version_models import BillingMode
from .plan_version_service import plan_version_service
from .service import billing_service
from .stripe_service import stripe_service
from .versioned_subscription_service import versioned_subscription_service

logger = logging.getLogger(__name__)


class InvalidStripeWebhook(Exception):
    """Raised when a webhook payload or signature fails Stripe verification."""


async def _resolve_plan_from_stripe_price(price_id: str):
    """Resolve plan version and legacy subscription plan from a Stripe price ID.

    Prefers ``plan_versions`` (immutable version binding). Falls back to legacy
    ``subscription_plans`` when no version row exists (pre-migration environments).

    Args:
        price_id: Stripe Price identifier.

    Returns:
        Tuple of (resolved_checkout_plan or None, legacy SubscriptionPlan or None).
        At least one element is non-None when a match exists.

    Raises:
        ValueError: When no plan matches the price ID.
    """
    try:
        resolved = await plan_version_service.resolve_checkout_plan(price_id)
        legacy_plan = None
        if resolved.subscription_plan_id:
            legacy_plan = await billing_service.get_subscription_plan(
                resolved.subscription_plan_id
            )
        return resolved, legacy_plan
    except ValueError:
        plans = await billing_service.get_subscription_plans(active_only=False)
        legacy_plan = next((p for p in plans if p.stripe_price_id == price_id), None)
        if not legacy_plan:
            raise ValueError(f"No plan found for price ID {price_id}")
        return None, legacy_plan


async def handle_stripe_webhook(payload: bytes, signature: str):
    """Process Stripe webhook events."""
    try:
        # Get webhook secret from settings
        webhook_secret = getattr(settings, "stripe_webhook_secret", None)
        if not webhook_secret:
            raise RuntimeError("Stripe webhook secret is not configured")

        # Construct and verify webhook event
        try:
            event = stripe_service.construct_webhook_event(
                payload, signature, webhook_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            raise InvalidStripeWebhook(
                "Invalid Stripe webhook signature or payload"
            ) from exc

        logger.info(f"Processing Stripe webhook event: {event['type']}")

        # Route event to appropriate handler
        if event["type"] == "checkout.session.completed":
            await handle_checkout_session_completed(event)
        elif event["type"] == "checkout.session.async_payment_succeeded":
            await handle_checkout_session_completed(event)
        elif event["type"] == "customer.subscription.created":
            await handle_subscription_created(event)
        elif event["type"] == "customer.subscription.updated":
            await handle_subscription_updated(event)
        elif event["type"] == "customer.subscription.deleted":
            await handle_subscription_deleted(event)
        elif event["type"] == "invoice.payment_succeeded":
            await handle_invoice_payment_succeeded(event)
        elif event["type"] == "invoice.payment_failed":
            await handle_invoice_payment_failed(event)
        elif event["type"] == "payment_intent.succeeded":
            await handle_payment_intent_succeeded(event)
        elif event["type"] == "payment_intent.payment_failed":
            await handle_payment_intent_failed(event)
        else:
            logger.info(f"Unhandled webhook event type: {event['type']}")

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise


async def handle_checkout_session_completed(event):
    """Handle successful checkout session completion."""
    try:
        session = event["data"]["object"]
        metadata = session.get("metadata", {})

        organization_id = metadata.get("organization_id")
        if not organization_id:
            raise ValueError("Checkout session is missing organization_id metadata")

        logger.info(f"Checkout session completed for organization {organization_id}")

        # Handle subscription checkout
        if session["mode"] == "subscription":
            subscription_id = session.get("subscription")
            if not subscription_id:
                raise ValueError("Completed subscription checkout has no subscription")
            if isinstance(subscription_id, dict):
                subscription = subscription_id
            else:
                subscription = await stripe_service.get_subscription(
                    str(subscription_id)
                )
            if hasattr(subscription, "to_dict_recursive"):
                subscription = subscription.to_dict_recursive()
            subscription["metadata"] = {
                **(subscription.get("metadata") or {}),
                **(metadata or {}),
            }
            # Do not rely on Stripe delivering a separate
            # customer.subscription.created event. The checkout completion event
            # is sufficient to persist the version-bound subscription; the
            # created event remains safe to replay and update the same row.
            await handle_subscription_created({"data": {"object": subscription}})

        # Handle one-time payment (credit purchase)
        elif session["mode"] == "payment":
            product_id = metadata.get("product_id")
            credit_amount = metadata.get("credit_amount")
            payment_intent_id = session.get("payment_intent")
            if isinstance(payment_intent_id, dict):
                payment_intent_id = payment_intent_id.get("id")

            if (
                session.get("payment_status") == "paid"
                and product_id
                and credit_amount
                and payment_intent_id
            ):
                # Add purchased credits
                await billing_service.add_purchased_credits(
                    organization_id=UUID(organization_id),
                    credits=int(credit_amount),
                    stripe_payment_intent_id=str(payment_intent_id),
                    description=f"Credit purchase - {credit_amount} credits",
                )

                logger.info(
                    f"Added {credit_amount} purchased credits to organization {organization_id}"
                )
            elif session.get("payment_status") != "paid":
                logger.info(
                    "Credit Checkout session %s is complete but payment is pending; "
                    "credits will be granted after payment succeeds",
                    session.get("id"),
                )

    except Exception as e:
        logger.error(f"Error handling checkout session completed: {e}")
        raise


async def handle_subscription_created(event):
    """Handle subscription creation."""
    try:
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]

        # Get organization_id from subscription metadata
        organization_id = subscription.get("metadata", {}).get("organization_id")

        if not organization_id:
            logger.warning(
                f"No organization_id in subscription {subscription['id']} metadata"
            )
            return

        # Resolve plan version + legacy plan from Stripe price ID
        price_id = subscription["items"]["data"][0]["price"]["id"]
        resolved, plan = await _resolve_plan_from_stripe_price(price_id)

        if not plan and resolved and resolved.subscription_plan_id:
            plan = await billing_service.get_subscription_plan(
                resolved.subscription_plan_id
            )

        if not plan and resolved and not resolved.subscription_plan_id:
            await versioned_subscription_service.record_paid_subscription_from_stripe(
                UUID(organization_id), resolved, subscription
            )
            logger.info(
                "Created version-bound subscription for organization %s",
                organization_id,
            )
            return

        if not plan:
            logger.warning(f"No plan found for price ID {price_id}")
            return

        plan_version_id = resolved.plan_version_id if resolved else None

        # Check if organization already has a subscription
        existing_subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        if existing_subscription:
            # Update existing subscription (plan upgrade/downgrade)
            logger.info(
                f"Updating existing subscription for organization {organization_id}"
            )

            # Check if this is a downgrade (new plan has fewer credits)
            current_plan_credits = (
                existing_subscription.plan.included_credits
                if existing_subscription.plan
                else 0
            )
            is_downgrade = plan.included_credits < current_plan_credits

            subscription_metadata = _paid_subscription_metadata(
                existing_subscription.metadata, subscription
            )
            scheduled_plan_change = (existing_subscription.metadata or {}).get(
                "pending_plan_change"
            ) or {}
            if scheduled_plan_change.get("status") == "scheduled" and str(
                scheduled_plan_change.get("target_plan_version_id")
            ) == str(plan_version_id):
                subscription_metadata.pop("pending_plan_change", None)

            update_data = OrganizationSubscriptionUpdate(
                subscription_plan_id=plan.id,
                plan_version_id=plan_version_id,
                stripe_subscription_id=subscription["id"],
                stripe_customer_id=customer_id,
                status=_map_stripe_status(subscription["status"]),
                metadata=subscription_metadata,
            )

            # Only set period dates if they exist
            if subscription.get("current_period_start"):
                update_data.current_period_start = datetime.fromtimestamp(
                    subscription["current_period_start"]
                )
            if subscription.get("current_period_end"):
                update_data.current_period_end = datetime.fromtimestamp(
                    subscription["current_period_end"]
                )

            if subscription.get("trial_start"):
                update_data.trial_start = datetime.fromtimestamp(
                    subscription["trial_start"]
                )
            if subscription.get("trial_end"):
                update_data.trial_end = datetime.fromtimestamp(
                    subscription["trial_end"]
                )

            # For downgrades, set cancel_at_period_end to give user grace period
            if is_downgrade:
                update_data.cancel_at_period_end = True
                logger.info(
                    f"Downgrade detected for organization {organization_id} - setting cancel_at_period_end"
                )

            await billing_service.update_organization_subscription(
                UUID(organization_id), update_data
            )
            if isinstance(
                getattr(existing_subscription, "pending_plan_transition", None), dict
            ):
                await versioned_subscription_service.reconcile_pending_plan_transition(
                    existing_subscription.model_dump(mode="json")
                )

            if is_downgrade:
                logger.info(
                    f"Downgraded subscription for organization {organization_id} to plan {plan.id} (will cancel at period end)"
                )
            else:
                logger.info(
                    f"Updated subscription for organization {organization_id} to plan {plan.id}"
                )
        else:
            # Create new organization subscription
            logger.info(f"Creating new subscription for organization {organization_id}")

            from .models import OrganizationSubscriptionCreate

            subscription_data = OrganizationSubscriptionCreate(
                organization_id=UUID(organization_id),
                subscription_plan_id=plan.id,
                stripe_customer_id=customer_id,
            )

            org_subscription = await billing_service.create_organization_subscription(
                subscription_data, grant_initial_credits=False
            )

            # Update with Stripe subscription details
            update_data = OrganizationSubscriptionUpdate(
                stripe_subscription_id=subscription["id"],
                stripe_customer_id=customer_id,
                status=_map_stripe_status(subscription["status"]),
                plan_version_id=plan_version_id,
                metadata=_paid_subscription_metadata(None, subscription),
            )

            # Only set period dates if they exist
            if subscription.get("current_period_start"):
                update_data.current_period_start = datetime.fromtimestamp(
                    subscription["current_period_start"]
                )
            if subscription.get("current_period_end"):
                update_data.current_period_end = datetime.fromtimestamp(
                    subscription["current_period_end"]
                )

            if subscription.get("trial_start"):
                update_data.trial_start = datetime.fromtimestamp(
                    subscription["trial_start"]
                )
            if subscription.get("trial_end"):
                update_data.trial_end = datetime.fromtimestamp(
                    subscription["trial_end"]
                )

            await billing_service.update_organization_subscription(
                UUID(organization_id), update_data
            )

            logger.info(f"Created subscription for organization {organization_id}")

    except Exception as e:
        logger.error(f"Error handling subscription created: {e}")
        raise


async def handle_subscription_updated(event):
    """Handle subscription updates."""
    try:
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]

        # Get organization_id from subscription metadata
        organization_id = subscription.get("metadata", {}).get("organization_id")

        if not organization_id:
            logger.warning(
                f"No organization_id in subscription {subscription['id']} metadata"
            )
            return

        # Get current subscription to check for plan changes
        current_subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        # Check whether Stripe has moved this subscription to a different
        # immutable plan version. A versioned plan may not have a legacy
        # subscription_plans row, so comparing legacy plan IDs alone can miss
        # the change and leave invoice validation bound to the previous plan.
        plan_changed = False
        is_downgrade = False
        price_id = subscription["items"]["data"][0]["price"]["id"]
        resolved = None
        new_plan = None

        if current_subscription:
            try:
                resolved, new_plan = await _resolve_plan_from_stripe_price(price_id)
            except ValueError:
                logger.warning(f"No plan found for price ID {price_id}")
                new_plan = None

            current_plan = getattr(current_subscription, "plan", None)
            if resolved:
                current_version_id = getattr(
                    current_subscription, "plan_version_id", None
                )
                plan_changed = str(current_version_id) != str(resolved.plan_version_id)
                target_plan_label = (
                    new_plan.name if new_plan else str(resolved.plan_version_id)
                )
            else:
                # Compatibility for subscriptions and prices that still use
                # the legacy subscription_plans catalog.
                compare_plan_id = getattr(new_plan, "id", None)
                current_plan_id = getattr(current_plan, "id", None) or getattr(
                    current_subscription, "subscription_plan_id", None
                )
                plan_changed = bool(
                    compare_plan_id
                    and current_plan_id
                    and str(compare_plan_id) != str(current_plan_id)
                )
                target_plan_label = (
                    new_plan.name if new_plan else str(compare_plan_id or "unknown")
                )

            if plan_changed:
                if new_plan and current_plan:
                    is_downgrade = (
                        new_plan.included_credits < current_plan.included_credits
                    )
                logger.info(
                    "Plan change detected for organization %s: %s -> %s",
                    organization_id,
                    getattr(current_plan, "name", "unknown"),
                    target_plan_label,
                )

        # Update subscription details
        subscription_metadata = _paid_subscription_metadata(
            current_subscription.metadata if current_subscription else None,
            subscription,
        )
        scheduled_plan_change = subscription_metadata.get("pending_plan_change") or {}
        if scheduled_plan_change.get("status") == "scheduled":
            scheduled_target_is_active = bool(
                resolved
                and str(scheduled_plan_change.get("target_plan_version_id"))
                == str(resolved.plan_version_id)
            )
            previous_attributes = (event.get("data") or {}).get(
                "previous_attributes"
            ) or {}
            target_billing_mode = scheduled_plan_change.get("target_billing_mode")
            subscription_has_schedule = bool(subscription.get("schedule"))
            cancellation_was_reactivated = bool(
                previous_attributes.get("cancel_at_period_end") is True
                and not subscription.get("cancel_at_period_end", False)
                and target_billing_mode != BillingMode.PAID.value
                and not subscription_has_schedule
            )
            if (
                not subscription.get("cancel_at_period_end", False)
                and not cancellation_was_reactivated
            ):
                target_version_id = scheduled_plan_change.get("target_plan_version_id")
                if (
                    target_billing_mode is None
                    and target_version_id
                    and not subscription_has_schedule
                ):
                    try:
                        scheduled_target = await versioned_subscription_service._get_customer_plan_version(
                            UUID(str(target_version_id)),
                            require_current_for_signup=False,
                        )
                        target_billing_mode = scheduled_target.billing_mode.value
                    except Exception:
                        logger.exception(
                            "Could not resolve scheduled plan mode for subscription %s",
                            subscription["id"],
                        )
                cancellation_was_reactivated = (
                    target_billing_mode == BillingMode.FREE.value
                    and not subscription_has_schedule
                )

            if scheduled_target_is_active or cancellation_was_reactivated:
                subscription_metadata.pop("pending_plan_change", None)

        update_data = OrganizationSubscriptionUpdate(
            status=_map_stripe_status(subscription["status"]),
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            stripe_subscription_id=subscription["id"],
            stripe_customer_id=customer_id,
            metadata=subscription_metadata,
        )

        if plan_changed and resolved:
            update_data.plan_version_id = resolved.plan_version_id
            if resolved.subscription_plan_id:
                update_data.subscription_plan_id = resolved.subscription_plan_id
            elif new_plan:
                update_data.subscription_plan_id = new_plan.id

        # Only set period dates if they exist
        if subscription.get("current_period_start"):
            update_data.current_period_start = datetime.fromtimestamp(
                subscription["current_period_start"]
            )
        if subscription.get("current_period_end"):
            update_data.current_period_end = datetime.fromtimestamp(
                subscription["current_period_end"]
            )

        if subscription.get("canceled_at"):
            update_data.cancelled_at = datetime.fromtimestamp(
                subscription["canceled_at"]
            )

        await billing_service.update_organization_subscription(
            UUID(organization_id), update_data
        )
        pending_transition = getattr(
            current_subscription, "pending_plan_transition", None
        )
        if isinstance(pending_transition, dict):
            await versioned_subscription_service.reconcile_pending_plan_transition(
                current_subscription.model_dump(mode="json")
            )

        if plan_changed:
            if is_downgrade:
                logger.info(
                    f"Downgrade processed for organization {organization_id} - subscription will cancel at period end"
                )
            else:
                logger.info(f"Upgrade processed for organization {organization_id}")
        else:
            logger.info(f"Updated subscription for organization {organization_id}")

    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")
        raise


async def handle_subscription_deleted(event):
    """Handle subscription deletion/cancellation."""
    try:
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]

        # Get organization_id from subscription metadata
        organization_id = subscription.get("metadata", {}).get("organization_id")

        if not organization_id:
            logger.warning(
                f"No organization_id in subscription {subscription['id']} metadata"
            )
            return

        local_subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )
        local_metadata = getattr(local_subscription, "metadata", None)
        metadata = dict(local_metadata) if isinstance(local_metadata, dict) else {}
        metadata.pop("pending_plan_change", None)

        # Update subscription status to cancelled and discard any schedule that
        # Stripe has now finalized by deleting the subscription.
        update_data = OrganizationSubscriptionUpdate(
            status=SubscriptionStatus.CANCELLED,
            cancelled_at=datetime.fromtimestamp(
                subscription.get("canceled_at", event["created"])
            ),
            metadata=metadata,
        )

        await billing_service.update_organization_subscription(
            UUID(organization_id), update_data
        )

        if local_subscription and local_subscription.pending_plan_transition:
            pending_transition = local_subscription.pending_plan_transition
            versioned_subscription_service.clear_plan_transition(
                local_subscription.id, pending_transition.get("transition_id", "")
            )

        logger.info(f"Cancelled subscription for organization {organization_id}")

    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")
        raise


async def handle_invoice_payment_succeeded(event):
    """Handle successful invoice payment."""
    try:
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]

        # Get organization_id from subscription metadata if it's a subscription invoice
        organization_id = None
        subscription = None
        if invoice.get("subscription"):
            subscription = await stripe_service.get_subscription(
                invoice["subscription"]
            )
            organization_id = subscription.get("metadata", {}).get("organization_id")

        # Fallback to customer metadata
        if not organization_id:
            customer = await stripe_service.get_customer(customer_id)
            organization_id = customer.metadata.get("organization_id")

        if not organization_id:
            logger.warning(f"No organization_id found for invoice {invoice['id']}")
            return

        # Create billing history entry
        billing_data = BillingHistoryCreate(
            organization_id=UUID(organization_id),
            stripe_invoice_id=invoice["id"],
            stripe_payment_intent_id=invoice.get("payment_intent"),
            amount=invoice["amount_paid"],
            currency=invoice["currency"],
            status=BillingStatus.PAID,
            description=f"Invoice payment - {invoice.get('description', 'Subscription')}",
            invoice_url=invoice.get("hosted_invoice_url"),
            receipt_url=invoice.get("receipt_url"),
            billing_reason=invoice.get("billing_reason"),
            paid_at=datetime.fromtimestamp(
                invoice.get("status_transitions", {}).get("paid_at", event["created"])
            ),
        )

        await billing_service.create_billing_history(billing_data)

        # If this is a subscription invoice, allocate credits through the
        # shared policy-aware grant service. Stripe may retry this event, so
        # each grant uses a stable key.
        if invoice.get("subscription"):
            price_id = subscription["items"]["data"][0]["price"]["id"]
            org_subscription = await billing_service.get_organization_subscription(
                UUID(organization_id)
            )
            if not org_subscription:
                # Stripe may deliver invoice.paid before checkout completion or
                # subscription.created. Keep this event retryable until the
                # local version-bound subscription exists; history upsert is
                # safe to repeat on that retry.
                raise RuntimeError(
                    f"Subscription {invoice['subscription']} is not persisted for invoice {invoice['id']} yet"
                )

            grant_subscription = (
                org_subscription.model_dump(mode="json")
                if hasattr(org_subscription, "model_dump")
                else dict(org_subscription)
            )
            if (
                grant_subscription.get("stripe_subscription_id")
                != invoice["subscription"]
            ):
                raise RuntimeError(
                    f"Subscription {invoice['subscription']} is not synchronized "
                    f"for invoice {invoice['id']} yet"
                )

            resolved_plan, legacy_plan = await _resolve_plan_from_stripe_price(price_id)
            pending_transition = grant_subscription.get("pending_plan_transition") or {}
            interval_reset_invoice = (
                invoice.get("billing_reason") == "subscription_update"
                and pending_transition.get("billing_interval_changed") is True
                and str(pending_transition.get("target_plan_version_id"))
                == str(resolved_plan.plan_version_id if resolved_plan else None)
            )
            local_plan_version_id = grant_subscription.get("plan_version_id")
            if local_plan_version_id:
                if resolved_plan is None or str(local_plan_version_id) != str(
                    resolved_plan.plan_version_id
                ):
                    if interval_reset_invoice and resolved_plan is not None:
                        # This invoice is the durable signal that the claimed
                        # interval change reached Stripe. Repair local binding
                        # before granting the target period's allowance.
                        await billing_service.update_organization_subscription(
                            UUID(organization_id),
                            OrganizationSubscriptionUpdate(
                                plan_version_id=resolved_plan.plan_version_id
                            ),
                        )
                        grant_subscription["plan_version_id"] = str(
                            resolved_plan.plan_version_id
                        )
                    else:
                        raise RuntimeError(
                            f"Subscription {invoice['subscription']} is not bound to "
                            f"the invoice plan for invoice {invoice['id']} yet"
                        )
            elif resolved_plan is not None:
                expected_legacy_plan_id = resolved_plan.subscription_plan_id
                local_legacy_plan_id = grant_subscription.get("subscription_plan_id")
                if (
                    expected_legacy_plan_id is None
                    or str(local_legacy_plan_id) != str(expected_legacy_plan_id)
                    or legacy_plan is None
                ):
                    raise RuntimeError(
                        f"Subscription {invoice['subscription']} is not bound to "
                        f"the invoice plan for invoice {invoice['id']} yet"
                    )
            elif legacy_plan is None or str(
                grant_subscription.get("subscription_plan_id")
            ) != str(legacy_plan.id):
                raise RuntimeError(
                    f"Subscription {invoice['subscription']} is not bound to "
                    f"the invoice plan for invoice {invoice['id']} yet"
                )

            period_start = datetime.fromtimestamp(
                subscription.get("current_period_start", event["created"]),
                tz=timezone.utc,
            )
            period_end = (
                datetime.fromtimestamp(
                    subscription["current_period_end"], tz=timezone.utc
                )
                if subscription.get("current_period_end")
                else None
            )
            if (
                invoice.get("billing_reason") == "subscription_update"
                and not interval_reset_invoice
            ):
                # An immediate plan upgrade may create a proration invoice.
                # It does not start a new credit period: the new plan's full
                # allowance is granted on the next subscription-cycle invoice.
                logger.info(
                    "Recorded plan-change invoice %s without renewing included credits",
                    invoice["id"],
                )
                if (
                    pending_transition.get("transition_id")
                    and pending_transition.get("billing_interval_changed") is not True
                    and str(pending_transition.get("target_plan_version_id"))
                    == str(resolved_plan.plan_version_id if resolved_plan else None)
                ):
                    # A paid same-period proration confirms its in-flight plan
                    # update, but does not renew the included credit balance.
                    versioned_subscription_service.clear_plan_transition(
                        org_subscription["id"], pending_transition["transition_id"]
                    )
            else:
                period_start_timestamp = int(
                    subscription.get("current_period_start", event["created"])
                )
                grant_key = (
                    f"stripe-subscription-period:{invoice['subscription']}:{period_start_timestamp}"
                    if interval_reset_invoice
                    else f"stripe-invoice:{invoice['id']}"
                )
                await credit_grant_service.grant_for_subscription(
                    grant_subscription,
                    grant_reason="invoice_paid",
                    period_start=period_start,
                    period_end=period_end,
                    grant_key=grant_key,
                    fallback_credits=(
                        legacy_plan.included_credits if legacy_plan else 0
                    ),
                )
                if interval_reset_invoice:
                    # Retain retry safety: if this metadata update fails, the
                    # stable subscription-period grant key makes the retry a
                    # no-op before the transition-ID compare-and-set succeeds.
                    cleared = versioned_subscription_service.clear_plan_transition(
                        org_subscription["id"], pending_transition["transition_id"]
                    )
                    if not cleared:
                        logger.warning(
                            "Interval-change transition %s was already cleared or "
                            "replaced after invoice %s credit grant",
                            pending_transition.get("transition_id"),
                            invoice["id"],
                        )

        logger.info(
            f"Processed successful invoice payment for organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Error handling invoice payment succeeded: {e}")
        raise


async def handle_invoice_payment_failed(event):
    """Handle failed invoice payment."""
    try:
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]

        # Get organization_id from subscription metadata if it's a subscription invoice
        organization_id = None
        if invoice.get("subscription"):
            subscription = await stripe_service.get_subscription(
                invoice["subscription"]
            )
            organization_id = subscription.get("metadata", {}).get("organization_id")

        # Fallback to customer metadata
        if not organization_id:
            customer = await stripe_service.get_customer(customer_id)
            organization_id = customer.metadata.get("organization_id")

        if not organization_id:
            logger.warning(f"No organization_id found for invoice {invoice['id']}")
            return

        # Create billing history entry
        billing_data = BillingHistoryCreate(
            organization_id=UUID(organization_id),
            stripe_invoice_id=invoice["id"],
            stripe_payment_intent_id=invoice.get("payment_intent"),
            amount=invoice["amount_due"],
            currency=invoice["currency"],
            status=BillingStatus.FAILED,
            description=f"Failed invoice payment - {invoice.get('description', 'Subscription')}",
            invoice_url=invoice.get("hosted_invoice_url"),
            billing_reason=invoice.get("billing_reason"),
        )

        await billing_service.create_billing_history(billing_data)

        # Update subscription status if applicable
        if invoice.get("subscription"):
            update_data = OrganizationSubscriptionUpdate(
                status=SubscriptionStatus.PAST_DUE
            )

            await billing_service.update_organization_subscription(
                UUID(organization_id), update_data
            )

        logger.info(
            f"Processed failed invoice payment for organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Error handling invoice payment failed: {e}")
        raise


async def handle_payment_intent_succeeded(event):
    """Handle successful payment intent (one-time payments)."""
    try:
        payment_intent = event["data"]["object"]
        customer_id = payment_intent.get("customer")

        if not customer_id:
            logger.warning("No customer ID in payment intent")
            return

        # Get organization_id from payment_intent metadata
        organization_id = payment_intent.get("metadata", {}).get("organization_id")

        # Fallback to customer metadata
        if not organization_id:
            customer = await stripe_service.get_customer(customer_id)
            organization_id = customer.metadata.get("organization_id")

        if not organization_id:
            logger.warning(
                f"No organization_id found for payment intent {payment_intent['id']}"
            )
            return

        # Create billing history entry for one-time payment
        billing_data = BillingHistoryCreate(
            organization_id=UUID(organization_id),
            stripe_payment_intent_id=payment_intent["id"],
            amount=payment_intent["amount"],
            currency=payment_intent["currency"],
            status=BillingStatus.PAID,
            description=f"One-time payment - {payment_intent.get('description', 'Credit purchase')}",
            receipt_url=payment_intent.get("receipt_url"),
            billing_reason="manual",
            paid_at=datetime.fromtimestamp(payment_intent.get("created")),
        )

        await billing_service.create_billing_history(billing_data)

        # Credit purchase metadata is attached to both the Checkout Session
        # and its PaymentIntent. The PaymentIntent event is the settled-payment
        # signal for delayed methods; the grant RPC is idempotent when Stripe
        # also delivers a paid Checkout Session event.
        metadata = payment_intent.get("metadata") or {}
        credit_amount = metadata.get("credit_amount")
        if metadata.get("type") == "credits" and credit_amount:
            await billing_service.add_purchased_credits(
                organization_id=UUID(organization_id),
                credits=int(credit_amount),
                stripe_payment_intent_id=payment_intent["id"],
                description=f"Credit purchase - {credit_amount} credits",
            )

        logger.info(
            f"Processed successful payment intent for organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Error handling payment intent succeeded: {e}")
        raise


async def handle_payment_intent_failed(event):
    """Handle failed payment intent."""
    try:
        payment_intent = event["data"]["object"]
        customer_id = payment_intent.get("customer")

        if not customer_id:
            logger.warning("No customer ID in payment intent")
            return

        # Get organization_id from payment_intent metadata
        organization_id = payment_intent.get("metadata", {}).get("organization_id")

        # Fallback to customer metadata
        if not organization_id:
            customer = await stripe_service.get_customer(customer_id)
            organization_id = customer.metadata.get("organization_id")

        if not organization_id:
            logger.warning(
                f"No organization_id found for payment intent {payment_intent['id']}"
            )
            return

        # Create billing history entry for failed payment
        billing_data = BillingHistoryCreate(
            organization_id=UUID(organization_id),
            stripe_payment_intent_id=payment_intent["id"],
            amount=payment_intent["amount"],
            currency=payment_intent["currency"],
            status=BillingStatus.FAILED,
            description=f"Failed payment - {payment_intent.get('description', 'Credit purchase')}",
            billing_reason="manual",
        )

        await billing_service.create_billing_history(billing_data)

        logger.info(
            f"Processed failed payment intent for organization {organization_id}"
        )

    except Exception as e:
        logger.error(f"Error handling payment intent failed: {e}")
        raise


def _map_stripe_status(stripe_status: str) -> SubscriptionStatus:
    """Map Stripe subscription status to our enum."""
    status_mapping = {
        "trialing": SubscriptionStatus.TRIAL,
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELLED,
        "unpaid": SubscriptionStatus.EXPIRED,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
    }

    return status_mapping.get(stripe_status, SubscriptionStatus.ACTIVE)


def _paid_subscription_metadata(
    existing_metadata: dict | None, subscription: dict
) -> dict:
    """Build canonical local billing metadata from a Stripe subscription."""
    metadata = {
        **(existing_metadata or {}),
        **(subscription.get("metadata") or {}),
    }
    items = (subscription.get("items") or {}).get("data") or []
    price = (items[0].get("price") or {}) if items else {}
    stripe_interval = (price.get("recurring") or {}).get("interval")
    billing_interval = {"month": "monthly", "year": "annual"}.get(stripe_interval)
    if billing_interval is None:
        current_interval = metadata.get("billing_interval")
        billing_interval = (
            current_interval if current_interval in {"monthly", "annual"} else "monthly"
        )

    # Stripe's existence is authoritative: never retain stale Free metadata
    # when a paid Checkout replaces a free subscription record.
    metadata.update(
        {
            "billing_mode": "paid",
            "credit_grant_policy": "recurring",
            "billing_interval": billing_interval,
        }
    )
    return metadata
