"""
Core billing service for subscription and credit management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from shared.config import settings, supabase_config

from .credit_entitlement_service import (
    CreditEntitlementService,
    credit_entitlement_service,
)
from .models import (
    AdminCreditGrantResponse,
    BillingHistory,
    BillingHistoryCreate,
    CreditBalance,
    CreditConsumptionRequest,
    CreditConsumptionResponse,
    CreditEvent,
    CreditProduct,
    CreditTransaction,
    CreditTransactionCreate,
    CreditTransactionsResponse,
    CreditTransactionWithEvent,
    CreditUsageCategory,
    CreditUsageResponse,
    OrganizationBillingSummary,
    OrganizationSubscription,
    OrganizationSubscriptionCreate,
    OrganizationSubscriptionUpdate,
    OrganizationSubscriptionWithPlan,
    SubscriptionPlan,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionStatus,
    TransactionSource,
    TransactionSourceMapping,
    TransactionType,
)
from .stripe_service import stripe_service

logger = logging.getLogger(__name__)


class BillingService:
    """Service for managing billing, subscriptions, and credits."""

    def __init__(self):
        """Initialize billing service."""
        self.supabase = supabase_config.client

    # Subscription Plan Management
    async def create_subscription_plan(
        self, plan_data: SubscriptionPlanCreate
    ) -> SubscriptionPlan:
        """Create a new subscription plan."""
        try:
            result = (
                self.supabase.table("subscription_plans")
                .insert(plan_data.model_dump())
                .execute()
            )

            if result.data:
                logger.info(f"Created subscription plan: {result.data[0]['id']}")
                return SubscriptionPlan(**result.data[0])

            raise Exception("Failed to create subscription plan")

        except Exception as e:
            logger.error(f"Error creating subscription plan: {e}")
            raise

    async def get_subscription_plans(
        self, active_only: bool = True
    ) -> list[SubscriptionPlan]:
        """Get all subscription plans."""
        try:
            query = self.supabase.table("subscription_plans").select("*")

            if active_only:
                query = query.eq("is_active", True)

            result = query.execute()

            return [SubscriptionPlan(**plan) for plan in result.data]

        except Exception as e:
            logger.error(f"Error fetching subscription plans: {e}")
            raise

    async def get_subscription_plan(self, plan_id: UUID) -> Optional[SubscriptionPlan]:
        """Get a subscription plan by ID."""
        try:
            result = (
                self.supabase.table("subscription_plans")
                .select("*")
                .eq("id", str(plan_id))
                .execute()
            )

            if result.data:
                return SubscriptionPlan(**result.data[0])

            return None

        except Exception as e:
            logger.error(f"Error fetching subscription plan {plan_id}: {e}")
            raise

    async def update_subscription_plan(
        self, plan_id: UUID, plan_data: SubscriptionPlanUpdate
    ) -> Optional[SubscriptionPlan]:
        """Update a subscription plan."""
        try:
            update_data = {
                k: v for k, v in plan_data.model_dump().items() if v is not None
            }
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = (
                self.supabase.table("subscription_plans")
                .update(update_data)
                .eq("id", str(plan_id))
                .execute()
            )

            if result.data:
                return SubscriptionPlan(**result.data[0])

            return None

        except Exception as e:
            logger.error(f"Error updating subscription plan {plan_id}: {e}")
            raise

    # Organization Subscription Management
    async def create_organization_subscription(
        self, subscription_data: OrganizationSubscriptionCreate
    ) -> OrganizationSubscription:
        """Create an organization subscription."""
        try:
            # Get the subscription plan
            plan = await self.get_subscription_plan(
                subscription_data.subscription_plan_id
            )
            if not plan:
                raise ValueError(
                    f"Subscription plan {subscription_data.subscription_plan_id} not found"
                )

            # Create Stripe customer if not provided
            stripe_customer_id = subscription_data.stripe_customer_id
            if not stripe_customer_id:
                # Get organization details for customer creation
                org_result = (
                    self.supabase.table("organizations")
                    .select("*")
                    .eq("id", str(subscription_data.organization_id))
                    .execute()
                )

                if not org_result.data:
                    raise ValueError(
                        f"Organization {subscription_data.organization_id} not found"
                    )

                org = org_result.data[0]

                # Create Stripe customer
                customer = await stripe_service.create_customer(
                    email=f"billing@{org['slug']}.example.com",  # Replace with actual email
                    name=org["name"],
                    organization_id=str(subscription_data.organization_id),
                )
                stripe_customer_id = customer.id

            # Prepare subscription data
            sub_data = {
                "organization_id": str(subscription_data.organization_id),
                "subscription_plan_id": str(subscription_data.subscription_plan_id),
                "stripe_customer_id": stripe_customer_id,
                "status": (
                    SubscriptionStatus.TRIAL.value
                    if plan.trial_period_days
                    else SubscriptionStatus.ACTIVE.value
                ),
            }

            # Set trial period if applicable
            if plan.trial_period_days:
                trial_start = datetime.now(timezone.utc)
                trial_end = trial_start + timedelta(days=plan.trial_period_days)
                sub_data.update(
                    {
                        "trial_start": trial_start.isoformat(),
                        "trial_end": trial_end.isoformat(),
                    }
                )

            result = (
                self.supabase.table("organization_subscriptions")
                .insert(sub_data)
                .execute()
            )

            if result.data:
                subscription = OrganizationSubscription(**result.data[0])

                # Allocate initial credits if any
                if plan.included_credits > 0:
                    await self.add_subscription_credits(
                        subscription.organization_id,
                        plan.included_credits,
                        subscription.id,
                        subscription.current_period_end,
                    )

                logger.info(f"Created organization subscription: {subscription.id}")
                return subscription

            raise Exception("Failed to create organization subscription")

        except Exception as e:
            logger.error(f"Error creating organization subscription: {e}")
            raise

    async def get_organization_subscription(
        self, organization_id: UUID
    ) -> Optional[OrganizationSubscriptionWithPlan]:
        """Get organization subscription with plan details."""
        try:
            result = (
                self.supabase.table("organization_subscriptions")
                .select("*, subscription_plans(*)")
                .eq("organization_id", str(organization_id))
                .execute()
            )

            if result.data:
                data = result.data[0]
                subscription = OrganizationSubscription(
                    **{k: v for k, v in data.items() if k != "subscription_plans"}
                )

                plan = None
                if data.get("subscription_plans"):
                    plan = SubscriptionPlan(**data["subscription_plans"])

                return OrganizationSubscriptionWithPlan(
                    **subscription.model_dump(), plan=plan
                )

            return None

        except Exception as e:
            logger.error(
                f"Error fetching organization subscription for {organization_id}: {e}"
            )
            raise

    async def update_organization_subscription(
        self, organization_id: UUID, subscription_data: OrganizationSubscriptionUpdate
    ) -> Optional[OrganizationSubscription]:
        """Update organization subscription."""
        try:
            update_data = {
                k: v for k, v in subscription_data.model_dump().items() if v is not None
            }

            # Convert any UUID objects to strings for JSON serialization
            for key, value in update_data.items():
                if isinstance(value, UUID):
                    update_data[key] = str(value)

            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = (
                self.supabase.table("organization_subscriptions")
                .update(update_data)
                .eq("organization_id", str(organization_id))
                .execute()
            )

            if result.data:
                updated_subscription = OrganizationSubscription(**result.data[0])

                # Handle credit reset for plan changes
                if subscription_data.subscription_plan_id:
                    new_plan = await self.get_subscription_plan(
                        subscription_data.subscription_plan_id
                    )
                    if new_plan:
                        # Reset credits to the new plan amount (not add to existing)
                        await self.reset_subscription_credits(
                            organization_id=organization_id,
                            credits=new_plan.included_credits,
                            subscription_id=updated_subscription.id,
                            expires_at=updated_subscription.current_period_end,
                        )
                        logger.info(
                            f"Reset credits to {new_plan.included_credits} for plan change to {new_plan.id}"
                        )

                return updated_subscription

            return None

        except Exception as e:
            logger.error(
                f"Error updating organization subscription for {organization_id}: {e}"
            )
            raise

    # Credit Management
    async def get_credit_balance(self, organization_id: UUID) -> CreditBalance:
        """Get detailed credit balance for an organization.

        Three-pool model: ``organizations.credit_balance`` holds plan credits
        (granted per billing period, expire at period end),
        ``organizations.admin_credit_balance`` holds non-expiring platform
        grants, and ``organizations.purchased_credit_balance`` holds one-off
        purchased credit packs. ``total_credits`` is their sum.
        """
        try:
            # Get organization's current credit balances across all pools.
            org_result = (
                self.supabase.table("organizations")
                .select(
                    "credit_balance, admin_credit_balance, purchased_credit_balance"
                )
                .eq("id", str(organization_id))
                .execute()
            )

            if not org_result.data:
                raise ValueError(f"Organization {organization_id} not found")

            plan_credits = int(org_result.data[0].get("credit_balance") or 0)
            admin_credits = int(org_result.data[0].get("admin_credit_balance") or 0)
            purchased_credits = int(
                org_result.data[0].get("purchased_credit_balance") or 0
            )
            total_credits = plan_credits + admin_credits + purchased_credits

            # Credits expiring soon (plan credits carry an expiry per period)
            thirty_days_from_now = (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat()

            expiring_soon_result = (
                self.supabase.table("credit_transactions")
                .select("amount, expires_at")
                .eq("organization_id", str(organization_id))
                .not_.is_("expires_at", "null")
                .lte("expires_at", thirty_days_from_now)
                .gte("expires_at", datetime.now(timezone.utc).isoformat())
                .order("expires_at")
                .execute()
            )

            expiring_soon = sum(tx["amount"] for tx in expiring_soon_result.data)
            next_expiry = None
            if expiring_soon_result.data:
                next_expiry = datetime.fromisoformat(
                    expiring_soon_result.data[0]["expires_at"].replace("Z", "+00:00")
                )

            return CreditBalance(
                total_credits=total_credits,
                subscription_credits=plan_credits,
                admin_granted_credits=admin_credits,
                purchased_credits=purchased_credits,
                expiring_soon=expiring_soon,
                expires_at=next_expiry,
            )

        except Exception as e:
            logger.error(f"Error getting credit balance for {organization_id}: {e}")
            raise

    @staticmethod
    def _credit_transaction_from_row(row: dict[str, Any]) -> CreditTransactionWithEvent:
        """Normalize Supabase's embedded ``credit_events`` field."""
        payload = dict(row)
        event_data = payload.pop("credit_events", None) or payload.pop(
            "credit_event", None
        )
        if isinstance(event_data, list):
            event_data = event_data[0] if event_data else None
        payload["credit_event"] = (
            CreditEvent(**event_data) if isinstance(event_data, dict) else None
        )
        return CreditTransactionWithEvent(**payload)

    async def get_credit_transactions(
        self,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 25,
        transaction_type: Optional[TransactionType] = None,
    ) -> CreditTransactionsResponse:
        """Return a paginated, event-enriched credit ledger for an organization.

        Args:
            organization_id: Organization whose ledger is requested.
            page: One-based page number.
            page_size: Number of rows to return, capped by the API route.
            transaction_type: Optional movement filter such as ``consumed``.

        Returns:
            Paginated ledger rows including the event category and unit cost
            when a transaction was caused by a credit event.
        """
        try:
            query = (
                self.supabase.table("credit_transactions")
                .select("*, credit_events(*)", count="exact")
                .eq("organization_id", str(organization_id))
                .order("created_at", desc=True)
            )
            if transaction_type:
                query = query.eq("transaction_type", transaction_type.value)

            offset = (page - 1) * page_size
            result = query.range(offset, offset + page_size - 1).execute()
            total = int(result.count or 0)
            items = [
                self._credit_transaction_from_row(row) for row in (result.data or [])
            ]
            return CreditTransactionsResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=max(1, (total + page_size - 1) // page_size),
            )
        except Exception as e:
            logger.error(
                "Error fetching credit transactions for %s: %s",
                organization_id,
                e,
            )
            raise

    async def get_credit_usage(
        self, organization_id: UUID, *, transaction_limit: int = 50
    ) -> CreditUsageResponse:
        """Build the organization credit dashboard payload.

        The response intentionally keeps the two live pools visible while
        aggregating current-period ledger movements by event category. This
        lets administrators distinguish available plan credits from purchased
        credits and see exactly what consumed the balance.
        """
        try:
            balance = await self.get_credit_balance(organization_id)
            subscription = await self.get_organization_subscription(organization_id)
            period_start = subscription.current_period_start if subscription else None
            period_end = subscription.current_period_end if subscription else None

            query = (
                self.supabase.table("credit_transactions")
                .select("*, credit_events(*)")
                .eq("organization_id", str(organization_id))
                .order("created_at", desc=True)
            )
            if period_start:
                query = query.gte("created_at", period_start.isoformat())
            rows = query.execute().data or []

            period_granted = 0
            period_used = 0
            category_totals: dict[str, CreditUsageCategory] = {}
            for row in rows:
                transaction_type = row.get("transaction_type")
                amount = int(row.get("amount") or 0)
                if (
                    transaction_type
                    in {
                        TransactionType.EARNED.value,
                        TransactionType.PURCHASED.value,
                    }
                    and amount > 0
                ):
                    period_granted += amount
                if transaction_type != TransactionType.CONSUMED.value:
                    continue

                consumed = abs(amount)
                period_used += consumed
                event = row.get("credit_events") or row.get("credit_event") or {}
                if isinstance(event, list):
                    event = event[0] if event else {}
                category = str(
                    event.get("category")
                    or (row.get("metadata") or {}).get("category")
                    or row.get("source")
                    or "other"
                )
                existing = category_totals.get(category)
                if existing:
                    existing.credits_consumed += consumed
                    existing.transaction_count += 1
                else:
                    category_totals[category] = CreditUsageCategory(
                        category=category,
                        credits_consumed=consumed,
                        transaction_count=1,
                    )

            recent = [
                self._credit_transaction_from_row(row)
                for row in rows[:transaction_limit]
            ]
            return CreditUsageResponse(
                organization_id=organization_id,
                balance=balance,
                period_start=period_start,
                period_end=period_end,
                period_credits_granted=period_granted,
                period_credits_used=period_used,
                period_credits_remaining=max(0, period_granted - period_used),
                usage_by_category=sorted(
                    category_totals.values(),
                    key=lambda item: item.credits_consumed,
                    reverse=True,
                ),
                transactions=recent,
            )
        except Exception as e:
            logger.error("Error building credit usage for %s: %s", organization_id, e)
            raise

    async def add_subscription_credits(
        self,
        organization_id: UUID,
        credits: int,
        subscription_id: UUID,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreditTransaction:
        """Add subscription credits to an organization exactly once per key."""
        return await self._add_credits(
            organization_id=organization_id,
            credits=credits,
            source=TransactionSource.SUBSCRIPTION,
            source_id=subscription_id,
            expires_at=expires_at,
            metadata=metadata,
            idempotency_key=idempotency_key,
            description="Subscription credits allocation",
        )

    async def reset_subscription_credits(
        self,
        organization_id: UUID,
        credits: int,
        subscription_id: UUID,
        expires_at: Optional[datetime] = None,
    ) -> CreditTransaction:
        """Reset subscription (plan) credits to a specific amount (for plan changes).

        Only the plan pool (``organizations.credit_balance``) is reset to the
        target; purchased credits are user-bought and never touched by plan
        changes.
        """
        try:
            # Get current balances across all pools.
            org_result = (
                self.supabase.table("organizations")
                .select(
                    "credit_balance, admin_credit_balance, purchased_credit_balance"
                )
                .eq("id", str(organization_id))
                .execute()
            )

            if not org_result.data:
                raise ValueError(f"Organization {organization_id} not found")

            current_plan_balance = org_result.data[0]["credit_balance"]
            current_admin_balance = int(
                org_result.data[0].get("admin_credit_balance") or 0
            )
            current_purchased_balance = org_result.data[0]["purchased_credit_balance"]

            # Calculate the difference needed to reach the target plan credit amount
            credit_difference = credits - current_plan_balance

            if credit_difference == 0:
                # No change needed
                logger.info(
                    f"Credits already at target amount {credits} for organization {organization_id}"
                )
                return None

            # Update organization plan balance to the exact target amount
            # (purchased pool untouched)
            self.supabase.table("organizations").update(
                {
                    "credit_balance": credits,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", str(organization_id)).execute()

            # Create transaction record for the adjustment
            transaction_data = CreditTransactionCreate(
                organization_id=organization_id,
                transaction_type=(
                    TransactionType.EARNED
                    if credit_difference > 0
                    else TransactionType.CONSUMED
                ),
                amount=credit_difference,
                source=TransactionSource.SUBSCRIPTION,
                source_id=subscription_id,
                expires_at=expires_at,
                description=f"Plan change: credits reset to {credits}",
            )

            # Convert UUID objects to strings for JSON serialization
            transaction_dict = transaction_data.model_dump()
            if (
                "organization_id" in transaction_dict
                and transaction_dict["organization_id"]
            ):
                transaction_dict["organization_id"] = str(
                    transaction_dict["organization_id"]
                )
            if "source_id" in transaction_dict and transaction_dict["source_id"]:
                transaction_dict["source_id"] = str(transaction_dict["source_id"])

            # Set balance_after field (combined total; required by database)
            transaction_dict["balance_after"] = (
                credits + current_admin_balance + current_purchased_balance
            )

            # Convert datetime objects to ISO strings
            if "expires_at" in transaction_dict and transaction_dict["expires_at"]:
                if isinstance(transaction_dict["expires_at"], datetime):
                    transaction_dict["expires_at"] = transaction_dict[
                        "expires_at"
                    ].isoformat()

            result = (
                self.supabase.table("credit_transactions")
                .insert(transaction_dict)
                .execute()
            )

            if result.data:
                logger.info(
                    f"Reset credits to {credits} for organization {organization_id} (was {current_plan_balance})"
                )
                return CreditTransaction(**result.data[0])

            raise Exception("Failed to create credit reset transaction")

        except Exception as e:
            logger.error(
                f"Error resetting credits to {credits} for {organization_id}: {e}"
            )
            raise

    async def add_purchased_credits(
        self,
        organization_id: UUID,
        credits: int,
        stripe_payment_intent_id: str,
        description: Optional[str] = None,
    ) -> CreditTransaction:
        """Add purchased credits to an organization."""
        return await self._add_credits(
            organization_id=organization_id,
            credits=credits,
            source=TransactionSource.PURCHASE,
            stripe_payment_intent_id=stripe_payment_intent_id,
            description=description or "Credit purchase",
        )

    async def refund_credits(
        self,
        organization_id: UUID,
        credits: int,
        reason: str,
        metadata: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreditTransaction:
        """Return credits to the purchased pool with a refunded ledger type.

        Refunds are platform adjustments rather than provider transactions, so
        they use ``admin_adjustment`` as their source and remain visible in the
        same immutable credit ledger as the original debit.
        """
        if credits <= 0:
            raise ValueError("Refund credits must be positive")
        return await self._add_credits(
            organization_id=organization_id,
            credits=credits,
            source=TransactionSource.ADMIN_ADJUSTMENT,
            transaction_type=TransactionType.REFUNDED,
            description=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

    async def _add_credits(
        self,
        organization_id: UUID,
        credits: int,
        source: TransactionSource,
        source_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
        stripe_payment_intent_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> CreditTransaction:
        """Internal method to add credits to the correct pool.

        Two-pool model:
        - SUBSCRIPTION grants land in ``organizations.credit_balance`` (plan
          pool). When a grant carries an ``expires_at`` (renewal), any leftover
          plan credits from the previous period are first expired (logged as an
          EXPIRED transaction) and the new grant replaces them.
        - PURCHASE grants land in ``organizations.purchased_credit_balance``
          (purchased pool, never expires).

        Any grant/purchase re-arms low-balance notifications for the cycle.
        """
        try:
            if idempotency_key:
                existing_result = (
                    self.supabase.table("credit_transactions")
                    .select("*")
                    .eq("organization_id", str(organization_id))
                    .contains("metadata", {"grant_key": idempotency_key})
                    .limit(1)
                    .execute()
                )
                if existing_result.data:
                    return CreditTransaction(**existing_result.data[0])

            # Versioned subscription grants always carry a stable key. Route
            # those grants through Postgres so the balance update, expiry
            # bookkeeping, and ledger insert commit or roll back together.
            if source == TransactionSource.SUBSCRIPTION and idempotency_key:
                return await self._grant_subscription_credits_locked(
                    organization_id=organization_id,
                    credits=credits,
                    source_id=source_id,
                    expires_at=expires_at,
                    metadata=metadata,
                    description=description,
                    idempotency_key=idempotency_key,
                )

            # Get current balances
            org_result = (
                self.supabase.table("organizations")
                .select(
                    "credit_balance, admin_credit_balance, purchased_credit_balance"
                )
                .eq("id", str(organization_id))
                .execute()
            )

            if not org_result.data:
                raise ValueError(f"Organization {organization_id} not found")

            current_plan = int(org_result.data[0].get("credit_balance") or 0)
            current_admin = int(org_result.data[0].get("admin_credit_balance") or 0)
            current_purchased = int(
                org_result.data[0].get("purchased_credit_balance") or 0
            )

            # Validate and serialize the ledger payload before any balance
            # mutation. Pydantic's default model_dump leaves datetime objects
            # in Python mode, which Supabase cannot encode as JSON.
            if idempotency_key:
                metadata = dict(metadata or {})
                metadata["grant_key"] = idempotency_key

            transaction_data = CreditTransactionCreate(
                organization_id=organization_id,
                transaction_type=(
                    transaction_type
                    or (
                        TransactionType.EARNED
                        if source == TransactionSource.SUBSCRIPTION
                        else TransactionType.PURCHASED
                    )
                ),
                amount=credits,
                source=source,
                source_id=source_id,
                expires_at=expires_at,
                stripe_payment_intent_id=stripe_payment_intent_id,
                description=description,
                metadata=metadata,
            )
            transaction_dict = transaction_data.model_dump(mode="json")

            # Expire leftover plan credits from the previous period when a new
            # expiring grant lands (renewal / invoice paid).
            if source == TransactionSource.SUBSCRIPTION and expires_at is not None:
                if current_plan > 0:
                    current_purchased = await self._expire_plan_credits(
                        organization_id,
                        current_plan,
                        current_admin,
                        current_purchased,
                    )
                    current_plan = 0

            if source == TransactionSource.SUBSCRIPTION:
                new_plan = current_plan + credits
                new_purchased = current_purchased
                self.supabase.table("organizations").update(
                    {
                        "credit_balance": new_plan,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", str(organization_id)).execute()
            else:
                new_plan = current_plan
                new_purchased = current_purchased + credits
                self.supabase.table("organizations").update(
                    {
                        "purchased_credit_balance": new_purchased,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", str(organization_id)).execute()

            new_balance = new_plan + current_admin + new_purchased

            # Set balance_after field (combined total; required by database)
            transaction_dict["balance_after"] = new_balance

            # Log the polymorphic relationship for debugging
            table_name = TransactionSourceMapping.get_source_table(source)
            logger.debug(
                f"Creating credit transaction: source={source.value}, source_id={source_id}, references_table={table_name}"
            )

            result = (
                self.supabase.table("credit_transactions")
                .insert(transaction_dict)
                .execute()
            )

            if result.data:
                logger.info(
                    f"Added {credits} credits to organization {organization_id} (source: {source.value})"
                )
                # Re-arm low-balance warnings for the new cycle
                await self._reset_low_credit_notification(organization_id)
                return CreditTransaction(**result.data[0])

            raise Exception("Failed to create credit transaction")

        except Exception as e:
            logger.error(f"Error adding credits to {organization_id}: {e}")
            raise

    async def _grant_subscription_credits_locked(
        self,
        organization_id: UUID,
        credits: int,
        source_id: Optional[UUID],
        expires_at: Optional[datetime],
        metadata: Optional[dict[str, Any]],
        description: Optional[str],
        idempotency_key: str,
    ) -> CreditTransaction:
        """Apply an idempotent subscription grant inside one database transaction.

        The backing PostgreSQL function locks the organization row, checks the
        grant key, expires leftover plan credits when appropriate, updates the
        plan pool, and inserts the ledger row before returning. Keeping these
        writes together prevents a failed ledger serialization or insert from
        leaving a balance that cannot be audited or safely retried.

        Args:
            organization_id: Organization receiving the included credits.
            credits: Positive number of credits to grant.
            source_id: Subscription UUID that owns the grant.
            expires_at: Optional period boundary for recurring plan credits.
            metadata: JSON-compatible grant metadata, including ``grant_key``.
            description: Human-readable ledger description.
            idempotency_key: Stable key for activation, invoice, or renewal.

        Returns:
            The inserted or previously applied credit transaction.

        Raises:
            ValueError: If the organization or grant is invalid.
            RuntimeError: If the database function returns no transaction.
        """
        result = self.supabase.rpc(
            "grant_subscription_credits",
            {
                "p_organization_id": str(organization_id),
                "p_credits": credits,
                "p_subscription_id": str(source_id) if source_id else None,
                "p_expires_at": expires_at.isoformat() if expires_at else None,
                "p_metadata": metadata,
                "p_description": description,
                "p_idempotency_key": idempotency_key,
            },
        ).execute()
        payload = result.data
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not payload:
            raise RuntimeError("Subscription credit grant returned no result")
        if payload.get("error"):
            error = payload["error"]
            if error == "organization_not_found":
                raise ValueError(f"Organization {organization_id} not found")
            raise ValueError(f"Subscription credit grant failed: {error}")

        transaction_payload = payload.get("transaction")
        if not transaction_payload:
            raise RuntimeError("Subscription credit grant returned no transaction")
        return CreditTransaction(**transaction_payload)

    async def grant_admin_credits(
        self,
        *,
        organization_id: UUID,
        credits: int,
        created_by: UUID,
        reason: str,
        idempotency_key: Optional[str] = None,
    ) -> AdminCreditGrantResponse:
        """Atomically allocate non-expiring bonus credits to an organization.

        The Postgres function locks the organization row, increments only the
        dedicated platform-grant pool, and writes both the immutable credit
        ledger row and the grant audit record in one transaction. A supplied
        idempotency key makes retries return the original grant without adding
        credits a second time.

        Args:
            organization_id: Organization receiving the platform allocation.
            credits: Positive number of bonus credits to allocate.
            created_by: Authenticated platform administrator performing the action.
            reason: Human-readable support or business reason retained for audit.
            idempotency_key: Optional stable retry key from the caller.

        Returns:
            The grant result with the created transaction and all live pools.

        Raises:
            ValueError: If the organization is missing or the database rejects
                the grant input.
            RuntimeError: If the database function does not return a transaction.
        """
        result = self.supabase.rpc(
            "grant_admin_credits",
            {
                "p_organization_id": str(organization_id),
                "p_credits": credits,
                "p_created_by": str(created_by),
                "p_reason": reason,
                "p_idempotency_key": idempotency_key,
            },
        ).execute()
        payload = result.data
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not payload:
            raise RuntimeError("Admin credit grant returned no result")
        if payload.get("error"):
            error = payload["error"]
            if error == "organization_not_found":
                raise ValueError(f"Organization {organization_id} not found")
            raise ValueError(f"Admin credit grant failed: {error}")

        transaction_payload = payload.get("transaction")
        if not transaction_payload:
            raise RuntimeError("Admin credit grant returned no transaction")

        transaction = CreditTransaction(**transaction_payload)
        plan_balance = int(payload.get("plan_balance") or 0)
        admin_balance = int(payload.get("admin_balance") or 0)
        purchased_balance = int(payload.get("purchased_balance") or 0)
        return AdminCreditGrantResponse(
            organization_id=organization_id,
            credits=credits,
            created=bool(payload.get("created", not payload.get("already_applied"))),
            grant_id=UUID(payload["grant_id"]) if payload.get("grant_id") else None,
            balance=CreditBalance(
                total_credits=plan_balance + admin_balance + purchased_balance,
                subscription_credits=plan_balance,
                admin_granted_credits=admin_balance,
                purchased_credits=purchased_balance,
                expiring_soon=0,
                expires_at=None,
            ),
            transaction=transaction,
        )

    async def _expire_plan_credits(
        self,
        organization_id: UUID,
        amount: int,
        current_admin: int,
        current_purchased: int,
    ) -> int:
        """Void leftover plan credits at period end and log an EXPIRED transaction.

        Returns the purchased balance unchanged (used to record a combined
        ``balance_after`` on the expiry row).
        """
        try:
            expire_tx = CreditTransactionCreate(
                organization_id=organization_id,
                transaction_type=TransactionType.EXPIRED,
                amount=-amount,
                source=TransactionSource.EXPIRY,
                description="Plan credits expired at period end",
            )
            expire_dict = expire_tx.model_dump(mode="json")
            expire_dict["balance_after"] = current_admin + current_purchased
            self.supabase.table("credit_transactions").insert(expire_dict).execute()
            logger.info(
                f"Expired {amount} leftover plan credits for organization {organization_id}"
            )
            return current_purchased
        except Exception as e:
            # Expiry bookkeeping must not block the new grant.
            logger.error(f"Error logging plan credit expiry for {organization_id}: {e}")
            return current_purchased

    async def _reset_low_credit_notification(self, organization_id: UUID) -> None:
        """Clear the notified threshold so warnings re-arm after a grant/purchase."""
        try:
            self.supabase.table("organizations").update(
                {"low_credit_threshold_notified": None}
            ).eq("id", str(organization_id)).execute()
        except Exception as e:
            logger.error(
                f"Error resetting low-credit notification marker for {organization_id}: {e}"
            )

    async def consume_credits(
        self, consumption_request: CreditConsumptionRequest
    ) -> CreditConsumptionResponse:
        """Consume credits for an event across three strictly prepaid pools.

        Plan credits are drained first, followed by platform-granted bonus
        credits, then purchased credits. The credit transaction is followed by
        a durable low-credit outbox row so email delivery is retried separately
        from the user-facing consumption request. The per-pool allocation is
        recorded in transaction metadata for audit.
        """
        try:
            if (
                consumption_request.idempotency_key
                and consumption_request.event_name.startswith("phone_number_")
            ):
                return await self._consume_phone_number_credits_atomic(
                    consumption_request
                )

            if consumption_request.idempotency_key:
                existing_result = (
                    self.supabase.table("credit_transactions")
                    .select("*")
                    .eq("organization_id", str(consumption_request.organization_id))
                    .contains(
                        "metadata",
                        {"idempotency_key": consumption_request.idempotency_key},
                    )
                    .limit(1)
                    .execute()
                )
                if existing_result.data:
                    existing = CreditTransaction(**existing_result.data[0])
                    return CreditConsumptionResponse(
                        success=True,
                        credits_consumed=abs(existing.amount),
                        balance_after=existing.balance_after,
                        transaction_id=existing.id,
                    )

            # Get credit event details
            event_result = (
                self.supabase.table("credit_events")
                .select("*")
                .eq("name", consumption_request.event_name)
                .eq("is_active", True)
                .execute()
            )

            if not event_result.data:
                raise ValueError(
                    f"Credit event '{consumption_request.event_name}' not found or inactive"
                )

            credit_event = CreditEvent(**event_result.data[0])
            credits_needed = credit_event.credit_cost * consumption_request.quantity

            if credits_needed == 0:
                balance_result = (
                    self.supabase.table("organizations")
                    .select(
                        "credit_balance, admin_credit_balance, purchased_credit_balance"
                    )
                    .eq("id", str(consumption_request.organization_id))
                    .limit(1)
                    .execute()
                )
                if not balance_result.data:
                    raise ValueError(
                        f"Organization {consumption_request.organization_id} not found"
                    )
                balance_row = balance_result.data[0]
                balance_after = sum(
                    int(balance_row.get(pool) or 0)
                    for pool in (
                        "credit_balance",
                        "admin_credit_balance",
                        "purchased_credit_balance",
                    )
                )
                return CreditConsumptionResponse(
                    success=True,
                    credits_consumed=0,
                    balance_after=balance_after,
                    transaction_id=UUID("00000000-0000-0000-0000-000000000000"),
                )

            debit_result = await self._debit_organization_credits_locked(
                consumption_request.organization_id, credits_needed
            )

            if debit_result.get("error") == "organization_not_found":
                raise ValueError(
                    f"Organization {consumption_request.organization_id} not found"
                )

            if not debit_result.get("success"):
                return CreditConsumptionResponse(
                    success=False,
                    credits_consumed=0,
                    balance_after=int(debit_result.get("balance_after") or 0),
                    transaction_id=UUID("00000000-0000-0000-0000-000000000000"),
                )

            new_balance = int(debit_result["balance_after"])
            plan_used = int(debit_result.get("plan_used") or 0)
            admin_used = int(debit_result.get("admin_used") or 0)
            purchased_used = int(debit_result.get("purchased_used") or 0)

            # Record per-pool allocation for audit
            consumption_metadata = dict(consumption_request.metadata or {})
            if consumption_request.idempotency_key:
                consumption_metadata["idempotency_key"] = (
                    consumption_request.idempotency_key
                )
            consumption_metadata["plan_credits"] = plan_used
            consumption_metadata["admin_credits"] = admin_used
            consumption_metadata["purchased_credits"] = purchased_used

            # Create consumption transaction using validated model
            transaction_data = CreditTransactionCreate(
                organization_id=consumption_request.organization_id,
                transaction_type=TransactionType.CONSUMED,
                amount=-credits_needed,
                source=TransactionSource.EVENT_CONSUMPTION,
                source_id=credit_event.id,  # References credit_events table
                credit_event_id=credit_event.id,
                description=f"Consumed {consumption_request.quantity}x {consumption_request.event_name}",
                metadata=consumption_metadata or None,
            )

            # Log the polymorphic relationship
            table_name = TransactionSourceMapping.get_source_table(
                TransactionSource.EVENT_CONSUMPTION
            )
            logger.debug(
                f"Creating consumption transaction: source_id={credit_event.id} references {table_name}"
            )

            # Manually set balance_after since it's not in the create model
            transaction_dict = transaction_data.model_dump()
            transaction_dict["balance_after"] = new_balance

            # Convert UUID objects to strings for JSON serialization
            if (
                "organization_id" in transaction_dict
                and transaction_dict["organization_id"]
            ):
                transaction_dict["organization_id"] = str(
                    transaction_dict["organization_id"]
                )
            if "source_id" in transaction_dict and transaction_dict["source_id"]:
                transaction_dict["source_id"] = str(transaction_dict["source_id"])
            if (
                "credit_event_id" in transaction_dict
                and transaction_dict["credit_event_id"]
            ):
                transaction_dict["credit_event_id"] = str(
                    transaction_dict["credit_event_id"]
                )

            # Convert datetime objects to ISO strings
            if "expires_at" in transaction_dict and transaction_dict["expires_at"]:
                if isinstance(transaction_dict["expires_at"], datetime):
                    transaction_dict["expires_at"] = transaction_dict[
                        "expires_at"
                    ].isoformat()

            result = (
                self.supabase.table("credit_transactions")
                .insert(transaction_dict)
                .execute()
            )

            if result.data:
                transaction = CreditTransaction(**result.data[0])
                logger.info(
                    f"Consumed {credits_needed} credits for {consumption_request.event_name} "
                    f"(plan={plan_used}, admin={admin_used}, purchased={purchased_used})"
                )

                # Notification delivery is deliberately asynchronous. A
                # provider outage must never roll back a successful debit.
                await self.enqueue_low_credit_notification(
                    consumption_request.organization_id,
                    transaction.id,
                    new_balance,
                )

                return CreditConsumptionResponse(
                    success=True,
                    credits_consumed=credits_needed,
                    balance_after=new_balance,
                    transaction_id=transaction.id,
                )

            raise Exception("Failed to create consumption transaction")

        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            raise

    async def _consume_phone_number_credits_atomic(
        self, consumption_request: CreditConsumptionRequest
    ) -> CreditConsumptionResponse:
        """Consume a phone rental exactly once inside a Postgres transaction.

        Phone-number purchase retries must not debit twice when two requests
        with the same idempotency key arrive concurrently. The dedicated RPC
        locks the organization row, checks the key, updates all credit pools,
        and inserts the ledger row before returning.
        """
        event_result = (
            self.supabase.table("credit_events")
            .select("*")
            .eq("name", consumption_request.event_name)
            .eq("is_active", True)
            .execute()
        )
        if not event_result.data:
            raise ValueError(
                f"Credit event '{consumption_request.event_name}' not found or inactive"
            )

        credit_event = CreditEvent(**event_result.data[0])
        credits_needed = credit_event.credit_cost * consumption_request.quantity
        rpc_result = self.supabase.rpc(
            "consume_phone_number_credits",
            {
                "p_organization_id": str(consumption_request.organization_id),
                "p_credit_event_id": str(credit_event.id),
                "p_credits_needed": credits_needed,
                "p_idempotency_key": consumption_request.idempotency_key,
                "p_phone_number": str(
                    (consumption_request.metadata or {}).get("phone_number", "")
                ),
                "p_purpose": (consumption_request.metadata or {}).get(
                    "purpose", "phone_number_purchase"
                ),
            },
        ).execute()
        payload = rpc_result.data
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        payload = payload or {}
        if not payload.get("success"):
            if payload.get("error") == "organization_not_found":
                raise ValueError(
                    f"Organization {consumption_request.organization_id} not found"
                )
            return CreditConsumptionResponse(
                success=False,
                credits_consumed=0,
                balance_after=int(payload.get("balance_after") or 0),
                transaction_id=UUID("00000000-0000-0000-0000-000000000000"),
            )

        transaction_id = UUID(str(payload["transaction_id"]))
        balance_after = int(payload.get("balance_after") or 0)
        if not payload.get("already_recorded"):
            await self.enqueue_low_credit_notification(
                consumption_request.organization_id,
                transaction_id,
                balance_after,
            )
        return CreditConsumptionResponse(
            success=True,
            credits_consumed=int(payload.get("credits_consumed") or credits_needed),
            balance_after=balance_after,
            transaction_id=transaction_id,
        )

    async def enqueue_low_credit_notification(
        self,
        organization_id: UUID,
        credit_transaction_id: UUID,
        balance_after: int,
    ) -> bool:
        """Persist a low-credit evaluation task after a successful debit.

        The outbox is idempotent on ``credit_transaction_id``. This method is
        best-effort by design: the credit debit has already succeeded, so an
        outbox persistence problem is logged for operational recovery instead
        of being reported as a failed usage charge.

        Args:
            organization_id: Organization whose balance changed.
            credit_transaction_id: Ledger transaction that caused the change.
            balance_after: Combined credit balance after the debit.

        Returns:
            ``True`` when the outbox row was accepted, otherwise ``False``.
        """
        try:
            self.supabase.table("credit_notification_outbox").upsert(
                {
                    "organization_id": str(organization_id),
                    "credit_transaction_id": str(credit_transaction_id),
                    "balance_after": int(balance_after),
                },
                on_conflict="credit_transaction_id",
            ).execute()
            return True
        except Exception as error:
            logger.error(
                "Failed to enqueue low-credit notification for transaction %s: %s",
                credit_transaction_id,
                error,
                exc_info=True,
            )
            return False

    async def process_low_credit_notification_outbox(
        self, limit: int = 100
    ) -> dict[str, int]:
        """Evaluate and deliver pending low-credit outbox rows.

        Rows remain pending when notification delivery fails. The scheduler
        records attempt diagnostics and retries them on a later pass; successful
        rows are marked processed so a worker restart cannot send duplicates.

        Args:
            limit: Maximum number of outbox rows to process in one pass.

        Returns:
            Counters for processed, succeeded, failed, and skipped rows.
        """
        summary = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
        try:
            result = (
                self.supabase.table("credit_notification_outbox")
                .select("*")
                .is_("processed_at", "null")
                .order("created_at")
                .limit(limit)
                .execute()
            )
        except Exception as error:
            logger.error("Failed to read low-credit notification outbox: %s", error)
            return summary

        for row in result.data or []:
            summary["processed"] += 1
            row_id = row.get("id")
            try:
                delivered = await self._maybe_notify_low_balance(
                    UUID(str(row["organization_id"])),
                    int(row.get("balance_after") or 0),
                )
                if delivered:
                    self.supabase.table("credit_notification_outbox").update(
                        {
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "last_error": None,
                        }
                    ).eq("id", str(row_id)).execute()
                    summary["succeeded"] += 1
                else:
                    raise RuntimeError("notification delivery incomplete")
            except Exception as error:
                summary["failed"] += 1
                try:
                    self.supabase.table("credit_notification_outbox").update(
                        {
                            "attempt_count": int(row.get("attempt_count") or 0) + 1,
                            "last_attempt_at": datetime.now(timezone.utc).isoformat(),
                            "last_error": str(error),
                        }
                    ).eq("id", str(row_id)).execute()
                except Exception:
                    logger.exception(
                        "Failed to record low-credit outbox retry for row %s", row_id
                    )
                logger.warning(
                    "Low-credit notification outbox row %s will be retried: %s",
                    row_id,
                    error,
                )
        return summary

    async def _debit_organization_credits_locked(
        self, organization_id: UUID, credits_needed: int
    ) -> dict[str, Any]:
        """Atomically debit plan, platform-grant, and purchased pools.

        Calls the ``debit_organization_credits`` Postgres function so concurrent
        consumers serialize on the organization row (``SELECT … FOR UPDATE``).

        Args:
            organization_id: Organization UUID.
            credits_needed: Positive credits to consume.

        Returns:
            JSON payload from the RPC with ``success``, balances, and pool usage.
        """
        result = self.supabase.rpc(
            "debit_organization_credits",
            {
                "p_organization_id": str(organization_id),
                "p_credits_needed": credits_needed,
            },
        ).execute()
        payload = result.data
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if payload is None:
            payload = {}
        return payload

    @staticmethod
    def allocate_consumption(
        plan_balance: int,
        purchased_balance: int,
        credits_needed: int,
    ) -> tuple[int, int]:
        """Allocate a legacy two-pool consumption in plan-first order.

        This helper remains available for callers that only model the legacy
        plan/purchased pools. New three-pool code should use
        :meth:`allocate_consumption_with_bonus`.

        Args:
            plan_balance: Current plan credits (expire at period end).
            purchased_balance: Current purchased credits (never expire).
            credits_needed: Credits to consume (positive integer).
        Returns:
            Tuple ``(plan_used, purchased_used)``. Sums to ``credits_needed``
            when the combined balance covers it, otherwise drains whatever is
            available (caller denies when the sum is short).

        Example:
            ```python
            allocate_consumption(30, 50, 60)  # -> (30, 30)
            allocate_consumption(0, 50, 60)  # -> (0, 50)
            allocate_consumption(100, 0, 60)  # -> (60, 0)
            ```
        """
        plan_used = max(0, min(plan_balance, credits_needed))
        remaining = credits_needed - plan_used
        purchased_used = max(0, min(purchased_balance, remaining))
        return plan_used, purchased_used

    @staticmethod
    def allocate_consumption_with_bonus(
        plan_balance: int,
        admin_balance: int,
        purchased_balance: int,
        credits_needed: int,
    ) -> tuple[int, int, int]:
        """Allocate consumption in plan, platform-bonus, purchased order.

        Args:
            plan_balance: Current expiring plan credits.
            admin_balance: Current non-expiring platform-granted credits.
            purchased_balance: Current non-expiring purchased credits.
            credits_needed: Positive credits to consume.

        Returns:
            Tuple ``(plan_used, admin_used, purchased_used)``. The tuple drains
            all available pools in precedence order when the total is short.
        """
        plan_used = max(0, min(plan_balance, credits_needed))
        remaining = credits_needed - plan_used
        admin_used = max(0, min(admin_balance, remaining))
        remaining -= admin_used
        purchased_used = max(0, min(purchased_balance, remaining))
        return plan_used, admin_used, purchased_used

    async def _maybe_notify_low_balance(
        self, organization_id: UUID, remaining_total: int
    ) -> bool:
        """Email org admins when the balance crosses a low-credit threshold.

        Uses the ``credits.low_balance`` template at 20/10/5% of the period's
        included credits. Each threshold fires at most once per billing cycle
        (``organizations.low_credit_threshold_notified``), re-armed by any
        grant or purchase. Notification logs provide per-recipient idempotency,
        so provider failures can be retried without duplicating successful
        deliveries. Return ``False`` when the outbox should retry the row.
        """
        try:
            from src.notifications.models import SendNotificationRequest
            from src.notifications.service import notification_service
            from src.rbac.user_roles.service import user_role_service

            included = await credit_entitlement_service.get_included_credits_per_billing_period(
                organization_id
            )
            if included <= 0:
                return True

            org_result = (
                self.supabase.table("organizations")
                .select("name, low_credit_threshold_notified")
                .eq("id", str(organization_id))
                .limit(1)
                .execute()
            )
            if not org_result.data:
                return True
            org_row = org_result.data[0]
            last_notified = org_row.get("low_credit_threshold_notified")

            threshold = CreditEntitlementService.low_credit_threshold_to_notify(
                remaining_total, included, last_notified
            )
            if threshold is None:
                return True

            members, error = await user_role_service.get_users_by_organization(
                organization_id
            )
            if error or not members:
                logger.warning(
                    f"No members to notify for low credit org {organization_id}: {error}"
                )
                return False

            # Billing notifications go to business owners represented by
            # organization admins, not every organization member.
            admins = [
                m for m in members if any(role.name == "org_admin" for role in m.roles)
            ]
            if not admins:
                logger.warning(
                    "No organization admins to notify for low credit org %s",
                    organization_id,
                )
                return False
            recipients = admins

            purchase_url = (
                f"{settings.app_base_url or 'http://localhost:3000'}"
                "/organization/billing"
            )

            all_sent = True
            for member in recipients:
                try:
                    request = SendNotificationRequest(
                        event_key="credits.low_balance",
                        recipient_email=member.email,
                        recipient_name=f"{member.first_name} {member.last_name}".strip(),
                        organization_id=organization_id,
                        user_id=member.id,
                        template_variables={
                            "user_name": f"{member.first_name} {member.last_name}".strip(),
                            "current_credits": str(remaining_total),
                            "threshold_percent": str(threshold),
                            "organization_name": org_row.get(
                                "name", "your organization"
                            ),
                            "purchase_credits_url": purchase_url,
                            "app_name": getattr(settings, "app_name", "24x7 AI"),
                        },
                        idempotency_key=(
                            f"low-credit:{organization_id}:{threshold}:{member.id}"
                        ),
                    )
                    response = await notification_service.send_notification(request)
                    if not response or not response.success:
                        all_sent = False
                except Exception as email_error:
                    all_sent = False
                    logger.error(
                        f"Failed to send low-credit email to {member.email}: {email_error}",
                        exc_info=True,
                    )

            # Only advance the cycle marker after every owner delivery has
            # succeeded. A later credit event can retry failed recipients by
            # reusing their idempotency keys.
            if all_sent:
                update_result = (
                    self.supabase.table("organizations")
                    .update({"low_credit_threshold_notified": threshold})
                    .eq("id", str(organization_id))
                    .execute()
                )
                return getattr(update_result, "data", None) is not None
            return False
        except Exception as e:
            logger.error(
                f"Error evaluating low-credit notification for {organization_id}: {e}",
                exc_info=True,
            )
            return False

    # Credit Events Management
    async def get_credit_events(self, active_only: bool = True) -> list[CreditEvent]:
        """Get all credit events."""
        try:
            query = self.supabase.table("credit_events").select("*")

            if active_only:
                query = query.eq("is_active", True)

            result = query.execute()

            return [CreditEvent(**event) for event in result.data]

        except Exception as e:
            logger.error(f"Error fetching credit events: {e}")
            raise

    # Credit Products Management
    async def get_credit_products(
        self, active_only: bool = True
    ) -> list[CreditProduct]:
        """Get all credit products."""
        try:
            query = self.supabase.table("credit_products").select("*")

            if active_only:
                query = query.eq("is_active", True)

            result = query.order("credit_amount").execute()

            return [CreditProduct(**product) for product in result.data]

        except Exception as e:
            logger.error(f"Error fetching credit products: {e}")
            raise

    # Billing History
    async def create_billing_history(
        self, billing_data: BillingHistoryCreate
    ) -> BillingHistory:
        """Create a billing history entry."""
        try:
            # Convert UUID objects to strings for JSON serialization
            billing_dict = billing_data.model_dump()
            if "organization_id" in billing_dict and billing_dict["organization_id"]:
                billing_dict["organization_id"] = str(billing_dict["organization_id"])

            # Convert datetime objects to ISO strings
            if "paid_at" in billing_dict and billing_dict["paid_at"]:
                if isinstance(billing_dict["paid_at"], datetime):
                    billing_dict["paid_at"] = billing_dict["paid_at"].isoformat()

            result = (
                self.supabase.table("billing_history").insert(billing_dict).execute()
            )

            if result.data:
                return BillingHistory(**result.data[0])

            raise Exception("Failed to create billing history")

        except Exception as e:
            logger.error(f"Error creating billing history: {e}")
            raise

    async def get_billing_history(
        self, organization_id: UUID, limit: int = 10
    ) -> list[BillingHistory]:
        """Get billing history for an organization."""
        try:
            result = (
                self.supabase.table("billing_history")
                .select("*")
                .eq("organization_id", str(organization_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return [BillingHistory(**record) for record in result.data]

        except Exception as e:
            logger.error(f"Error fetching billing history for {organization_id}: {e}")
            raise

    # Billing Summary
    async def get_organization_billing_summary(
        self, organization_id: UUID
    ) -> OrganizationBillingSummary:
        """Get comprehensive billing summary for an organization."""
        try:
            # Get subscription details
            subscription = await self.get_organization_subscription(organization_id)

            # Get credit balance
            credit_balance_info = await self.get_credit_balance(organization_id)

            # Calculate current period usage
            current_period_usage = 0
            if subscription and subscription.current_period_start:
                usage_result = (
                    self.supabase.table("credit_transactions")
                    .select("amount")
                    .eq("organization_id", str(organization_id))
                    .eq("transaction_type", TransactionType.CONSUMED.value)
                    .gte("created_at", subscription.current_period_start.isoformat())
                    .execute()
                )

                current_period_usage = abs(
                    sum(tx["amount"] for tx in usage_result.data)
                )

            # Determine next billing date and amount
            next_billing_date = None
            amount_due = None

            if subscription and subscription.current_period_end:
                next_billing_date = subscription.current_period_end
                if subscription.plan:
                    amount_due = subscription.plan.price_amount

            return OrganizationBillingSummary(
                organization_id=organization_id,
                subscription=subscription,
                credit_balance=credit_balance_info.total_credits,
                current_period_usage=current_period_usage,
                next_billing_date=next_billing_date,
                amount_due=amount_due,
            )

        except Exception as e:
            logger.error(f"Error getting billing summary for {organization_id}: {e}")
            raise

    # Polymorphic Relationship Utilities
    async def validate_transaction_references(
        self, organization_id: Optional[UUID] = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Validate polymorphic references in credit transactions.

        Returns a report of invalid or orphaned references.
        """
        try:
            # Get transactions to validate
            query = self.supabase.table("credit_transactions").select("*")
            if organization_id:
                query = query.eq("organization_id", str(organization_id))

            result = query.execute()
            transactions = result.data

            validation_report = {
                "invalid_source_relationships": [],
                "orphaned_references": [],
                "valid_transactions": 0,
                "total_transactions": len(transactions),
            }

            for tx in transactions:
                source = TransactionSource(tx["source"])
                source_id = tx.get("source_id")

                # Check source/source_id relationship validity
                if not TransactionSourceMapping.validate_source_relationship(
                    source, source_id
                ):
                    validation_report["invalid_source_relationships"].append(
                        {
                            "transaction_id": tx["id"],
                            "source": tx["source"],
                            "source_id": source_id,
                            "error": TransactionSourceMapping.get_validation_error(
                                source, source_id
                            ),
                        }
                    )
                    continue

                # Check if referenced record exists (for sources that require it)
                if source_id and TransactionSourceMapping.requires_source_id(source):
                    table_name = TransactionSourceMapping.get_source_table(source)
                    if table_name:
                        ref_result = (
                            self.supabase.table(table_name)
                            .select("id")
                            .eq("id", str(source_id))
                            .execute()
                        )

                        if not ref_result.data:
                            validation_report["orphaned_references"].append(
                                {
                                    "transaction_id": tx["id"],
                                    "source": tx["source"],
                                    "source_id": source_id,
                                    "referenced_table": table_name,
                                    "error": f"Referenced {table_name} record {source_id} does not exist",
                                }
                            )
                            continue

                validation_report["valid_transactions"] += 1

            logger.info(
                f"Transaction validation complete. Valid: {validation_report['valid_transactions']}/{validation_report['total_transactions']}"
            )
            return validation_report

        except Exception as e:
            logger.error(f"Error validating transaction references: {e}")
            raise

    async def get_transaction_source_details(
        self, transaction_id: UUID
    ) -> dict[str, Any]:
        """Get detailed information about a transaction's source reference.

        This is useful for debugging polymorphic relationships.
        """
        try:
            # Get the transaction
            result = (
                self.supabase.table("credit_transactions")
                .select("*")
                .eq("id", str(transaction_id))
                .execute()
            )

            if not result.data:
                raise ValueError(f"Transaction {transaction_id} not found")

            tx = result.data[0]
            source = TransactionSource(tx["source"])
            source_id = tx.get("source_id")

            details = {
                "transaction_id": str(transaction_id),
                "source": tx["source"],
                "source_id": source_id,
                "expected_table": TransactionSourceMapping.get_source_table(source),
                "requires_source_id": TransactionSourceMapping.requires_source_id(
                    source
                ),
                "relationship_valid": TransactionSourceMapping.validate_source_relationship(
                    source, source_id
                ),
                "referenced_record": None,
            }

            # Fetch referenced record if it exists
            if source_id and details["expected_table"]:
                ref_result = (
                    self.supabase.table(details["expected_table"])
                    .select("*")
                    .eq("id", str(source_id))
                    .execute()
                )

                if ref_result.data:
                    details["referenced_record"] = ref_result.data[0]
                else:
                    details["reference_exists"] = False

            return details

        except Exception as e:
            logger.error(
                f"Error getting transaction source details for {transaction_id}: {e}"
            )
            raise


# Global instance
billing_service = BillingService()
