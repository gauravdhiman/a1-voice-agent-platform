"""
Service for plan product versioning: publish, grandfathering, and Stripe resolution.

Published versions are immutable. Subscribers bind to a version via
``organization_subscriptions.plan_version_id``. Publishing a new version never
changes existing subscribers unless ``migration_mode`` is ``immediate_required``.

Key Features:
    - Resolve Stripe price IDs to plan versions for checkout/webhooks
    - Publish draft versions (Stripe Price creation, deprecate prior signup version)
    - Record publish events and optional migration rows for legacy subscribers

Example:
    ```python
    result = await plan_version_service.publish_plan_version(
        draft_id,
        PlanVersionPublishRequest(migration_mode=MigrationMode.NEW_SIGNUPS_ONLY),
        published_by=admin_user_id,
    )
    ```
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from shared.config import supabase_config

from .plan_version_models import (
    BillingMode,
    MigrationMode,
    PlanVersionPublishRequest,
    PlanVersionPublishResult,
    PlanVersionStatus,
    ResolvedCheckoutPlan,
)
from .stripe_service import stripe_service

logger = logging.getLogger(__name__)


class PlanVersionService:
    """Manage plan version lifecycle and Stripe price resolution."""

    def __init__(self) -> None:
        """Initialize with Supabase client."""
        self.supabase = supabase_config.client

    async def resolve_checkout_plan(self, stripe_price_id: str) -> ResolvedCheckoutPlan:
        """Resolve a Stripe price ID to a published plan version.

        Args:
            stripe_price_id: Stripe Price identifier from checkout or webhook.

        Returns:
            ResolvedCheckoutPlan with plan_version_id and optional legacy plan id.

        Raises:
            ValueError: When no published plan version matches the price ID.
        """
        row = await self._get_plan_version_by_stripe_price_id(stripe_price_id)
        if not row:
            raise ValueError(
                f"No plan version found for Stripe price {stripe_price_id}"
            )

        legacy_raw = row.get("legacy_subscription_plan_id")
        legacy_plan_id = UUID(str(legacy_raw)) if legacy_raw else None

        return ResolvedCheckoutPlan(
            plan_version_id=UUID(str(row["id"])),
            subscription_plan_id=legacy_plan_id,
            stripe_price_id=stripe_price_id,
        )

    async def publish_plan_version(
        self,
        plan_version_id: UUID,
        request: PlanVersionPublishRequest,
        published_by: UUID,
    ) -> PlanVersionPublishResult:
        """Publish a draft plan version and apply migration policy.

        Marks the draft as the current signup version, deprecates the previous
        current version for the same product, records a publish event, and
        optionally creates migration rows or immediate migrations.

        Args:
            plan_version_id: UUID of the draft version to publish.
            request: Migration policy and Stripe timing options.
            published_by: Platform admin user performing the publish.

        Returns:
            PlanVersionPublishResult summarizing the publish outcome.

        Raises:
            ValueError: If the version is not in draft status or validation fails.
        """
        draft = await self._get_plan_version(plan_version_id)
        if draft.get("status") != PlanVersionStatus.DRAFT.value:
            raise ValueError(
                f"Plan version {plan_version_id} is not draft (status={draft.get('status')})"
            )

        self._validate_publish_request(request)

        product_id = UUID(str(draft["plan_product_id"]))
        previous = await self._get_current_signup_version_for_product(product_id)
        from_version_id = UUID(str(previous["id"])) if previous else None

        stripe_price_id = await self._ensure_stripe_price(draft)
        published_at = datetime.now(timezone.utc)

        await self._update_plan_version(
            plan_version_id,
            {
                "status": PlanVersionStatus.PUBLISHED.value,
                "is_current_for_signup": True,
                "stripe_price_id": stripe_price_id,
                "published_at": published_at.isoformat(),
                "updated_at": published_at.isoformat(),
            },
        )

        if previous and from_version_id != plan_version_id:
            await self._update_plan_version(
                from_version_id,
                {
                    "is_current_for_signup": False,
                    "status": PlanVersionStatus.DEPRECATED.value,
                    "updated_at": published_at.isoformat(),
                },
            )

        publish_event = await self._create_publish_event(
            from_plan_version_id=from_version_id,
            to_plan_version_id=plan_version_id,
            request=request,
            published_by=published_by,
            published_at=published_at,
        )
        publish_event_id = UUID(str(publish_event["id"]))

        migration_rows = 0
        migrated_immediately = 0

        if from_version_id and request.migration_mode != MigrationMode.NEW_SIGNUPS_ONLY:
            if request.migration_mode == MigrationMode.IMMEDIATE_REQUIRED:
                migrated_immediately = await self._migrate_subscribers_immediately(
                    from_plan_version_id=from_version_id,
                    to_plan_version_id=plan_version_id,
                    publish_event_id=publish_event_id,
                )
            else:
                grace_ends_at = None
                if request.grace_period_days is not None:
                    grace_ends_at = published_at + timedelta(
                        days=request.grace_period_days
                    )
                migration_rows = await self._create_migration_rows_for_subscribers(
                    from_plan_version_id=from_version_id,
                    to_plan_version_id=plan_version_id,
                    publish_event_id=publish_event_id,
                    grace_period_ends_at=grace_ends_at,
                )

        logger.info(
            "Published plan version %s (from=%s, migrations=%s, immediate=%s)",
            plan_version_id,
            from_version_id,
            migration_rows,
            migrated_immediately,
        )

        return PlanVersionPublishResult(
            plan_version_id=plan_version_id,
            from_plan_version_id=from_version_id,
            publish_event_id=publish_event_id,
            stripe_price_id=stripe_price_id,
            migration_rows_created=migration_rows,
            subscribers_migrated_immediately=migrated_immediately,
            published_at=published_at,
        )

    def _validate_publish_request(self, request: PlanVersionPublishRequest) -> None:
        """Validate migration policy fields."""
        if request.migration_mode in (
            MigrationMode.GRACE_THEN_OPTIONAL,
            MigrationMode.GRACE_THEN_REQUIRED,
        ):
            if request.grace_period_days is None:
                raise ValueError(
                    "grace_period_days is required for grace-based migration modes"
                )

    async def _get_plan_version(self, plan_version_id: UUID) -> dict[str, Any]:
        """Fetch a plan version row by primary key."""
        result = (
            self.supabase.table("plan_versions")
            .select("*")
            .eq("id", str(plan_version_id))
            .single()
            .execute()
        )
        if not result.data:
            raise ValueError(f"Plan version {plan_version_id} not found")
        return result.data

    async def _get_plan_version_by_stripe_price_id(
        self, stripe_price_id: str
    ) -> Optional[dict[str, Any]]:
        """Look up a plan version by Stripe price ID."""
        result = (
            self.supabase.table("plan_versions")
            .select("*")
            .eq("stripe_price_id", stripe_price_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def _get_current_signup_version_for_product(
        self, plan_product_id: UUID
    ) -> Optional[dict[str, Any]]:
        """Return the version currently marked for new signups on a product."""
        result = (
            self.supabase.table("plan_versions")
            .select("*")
            .eq("plan_product_id", str(plan_product_id))
            .eq("is_current_for_signup", True)
            .eq("status", PlanVersionStatus.PUBLISHED.value)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def _ensure_stripe_price(self, draft: dict[str, Any]) -> Optional[str]:
        """Return a Stripe Price ID when the draft's billing mode requires it.

        Free versions may retain optional Stripe catalog metadata, but publishing
        them must never create a Stripe Price or require a Stripe Product.
        """
        existing = draft.get("stripe_price_id")

        if draft.get("billing_mode", BillingMode.PAID.value) == BillingMode.FREE.value:
            return str(existing) if existing else None

        if existing:
            return str(existing)

        product_id = draft.get("stripe_product_id")
        if not product_id:
            product = (
                self.supabase.table("plan_products")
                .select("stripe_product_id")
                .eq("id", str(draft["plan_product_id"]))
                .single()
                .execute()
            )
            if product.data:
                product_id = product.data.get("stripe_product_id")

        if not product_id:
            raise ValueError(
                "Stripe Product ID is required before publish. "
                "Auto-create may have failed — save prod_… on the draft or plan product, then publish again."
            )

        interval = draft.get("billing_interval", "monthly")
        stripe_interval = "year" if interval == "annual" else "month"

        metadata = {
            "plan_version_id": str(draft["id"]),
            "plan_product_id": str(draft["plan_product_id"]),
        }

        try:
            price = await stripe_service.create_price(
                product_id=str(product_id),
                unit_amount=int(draft.get("price_amount_cents", 0)),
                currency=str(draft.get("currency", "USD")),
                interval=stripe_interval,
                metadata=metadata,
            )
            return price.id
        except Exception as exc:
            raise ValueError(
                f"Failed to auto-create Stripe Price: {exc}. "
                "Create price_… in Stripe Dashboard, save it on the draft, and publish again."
            ) from exc

    async def _update_plan_version(
        self, plan_version_id: UUID, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Update plan version columns and return the updated row."""
        result = (
            self.supabase.table("plan_versions")
            .update(fields)
            .eq("id", str(plan_version_id))
            .execute()
        )
        if not result.data:
            raise ValueError(f"Failed to update plan version {plan_version_id}")
        return result.data[0]

    async def _create_publish_event(
        self,
        *,
        from_plan_version_id: Optional[UUID],
        to_plan_version_id: UUID,
        request: PlanVersionPublishRequest,
        published_by: UUID,
        published_at: datetime,
    ) -> dict[str, Any]:
        """Insert a plan_version_publish_events audit row."""
        row = {
            "from_plan_version_id": (
                str(from_plan_version_id) if from_plan_version_id else None
            ),
            "to_plan_version_id": str(to_plan_version_id),
            "migration_mode": request.migration_mode.value,
            "grace_period_days": request.grace_period_days,
            "auto_migrate_on_expiry": request.auto_migrate_on_expiry,
            "allow_indefinite_legacy": request.allow_indefinite_legacy,
            "stripe_migration_timing": request.stripe_migration_timing.value,
            "compliance_policy": request.compliance_policy,
            "published_by": str(published_by),
            "published_at": published_at.isoformat(),
        }
        result = (
            self.supabase.table("plan_version_publish_events").insert(row).execute()
        )
        if not result.data:
            raise ValueError("Failed to create plan version publish event")
        return result.data[0]

    async def _create_migration_rows_for_subscribers(
        self,
        *,
        from_plan_version_id: UUID,
        to_plan_version_id: UUID,
        publish_event_id: UUID,
        grace_period_ends_at: Optional[datetime],
    ) -> int:
        """Create pending migration rows for active subs on the legacy version."""
        subs_result = (
            self.supabase.table("organization_subscriptions")
            .select("id")
            .eq("plan_version_id", str(from_plan_version_id))
            .eq("status", "active")
            .execute()
        )
        subscribers = subs_result.data or []
        if not subscribers:
            return 0

        grace_iso = grace_period_ends_at.isoformat() if grace_period_ends_at else None
        status = "grace_active" if grace_period_ends_at else "pending"

        rows = [
            {
                "organization_subscription_id": sub["id"],
                "publish_event_id": str(publish_event_id),
                "from_plan_version_id": str(from_plan_version_id),
                "to_plan_version_id": str(to_plan_version_id),
                "status": status,
                "grace_period_ends_at": grace_iso,
            }
            for sub in subscribers
        ]

        result = (
            self.supabase.table("organization_subscription_migrations")
            .insert(rows)
            .execute()
        )
        return len(result.data or rows)

    async def _migrate_subscribers_immediately(
        self,
        *,
        from_plan_version_id: UUID,
        to_plan_version_id: UUID,
        publish_event_id: UUID,
    ) -> int:
        """Immediately update active subscribers to the new plan version."""
        subs_result = (
            self.supabase.table("organization_subscriptions")
            .select("id, organization_id")
            .eq("plan_version_id", str(from_plan_version_id))
            .eq("status", "active")
            .execute()
        )
        subscribers = subs_result.data or []
        if not subscribers:
            return 0

        to_version = await self._get_plan_version(to_plan_version_id)
        legacy_plan_id = to_version.get("legacy_subscription_plan_id")
        now_iso = datetime.now(timezone.utc).isoformat()

        for sub in subscribers:
            update_fields: dict[str, Any] = {
                "plan_version_id": str(to_plan_version_id),
                "updated_at": now_iso,
            }
            if legacy_plan_id:
                update_fields["subscription_plan_id"] = str(legacy_plan_id)

            self.supabase.table("organization_subscriptions").update(update_fields).eq(
                "id", sub["id"]
            ).execute()

            self.supabase.table("organization_subscription_migrations").insert(
                {
                    "organization_subscription_id": sub["id"],
                    "publish_event_id": str(publish_event_id),
                    "from_plan_version_id": str(from_plan_version_id),
                    "to_plan_version_id": str(to_plan_version_id),
                    "status": "migrated",
                    "migrated_at": now_iso,
                    "migration_type": "auto",
                }
            ).execute()

        return len(subscribers)


plan_version_service = PlanVersionService()
