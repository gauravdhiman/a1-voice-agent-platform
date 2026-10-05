"""
Plan-version migration execution and grace-period scheduling.

Handles self-service migration, daily auto-migration when grace expires, and
migration status for the billing UI. Entitlements always follow
``organization_subscriptions.plan_version_id`` after migration completes.

See ``docs/03_implementation/plan_entitlements_and_limits.md`` §6.3–6.4.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from opentelemetry import trace

from shared.config import supabase_config

from .entitlement_models import (
    OrgPlanMigrationInfo,
    PlanMigrationRunResult,
    PlanMigrationStatus,
)
from .stripe_service import stripe_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

ACTIVE_MIGRATION_STATUSES = frozenset(
    {
        PlanMigrationStatus.PENDING.value,
        PlanMigrationStatus.GRACE_ACTIVE.value,
    }
)


class PlanMigrationService:
    """Process plan-version migrations for legacy subscribers."""

    def __init__(self) -> None:
        self.supabase = supabase_config.client

    @tracer.start_as_current_span("billing.migration.get_active_for_org")
    async def get_active_migration_for_organization(
        self, organization_id: UUID
    ) -> Optional[OrgPlanMigrationInfo]:
        """Return active migration/grace info for an organization, if any."""
        row = await self._get_active_migration_for_subscription_org(organization_id)
        if not row:
            return None

        publish_event = row.get("plan_version_publish_events") or {}
        target_label, target_slug = await self._get_plan_version_display(
            UUID(str(row["to_plan_version_id"]))
        )

        return OrgPlanMigrationInfo(
            migration_id=UUID(str(row["id"])),
            from_plan_version_id=UUID(str(row["from_plan_version_id"])),
            to_plan_version_id=UUID(str(row["to_plan_version_id"])),
            status=PlanMigrationStatus(row["status"]),
            grace_period_ends_at=row.get("grace_period_ends_at"),
            target_plan_version_label=target_label,
            target_plan_product_slug=target_slug,
            allow_indefinite_legacy=bool(
                publish_event.get("allow_indefinite_legacy", True)
            ),
            can_self_migrate=True,
        )

    @tracer.start_as_current_span("billing.migration.migrate_organization")
    async def migrate_organization(self, organization_id: UUID) -> dict[str, Any]:
        """Self-service migrate an organization to the target plan version.

        Args:
            organization_id: Organization UUID requesting migration.

        Returns:
            Dict with migration_id and to_plan_version_id.

        Raises:
            ValueError: When no active migration exists for the organization.
        """
        row = await self._get_active_migration_for_subscription_org(organization_id)
        if not row:
            raise ValueError(
                f"No active plan migration available for organization {organization_id}"
            )

        await self._execute_migration(row, migration_type="self_service")
        return {
            "migration_id": row["id"],
            "to_plan_version_id": row["to_plan_version_id"],
            "status": PlanMigrationStatus.MIGRATED.value,
        }

    @tracer.start_as_current_span("billing.migration.process_due")
    async def process_due_migrations(self) -> PlanMigrationRunResult:
        """Process grace-period migrations whose deadline has passed.

        Called by the daily background scheduler. Only migrates rows tied to
        publish events with ``auto_migrate_on_expiry=true``.

        Returns:
            PlanMigrationRunResult with counts of processed/migrated/skipped rows.
        """
        due_rows = await self._fetch_due_migrations()
        result = PlanMigrationRunResult()

        for row in due_rows:
            result.processed += 1
            publish_event = row.get("plan_version_publish_events") or {}
            if not publish_event.get("auto_migrate_on_expiry"):
                result.skipped += 1
                continue

            try:
                await self._execute_migration(row, migration_type="auto")
                result.migrated += 1
            except Exception as exc:
                result.errors += 1
                logger.error(
                    "Failed auto-migration %s: %s",
                    row.get("id"),
                    exc,
                    exc_info=True,
                )

        if result.processed:
            logger.info(
                "Plan migration job: processed=%s migrated=%s skipped=%s errors=%s",
                result.processed,
                result.migrated,
                result.skipped,
                result.errors,
            )

        return result

    async def _get_active_migration_for_subscription_org(
        self, organization_id: UUID
    ) -> Optional[dict[str, Any]]:
        """Fetch the active migration row for an organization."""
        result = (
            self.supabase.table("organization_subscription_migrations")
            .select(
                "*, organization_subscriptions!inner(id, organization_id, "
                "stripe_subscription_id, plan_version_id, status, metadata, "
                "pending_plan_transition), "
                "plan_version_publish_events(*)"
            )
            .eq("organization_subscriptions.organization_id", str(organization_id))
            .in_("status", list(ACTIVE_MIGRATION_STATUSES))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def _fetch_due_migrations(self) -> list[dict[str, Any]]:
        """Return grace_active migrations past grace_period_ends_at."""
        now_iso = datetime.now(timezone.utc).isoformat()
        result = (
            self.supabase.table("organization_subscription_migrations")
            .select(
                "*, organization_subscriptions(id, organization_id, "
                "stripe_subscription_id, plan_version_id, status, metadata, "
                "pending_plan_transition), "
                "plan_version_publish_events(*)"
            )
            .eq("status", PlanMigrationStatus.GRACE_ACTIVE.value)
            .lte("grace_period_ends_at", now_iso)
            .execute()
        )
        return result.data or []

    async def _execute_migration(
        self,
        migration_row: dict[str, Any],
        *,
        migration_type: str,
    ) -> None:
        """Apply a migration: update subscription plan_version_id and Stripe."""
        # Lazy import avoids the billing service -> entitlement service -> plan
        # migration import cycle during application startup.
        from .versioned_subscription_service import (
            PlanChangeInProgressError,
            versioned_subscription_service,
        )

        subscription = migration_row.get("organization_subscriptions") or {}
        publish_event = migration_row.get("plan_version_publish_events") or {}
        to_version_id = UUID(str(migration_row["to_plan_version_id"]))
        from_version_id = UUID(str(migration_row["from_plan_version_id"]))
        migration_id = migration_row["id"]
        now_iso = datetime.now(timezone.utc).isoformat()

        sub_id = subscription.get("id")
        if not sub_id:
            raise ValueError(f"Migration {migration_id} missing subscription reference")

        scheduled_marker = (subscription.get("metadata") or {}).get(
            "pending_plan_change"
        ) or {}
        if scheduled_marker.get("status") == "scheduled":
            if str(scheduled_marker.get("target_plan_version_id")) == str(
                to_version_id
            ):
                self._mark_migration_complete(migration_id, migration_type, now_iso)
                return
            raise PlanChangeInProgressError(
                "A different plan change is already scheduled. Retry migration "
                "after it takes effect."
            )

        if subscription.get("pending_plan_transition"):
            reconciled = (
                await versioned_subscription_service.reconcile_pending_plan_transition(
                    subscription
                )
            )
            if not reconciled:
                raise PlanChangeInProgressError(
                    "A plan change is still being processed. Retry migration after "
                    "its payment is confirmed."
                )
            refreshed = (
                self.supabase.table("organization_subscriptions")
                .select("*")
                .eq("id", str(sub_id))
                .execute()
            )
            rows = refreshed.data or []
            if rows and str(rows[0].get("plan_version_id")) == str(to_version_id):
                self._mark_migration_complete(migration_id, migration_type, now_iso)
                return

        if str(subscription.get("plan_version_id")) == str(to_version_id):
            self._mark_migration_complete(migration_id, migration_type, now_iso)
            return

        to_version = await self._get_plan_version(to_version_id)
        from_version = await self._get_plan_version(from_version_id)
        legacy_plan_id = to_version.get("legacy_subscription_plan_id")
        stripe_price_id = to_version.get("stripe_price_id")
        stripe_sub_id = subscription.get("stripe_subscription_id")
        stripe_timing = publish_event.get("stripe_migration_timing", "immediate")
        should_update_stripe = (
            stripe_sub_id
            and stripe_price_id
            and (
                migration_type == "self_service"
                or stripe_timing in ("immediate", "at_grace_end")
            )
        )
        at_period_end = stripe_timing == "at_period_end"
        interval_changed = (
            bool(should_update_stripe)
            and not at_period_end
            and from_version.get("billing_interval")
            != to_version.get("billing_interval")
        )
        transition = {
            "transition_id": str(migration_id),
            "source_plan_version_id": str(from_version_id),
            "target_plan_version_id": str(to_version_id),
            "target_billing_mode": to_version.get("billing_mode"),
            "source_price_id": from_version.get("stripe_price_id"),
            "target_price_id": stripe_price_id,
            "billing_interval_changed": interval_changed,
            "effective_mode": "scheduled" if at_period_end else "immediate",
            "effective_at": publish_event.get("effective_at")
            or subscription.get("current_period_end"),
            "operation": "migration",
            "status": "awaiting_invoice" if interval_changed else "applying",
        }
        if not versioned_subscription_service.claim_plan_transition(sub_id, transition):
            raise PlanChangeInProgressError(
                "A plan change is already being processed. Retry migration after "
                "it completes."
            )

        try:
            if should_update_stripe:
                await stripe_service.change_subscription_price(
                    stripe_sub_id,
                    str(stripe_price_id),
                    at_period_end=at_period_end,
                )

            update_fields: dict[str, Any] = {
                "plan_version_id": str(to_version_id),
                "updated_at": now_iso,
            }
            if at_period_end:
                metadata = dict(subscription.get("metadata") or {})
                metadata["pending_plan_change"] = {
                    "transition_id": str(migration_id),
                    "target_plan_version_id": str(to_version_id),
                    "target_billing_mode": to_version.get("billing_mode"),
                    "effective_at": transition["effective_at"],
                    "status": "scheduled",
                }
                update_fields["metadata"] = metadata
            if legacy_plan_id:
                update_fields["subscription_plan_id"] = str(legacy_plan_id)
            self.supabase.table("organization_subscriptions").update(update_fields).eq(
                "id", sub_id
            ).execute()

            self._mark_migration_complete(migration_id, migration_type, now_iso)
            if not interval_changed:
                versioned_subscription_service.clear_plan_transition(
                    sub_id, migration_id
                )
        except Exception:
            await versioned_subscription_service.reconcile_pending_plan_transition(
                {
                    **subscription,
                    "pending_plan_transition": transition,
                }
            )
            raise

        logger.info(
            "Migrated subscription %s from version %s to %s (%s)",
            sub_id,
            from_version_id,
            to_version_id,
            migration_type,
        )

    def _mark_migration_complete(
        self, migration_id: str, migration_type: str, timestamp: str
    ) -> None:
        """Mark a migration complete after its Stripe/local state is reconciled."""
        self.supabase.table("organization_subscription_migrations").update(
            {
                "status": PlanMigrationStatus.MIGRATED.value,
                "migrated_at": timestamp,
                "migration_type": migration_type,
            }
        ).eq("id", migration_id).execute()

    async def _get_plan_version(self, plan_version_id: UUID) -> dict[str, Any]:
        """Fetch plan version row."""
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

    async def _get_plan_version_display(
        self, plan_version_id: UUID
    ) -> tuple[Optional[str], Optional[str]]:
        """Return a customer-facing label and stable product slug."""
        result = (
            self.supabase.table("plan_versions")
            .select("version_number, display_label, plan_products(display_name, slug)")
            .eq("id", str(plan_version_id))
            .single()
            .execute()
        )
        if not result.data:
            return None, None
        row = result.data
        product = row.get("plan_products") or {}
        slug = product.get("slug")
        if row.get("display_label"):
            return row["display_label"], slug
        name = product.get("display_name", "Plan")
        return f"{name} v{row.get('version_number', 1)}", slug


plan_migration_service = PlanMigrationService()
