"""Service for customer-facing, immutable plan selection and activation."""

import calendar
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from shared.config import supabase_config

from .credit_grant_service import credit_grant_service
from .models import SubscriptionStatus
from .plan_version_models import BillingMode, CreditGrantPolicy, PlanVersionStatus
from .stripe_service import stripe_service
from .versioned_subscription_models import (
    CustomerPlanVersion,
    FreePlanActivationResponse,
    SubscriptionActivationState,
    SubscriptionActivationStatus,
    VersionedSubscriptionCheckoutRequest,
    VersionedSubscriptionCheckoutResponse,
    VersionedSubscriptionRecord,
)

logger = logging.getLogger(__name__)


class VersionedSubscriptionService:
    """List published plan versions and activate them without legacy inference."""

    def __init__(self) -> None:
        """Initialize the service with the configured Supabase client."""
        self.supabase = supabase_config.client
        self.credit_grant_service = credit_grant_service

    async def list_available_plan_versions(self) -> list[CustomerPlanVersion]:
        """Return current published versions and their customer-visible entitlements."""
        result = (
            self.supabase.table("plan_versions")
            .select(
                "*, plan_products!inner(id, slug, display_name, description, sort_order)"
            )
            .eq("status", PlanVersionStatus.PUBLISHED.value)
            .eq("is_current_for_signup", True)
            .order("version_number", desc=True)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return []

        version_ids = [str(row["id"]) for row in rows]
        entitlements_result = (
            self.supabase.table("plan_version_entitlements")
            .select("plan_version_id, entitlement_key, value")
            .in_("plan_version_id", version_ids)
            .execute()
        )
        entitlements: dict[str, dict[str, dict[str, Any]]] = {}
        for row in entitlements_result.data or []:
            entitlements.setdefault(str(row["plan_version_id"]), {})[
                row["entitlement_key"]
            ] = row["value"]

        return [
            self._to_customer_plan_version(row, entitlements.get(str(row["id"]), {}))
            for row in rows
        ]

    async def activate_free_plan(
        self, organization_id: UUID, plan_version_id: UUID
    ) -> FreePlanActivationResponse:
        """Bind an organization to a published free version without Stripe."""
        version = await self._get_signup_plan_version(plan_version_id)
        self._require_billing_mode(version, BillingMode.FREE)

        existing = await self._get_existing_subscription(organization_id)
        if existing:
            if str(existing.get("plan_version_id")) == str(
                plan_version_id
            ) and existing.get("status") in {"active", "trial"}:
                retry_now = datetime.now(timezone.utc)
                period_start = self._coerce_datetime(
                    existing.get("current_period_start"), retry_now
                )
                period_end = self._coerce_optional_datetime(
                    existing.get("current_period_end")
                )
                # The subscription row may have committed before a transient
                # credit-grant failure. The grant service and database RPC are
                # idempotent, so replaying this key repairs that state without
                # creating another subscription or double-crediting success.
                await self.credit_grant_service.grant_for_subscription(
                    existing,
                    grant_reason="activation",
                    period_start=period_start,
                    period_end=period_end,
                    grant_key=f"free-subscription:{existing['id']}:activation",
                )
                return FreePlanActivationResponse(
                    subscription=self._to_subscription_record(existing), created=False
                )
            if existing.get("status") not in {"cancelled", "expired"}:
                raise ValueError("Organization already has an active subscription")

        now = datetime.now(timezone.utc)
        period_end = self._period_end(now, version.get("billing_interval", "monthly"))
        grant_policy = version.get(
            "credit_grant_policy", CreditGrantPolicy.RECURRING.value
        )
        payload = {
            "organization_id": str(organization_id),
            "subscription_plan_id": version.get("legacy_subscription_plan_id"),
            "plan_version_id": str(plan_version_id),
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "status": SubscriptionStatus.ACTIVE.value,
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "cancel_at_period_end": False,
            "cancelled_at": None,
            "metadata": {
                "activation_source": "onboarding",
                "billing_mode": BillingMode.FREE.value,
                "credit_grant_policy": grant_policy,
                "billing_interval": version.get("billing_interval", "monthly"),
            },
        }

        if existing:
            result = (
                self.supabase.table("organization_subscriptions")
                .update(payload)
                .eq("organization_id", str(organization_id))
                .execute()
            )
        else:
            result = (
                self.supabase.table("organization_subscriptions")
                .insert(payload)
                .execute()
            )

        if not result.data:
            raise ValueError("Failed to activate free plan")
        subscription_row = result.data[0]
        await self.credit_grant_service.grant_for_subscription(
            subscription_row,
            grant_reason="activation",
            period_start=now,
            period_end=period_end,
            grant_key=f"free-subscription:{subscription_row['id']}:activation",
        )
        return FreePlanActivationResponse(
            subscription=self._to_subscription_record(subscription_row),
            created=existing is None,
        )

    async def create_paid_checkout(
        self,
        request: VersionedSubscriptionCheckoutRequest,
        customer_email: str,
    ) -> VersionedSubscriptionCheckoutResponse:
        """Create Stripe Checkout for a published paid version.

        Args:
            request: Checkout request containing the organization, plan version,
                and redirect URLs.
            customer_email: Email address of the authenticated organization
                administrator starting checkout. This value is supplied by the
                route from the authenticated user profile and is never accepted
                from the browser request.

        Returns:
            The Stripe Checkout URL and session identifier for the selected plan.

        Raises:
            ValueError: If the plan is not eligible for paid checkout, the
                organization already has an active subscription, or Stripe setup
                fails validation.
        """
        version = await self._get_signup_plan_version(request.plan_version_id)
        self._require_billing_mode(version, BillingMode.PAID)
        price_id = version.get("stripe_price_id")
        if not price_id:
            raise ValueError("Stripe Price is required for paid plan checkout")

        existing = await self._get_existing_subscription(request.organization_id)
        if existing and existing.get("status") not in {"cancelled", "expired"}:
            raise ValueError("Organization already has an active subscription")

        organization_result = (
            self.supabase.table("organizations")
            .select("id, name, slug")
            .eq("id", str(request.organization_id))
            .limit(1)
            .execute()
        )
        if not organization_result.data:
            raise ValueError(f"Organization {request.organization_id} not found")
        organization = organization_result.data[0]

        customer = await stripe_service.create_customer(
            email=customer_email,
            name=organization["name"],
            organization_id=str(request.organization_id),
            metadata={"plan_version_id": str(request.plan_version_id)},
        )
        metadata = {
            "organization_id": str(request.organization_id),
            "plan_version_id": str(request.plan_version_id),
            "type": "versioned_subscription",
        }
        legacy_plan_id = version.get("legacy_subscription_plan_id")
        if legacy_plan_id:
            metadata["plan_id"] = str(legacy_plan_id)

        session = await stripe_service.create_checkout_session(
            customer_id=customer.id,
            price_id=str(price_id),
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            mode="subscription",
            metadata=metadata,
            trial_period_days=version.get("trial_period_days"),
        )
        return VersionedSubscriptionCheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
            plan_version_id=request.plan_version_id,
        )

    async def get_activation_status(
        self, organization_id: UUID
    ) -> SubscriptionActivationStatus:
        """Return the explicit plan-selection state for an organization."""
        existing = await self._get_existing_subscription(organization_id)
        if not existing:
            return SubscriptionActivationStatus(
                organization_id=organization_id,
                state=SubscriptionActivationState.UNSELECTED,
            )

        status = existing.get("status")
        state = {
            SubscriptionStatus.TRIAL.value: SubscriptionActivationState.TRIAL,
            SubscriptionStatus.ACTIVE.value: SubscriptionActivationState.ACTIVE,
            SubscriptionStatus.PAST_DUE.value: SubscriptionActivationState.PAST_DUE,
            SubscriptionStatus.CANCELLED.value: SubscriptionActivationState.CANCELLED,
            SubscriptionStatus.EXPIRED.value: SubscriptionActivationState.CANCELLED,
            SubscriptionStatus.INCOMPLETE.value: SubscriptionActivationState.CHECKOUT_PENDING,
            SubscriptionStatus.INCOMPLETE_EXPIRED.value: SubscriptionActivationState.CANCELLED,
        }.get(status, SubscriptionActivationState.CHECKOUT_PENDING)
        billing_mode = None
        if existing.get("metadata", {}).get("billing_mode") in {
            BillingMode.FREE.value,
            BillingMode.PAID.value,
        }:
            billing_mode = BillingMode(existing["metadata"]["billing_mode"])
        return SubscriptionActivationStatus(
            organization_id=organization_id,
            state=state,
            subscription_id=UUID(str(existing["id"])),
            plan_version_id=(
                UUID(str(existing["plan_version_id"]))
                if existing.get("plan_version_id")
                else None
            ),
            billing_mode=billing_mode,
            subscription_status=SubscriptionStatus(status) if status else None,
        )

    async def record_paid_subscription_from_stripe(
        self,
        organization_id: UUID,
        resolved_plan: Any,
        stripe_subscription: dict[str, Any],
    ) -> VersionedSubscriptionRecord:
        """Persist a paid Stripe subscription when no legacy plan row exists.

        Stripe webhooks resolve the immutable version from the Stripe Price. New
        catalog versions are allowed to omit ``legacy_subscription_plan_id``;
        this path keeps those subscriptions fully version-bound instead of
        dropping the event because the legacy table has no matching row.
        """
        existing = await self._get_existing_subscription(organization_id)
        period_start = stripe_subscription.get("current_period_start")
        period_end = stripe_subscription.get("current_period_end")
        payload = {
            "organization_id": str(organization_id),
            "subscription_plan_id": None,
            "plan_version_id": str(resolved_plan.plan_version_id),
            "stripe_subscription_id": stripe_subscription["id"],
            "stripe_customer_id": stripe_subscription.get("customer"),
            "status": stripe_subscription.get("status", "active"),
            "current_period_start": (
                datetime.fromtimestamp(period_start, tz=timezone.utc).isoformat()
                if period_start
                else None
            ),
            "current_period_end": (
                datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()
                if period_end
                else None
            ),
            "cancel_at_period_end": stripe_subscription.get(
                "cancel_at_period_end", False
            ),
            "metadata": {
                **(stripe_subscription.get("metadata") or {}),
                "billing_mode": BillingMode.PAID.value,
                "credit_grant_policy": CreditGrantPolicy.RECURRING.value,
            },
        }
        table = self.supabase.table("organization_subscriptions")
        if existing:
            result = (
                table.update(payload)
                .eq("organization_id", str(organization_id))
                .execute()
            )
        else:
            result = table.insert(payload).execute()
        if not result.data:
            raise ValueError("Failed to persist paid subscription from Stripe")
        return self._to_subscription_record(result.data[0])

    async def _get_signup_plan_version(self, plan_version_id: UUID) -> dict[str, Any]:
        """Fetch and validate the version is currently available for signup."""
        result = (
            self.supabase.table("plan_versions")
            .select(
                "*, plan_products!inner(id, slug, display_name, description, sort_order)"
            )
            .eq("id", str(plan_version_id))
            .eq("status", PlanVersionStatus.PUBLISHED.value)
            .eq("is_current_for_signup", True)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise ValueError("Plan version is not available for signup")
        return result.data[0]

    async def _get_existing_subscription(
        self, organization_id: UUID
    ) -> Optional[dict[str, Any]]:
        """Fetch the organization’s single subscription row, if present."""
        result = (
            self.supabase.table("organization_subscriptions")
            .select("*")
            .eq("organization_id", str(organization_id))
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    def _require_billing_mode(version: dict[str, Any], mode: BillingMode) -> None:
        """Reject activation when the explicit catalog mode does not match."""
        if version.get("billing_mode") != mode.value:
            raise ValueError(f"This endpoint is only for {mode.value} plan versions")

    @staticmethod
    def _period_end(start: datetime, billing_interval: str) -> datetime:
        """Return the next calendar-aligned monthly or annual boundary."""
        if billing_interval == "annual":
            try:
                return start.replace(year=start.year + 1)
            except ValueError:
                return start.replace(year=start.year + 1, day=28)
        next_month = start.month + 1
        next_year = start.year
        if next_month == 13:
            next_month = 1
            next_year += 1
        next_day = min(start.day, calendar.monthrange(next_year, next_month)[1])
        return start.replace(year=next_year, month=next_month, day=next_day)

    @staticmethod
    def _coerce_datetime(value: Any, fallback: datetime) -> datetime:
        """Parse a stored subscription timestamp, falling back safely."""
        parsed = VersionedSubscriptionService._coerce_optional_datetime(value)
        return parsed or fallback

    @staticmethod
    def _coerce_optional_datetime(value: Any) -> Optional[datetime]:
        """Convert a database timestamp to a timezone-aware datetime."""
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("Invalid subscription period timestamp: %s", value)
            return None

    @staticmethod
    def _to_customer_plan_version(
        row: dict[str, Any], entitlements: dict[str, dict[str, Any]]
    ) -> CustomerPlanVersion:
        """Map a database row to the safe customer-facing catalog shape."""
        product = row.get("plan_products") or {}
        return CustomerPlanVersion(
            id=UUID(str(row["id"])),
            plan_product_id=UUID(str(row["plan_product_id"])),
            product_slug=product.get("slug", ""),
            product_name=product.get(
                "display_name", row.get("display_label") or "Plan"
            ),
            product_description=product.get("description"),
            version_number=row["version_number"],
            display_label=row.get("display_label"),
            billing_mode=BillingMode(row["billing_mode"]),
            credit_grant_policy=CreditGrantPolicy(
                row.get("credit_grant_policy", CreditGrantPolicy.RECURRING.value)
            ),
            price_amount_cents=row["price_amount_cents"],
            currency=row["currency"],
            billing_interval=row["billing_interval"],
            trial_period_days=row.get("trial_period_days"),
            stripe_price_id=row.get("stripe_price_id"),
            entitlements=entitlements,
        )

    @staticmethod
    def _to_subscription_record(row: dict[str, Any]):
        """Map a database subscription row to the activation response model."""
        return VersionedSubscriptionRecord(
            id=UUID(str(row["id"])),
            organization_id=UUID(str(row["organization_id"])),
            subscription_plan_id=(
                UUID(str(row["subscription_plan_id"]))
                if row.get("subscription_plan_id")
                else None
            ),
            plan_version_id=UUID(str(row["plan_version_id"])),
            stripe_subscription_id=row.get("stripe_subscription_id"),
            stripe_customer_id=row.get("stripe_customer_id"),
            status=SubscriptionStatus(row["status"]),
            current_period_start=row.get("current_period_start"),
            current_period_end=row.get("current_period_end"),
            metadata=row.get("metadata") or {},
        )


versioned_subscription_service = VersionedSubscriptionService()
