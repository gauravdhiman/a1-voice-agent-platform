"""
Platform-admin CRUD for plan products, versions, and entitlement catalog.

Draft versions are editable; published entitlement values are immutable while
their display order remains administratively maintainable. Publish flow delegates
to ``PlanVersionService.publish_plan_version``.

See ``docs/03_implementation/plan_entitlements_and_limits.md`` §10.3.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from shared.config import supabase_config

from .admin_plan_models import (
    CreditEventAdminUpdate,
    EntitlementDefinitionUpdate,
    PlanProduct,
    PlanProductCreate,
    PlanProductCreateResult,
    PlanProductStripeUpdate,
    PlanProductWithVersions,
    PlanVersionDetail,
    PlanVersionDraftCreate,
    PlanVersionDraftUpdate,
    PlanVersionEntitlement,
    PlanVersionEntitlementInput,
    PlanVersionSummary,
)
from .entitlement_models import EntitlementDefinition
from .models import CreditEvent
from .plan_version_models import BillingMode, PlanVersionStatus
from .stripe_service import stripe_service
from .system_pricing import SYSTEM_PRICING_EVENT_NAMES, get_system_pricing_definition

logger = logging.getLogger(__name__)


class AdminPlanCatalogService:
    """Manage plan catalog and draft versions for platform administrators."""

    def __init__(self) -> None:
        self.supabase = supabase_config.client

    async def list_entitlement_definitions(
        self, *, active_only: bool = False
    ) -> list[EntitlementDefinition]:
        """List entitlement catalog entries."""
        query = self.supabase.table("entitlement_definitions").select("*")
        if active_only:
            query = query.eq("is_active", True)
        result = query.order("key").execute()
        return [EntitlementDefinition(**row) for row in (result.data or [])]

    async def update_entitlement_definition(
        self, key: str, update: EntitlementDefinitionUpdate
    ) -> EntitlementDefinition:
        """Update display metadata on a catalog definition."""
        fields = {
            k: v
            for k, v in update.model_dump(exclude_unset=True).items()
            if v is not None
        }
        if not fields:
            raise ValueError("No fields to update")
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = (
            self.supabase.table("entitlement_definitions")
            .update(fields)
            .eq("key", key)
            .execute()
        )
        if not result.data:
            raise ValueError(f"Entitlement definition '{key}' not found")
        return EntitlementDefinition(**result.data[0])

    async def list_credit_events(self) -> list[CreditEvent]:
        """List the finite set of configurable system usage prices."""
        result = (
            self.supabase.table("credit_events")
            .select("*")
            .in_("name", list(SYSTEM_PRICING_EVENT_NAMES))
            .order("category")
            .order("name")
            .execute()
        )
        rows_by_name = {row["name"]: row for row in (result.data or [])}
        return [
            CreditEvent(**rows_by_name[name])
            for name in SYSTEM_PRICING_EVENT_NAMES
            if name in rows_by_name
        ]

    async def update_credit_event(
        self, name: str, update: CreditEventAdminUpdate
    ) -> CreditEvent:
        """Update the rate and description of one system pricing event."""
        definition = get_system_pricing_definition(name)
        fields = {
            key: value
            for key, value in update.model_dump(exclude_unset=True).items()
            if value is not None
        }
        if not fields:
            raise ValueError("No fields to update")

        # Keep this validation close to the write path so a handcrafted API
        # request cannot change the runtime-owned meter semantics.
        fields["meter_type"] = definition.meter_type
        fields["billing_unit"] = definition.billing_unit
        fields["is_active"] = True

        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = (
            self.supabase.table("credit_events")
            .update(fields)
            .eq("name", name)
            .execute()
        )
        if not result.data:
            raise ValueError(f"Credit event '{name}' not found")
        return CreditEvent(**result.data[0])

    async def list_plan_products(
        self, *, include_versions: bool = True
    ) -> list[PlanProductWithVersions]:
        """List plan products with optional nested versions."""
        products_result = (
            self.supabase.table("plan_products")
            .select("*")
            .order("sort_order")
            .execute()
        )
        products = products_result.data or []
        if not include_versions:
            return [PlanProductWithVersions(**p, versions=[]) for p in products]

        output: list[PlanProductWithVersions] = []
        for product in products:
            versions = await self._list_version_summaries_for_product(
                UUID(str(product["id"]))
            )
            output.append(PlanProductWithVersions(**product, versions=versions))
        return output

    async def create_plan_product(
        self, data: PlanProductCreate
    ) -> PlanProductCreateResult:
        """Create a plan product, linking Stripe only for paid product families."""
        slug = data.slug.strip().lower()
        row = {
            "slug": slug,
            "display_name": data.display_name,
            "description": data.description,
            "sort_order": data.sort_order,
            "is_active": True,
        }
        result = self.supabase.table("plan_products").insert(row).execute()
        if not result.data:
            raise ValueError("Failed to create plan product")

        product_row = result.data[0]
        product_id = UUID(str(product_row["id"]))
        stripe_auto_create_error: Optional[str] = None

        if slug != "free":
            try:
                stripe_product = await stripe_service.create_product(
                    data.display_name,
                    metadata={
                        "plan_product_id": str(product_id),
                        "plan_product_slug": slug,
                    },
                )
                product_row = await self._update_plan_product_fields(
                    product_id,
                    {"stripe_product_id": stripe_product.id},
                )
            except ValueError as exc:
                stripe_auto_create_error = str(exc)
                logger.warning(
                    "Plan product %s created without Stripe Product: %s",
                    product_id,
                    exc,
                )
            except Exception as exc:
                stripe_auto_create_error = (
                    f"Stripe Product auto-create failed: {exc}. "
                    "Link prod_… manually from the plan catalog."
                )
                logger.warning(
                    "Plan product %s created without Stripe Product: %s",
                    product_id,
                    exc,
                    exc_info=True,
                )

        return PlanProductCreateResult(
            product=PlanProduct(**product_row),
            stripe_auto_create_error=stripe_auto_create_error,
        )

    async def update_plan_product_stripe(
        self, product_id: UUID, update: PlanProductStripeUpdate
    ) -> PlanProduct:
        """Manually link a Stripe Product ID after auto-create failed."""
        await self._get_product(product_id)
        stripe_product_id = update.stripe_product_id.strip()
        if not stripe_product_id.startswith("prod_"):
            raise ValueError("Stripe product ID must start with prod_")

        row = await self._update_plan_product_fields(
            product_id,
            {"stripe_product_id": stripe_product_id},
        )

        # Propagate to open drafts missing a product ID.
        self.supabase.table("plan_versions").update(
            {"stripe_product_id": stripe_product_id}
        ).eq("plan_product_id", str(product_id)).eq(
            "status", PlanVersionStatus.DRAFT.value
        ).is_(
            "stripe_product_id", "null"
        ).execute()

        return PlanProduct(**row)

    async def _get_draft_version_for_product(
        self, product_id: UUID
    ) -> Optional[dict[str, Any]]:
        """Return the existing draft row for a product, if any."""
        result = (
            self.supabase.table("plan_versions")
            .select("id, version_number, display_label")
            .eq("plan_product_id", str(product_id))
            .eq("status", PlanVersionStatus.DRAFT.value)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def _ensure_no_existing_draft(self, product_id: UUID) -> None:
        """Reject creating a second draft for the same plan product."""
        existing = await self._get_draft_version_for_product(product_id)
        if existing is not None:
            label = (
                existing.get("display_label") or f"v{existing.get('version_number')}"
            )
            raise ValueError(
                f"Plan product already has draft {label}. "
                "Publish or delete the existing draft before creating another."
            )

    async def create_draft_version(
        self, product_id: UUID, data: PlanVersionDraftCreate
    ) -> PlanVersionDetail:
        """Create a new draft version for a product."""
        await self._get_product(product_id)
        await self._ensure_no_existing_draft(product_id)
        version_number = await self._next_version_number(product_id)
        product = await self._get_product(product_id)
        inherited_stripe_product_id = (
            data.stripe_product_id or product.get("stripe_product_id")
            if data.billing_mode == BillingMode.PAID
            else None
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        version_row = {
            "plan_product_id": str(product_id),
            "version_number": version_number,
            "status": PlanVersionStatus.DRAFT.value,
            "display_label": data.display_label,
            "billing_mode": data.billing_mode.value,
            "credit_grant_policy": data.credit_grant_policy.value,
            "price_amount_cents": data.price_amount_cents,
            "currency": data.currency.upper(),
            "billing_interval": data.billing_interval,
            "trial_period_days": data.trial_period_days,
            "stripe_product_id": inherited_stripe_product_id,
            "is_current_for_signup": False,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        result = self.supabase.table("plan_versions").insert(version_row).execute()
        if not result.data:
            raise ValueError("Failed to create draft plan version")
        version_id = UUID(str(result.data[0]["id"]))
        if data.entitlements:
            await self._replace_entitlements(version_id, data.entitlements)
        return await self.get_plan_version(version_id)

    async def delete_draft_version(self, version_id: UUID) -> None:
        """Delete an unpublished draft version and its entitlement rows."""
        current = await self.get_plan_version(version_id)
        if current.status != PlanVersionStatus.DRAFT:
            raise ValueError(
                f"Plan version {version_id} is not draft (status={current.status})"
            )

        self.supabase.table("plan_version_entitlements").delete().eq(
            "plan_version_id", str(version_id)
        ).execute()
        result = (
            self.supabase.table("plan_versions")
            .delete()
            .eq("id", str(version_id))
            .eq("status", PlanVersionStatus.DRAFT.value)
            .execute()
        )
        if not result.data:
            raise ValueError(f"Failed to delete draft plan version {version_id}")

    async def clone_plan_version(
        self,
        source_version_id: UUID,
        *,
        display_label: Optional[str] = None,
        price_amount_cents: Optional[int] = None,
    ) -> PlanVersionDetail:
        """Clone a version (any status) into a new draft with incremented version number."""
        source = await self.get_plan_version(source_version_id)
        await self._ensure_no_existing_draft(source.plan_product_id)
        entitlements = [
            PlanVersionEntitlementInput(
                entitlement_key=e.entitlement_key,
                value=e.value,
                display_order=e.display_order,
            )
            for e in source.entitlements
        ]
        create_data = PlanVersionDraftCreate(
            display_label=display_label or source.display_label,
            billing_mode=source.billing_mode,
            credit_grant_policy=source.credit_grant_policy,
            price_amount_cents=(
                price_amount_cents
                if price_amount_cents is not None
                else source.price_amount_cents
            ),
            currency=source.currency,
            billing_interval=source.billing_interval,
            trial_period_days=source.trial_period_days,
            stripe_product_id=source.stripe_product_id,
            entitlements=entitlements,
        )
        return await self.create_draft_version(source.plan_product_id, create_data)

    async def get_plan_version(self, version_id: UUID) -> PlanVersionDetail:
        """Fetch plan version detail with entitlements."""
        result = (
            self.supabase.table("plan_versions")
            .select("*")
            .eq("id", str(version_id))
            .single()
            .execute()
        )
        if not result.data:
            raise ValueError(f"Plan version {version_id} not found")
        entitlements = await self._get_entitlements_for_version(version_id)
        return PlanVersionDetail(**result.data, entitlements=entitlements)

    async def update_draft_version(
        self, version_id: UUID, data: PlanVersionDraftUpdate
    ) -> PlanVersionDetail:
        """Update a draft plan version and its entitlements."""
        current = await self.get_plan_version(version_id)
        if current.status != PlanVersionStatus.DRAFT:
            raise ValueError(
                f"Plan version {version_id} is not draft (status={current.status})"
            )

        fields: dict[str, Any] = {
            k: v
            for k, v in data.model_dump(
                exclude_unset=True, exclude={"entitlements"}
            ).items()
            if v is not None
        }
        if (
            fields.get("billing_mode", current.billing_mode.value)
            == BillingMode.FREE.value
        ):
            fields["stripe_product_id"] = None
            fields["stripe_price_id"] = None
        if "currency" in fields:
            fields["currency"] = str(fields["currency"]).upper()
        if fields:
            fields["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.supabase.table("plan_versions").update(fields).eq(
                "id", str(version_id)
            ).execute()

            if "stripe_product_id" in fields and fields["stripe_product_id"]:
                await self._update_plan_product_fields(
                    current.plan_product_id,
                    {"stripe_product_id": fields["stripe_product_id"]},
                )

        if data.entitlements is not None:
            await self._replace_entitlements(version_id, data.entitlements)

        return await self.get_plan_version(version_id)

    async def reorder_plan_version_entitlements(
        self, version_id: UUID, ordered_keys: list[str]
    ) -> PlanVersionDetail:
        """Change entitlement presentation order without changing membership or values.

        Draft editors normally persist order with their regular save request. This
        focused operation is used by the published-version UI so published plan
        values remain immutable while card presentation can still be maintained.

        Args:
            version_id: Plan version whose entitlement order should change.
            ordered_keys: Every currently assigned entitlement key exactly once,
                in the desired card display order.

        Returns:
            The updated plan version detail with entitlements in display order.

        Raises:
            ValueError: If the version is missing or the requested keys do not
                exactly match the version's current entitlement membership.
        """
        current = await self.get_plan_version(version_id)
        current_keys = [
            entitlement.entitlement_key for entitlement in current.entitlements
        ]
        if len(ordered_keys) != len(set(ordered_keys)):
            raise ValueError("Entitlement order must not contain duplicate keys")
        if set(ordered_keys) != set(current_keys):
            raise ValueError(
                "Entitlement order must include exactly the entitlements on this version"
            )

        row_by_key = {
            entitlement.entitlement_key: entitlement
            for entitlement in current.entitlements
        }
        for display_order, key in enumerate(ordered_keys):
            self.supabase.table("plan_version_entitlements").update(
                {"display_order": display_order}
            ).eq("id", str(row_by_key[key].id)).execute()

        return await self.get_plan_version(version_id)

    async def _list_version_summaries_for_product(
        self, product_id: UUID
    ) -> list[PlanVersionSummary]:
        """List version metadata for a product without entitlement rows."""
        result = (
            self.supabase.table("plan_versions")
            .select("*")
            .eq("plan_product_id", str(product_id))
            .order("version_number", desc=True)
            .execute()
        )
        return [PlanVersionSummary(**row) for row in (result.data or [])]

    async def _get_product(self, product_id: UUID) -> dict[str, Any]:
        result = (
            self.supabase.table("plan_products")
            .select("*")
            .eq("id", str(product_id))
            .single()
            .execute()
        )
        if not result.data:
            raise ValueError(f"Plan product {product_id} not found")
        return result.data

    async def _update_plan_product_fields(
        self, product_id: UUID, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Update plan product columns and return the updated row."""
        payload = {
            **fields,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = (
            self.supabase.table("plan_products")
            .update(payload)
            .eq("id", str(product_id))
            .execute()
        )
        if not result.data:
            raise ValueError(f"Failed to update plan product {product_id}")
        return result.data[0]

    async def _next_version_number(self, product_id: UUID) -> int:
        result = (
            self.supabase.table("plan_versions")
            .select("version_number")
            .eq("plan_product_id", str(product_id))
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return int(result.data[0]["version_number"]) + 1
        return 1

    async def _get_entitlements_for_version(
        self, version_id: UUID
    ) -> list[PlanVersionEntitlement]:
        result = (
            self.supabase.table("plan_version_entitlements")
            .select("*")
            .eq("plan_version_id", str(version_id))
            .order("display_order")
            .order("created_at")
            .execute()
        )
        rows = result.data or []
        # Keep legacy/test rows deterministic when the migration has not yet
        # added display_order to the returned shape.
        rows = sorted(
            enumerate(rows),
            key=lambda pair: (
                int(pair[1].get("display_order", pair[0])),
                pair[0],
            ),
        )
        return [PlanVersionEntitlement(**row) for _, row in rows]

    async def _replace_entitlements(
        self,
        version_id: UUID,
        entitlements: list[PlanVersionEntitlementInput],
    ) -> None:
        """Replace all entitlements on a draft version."""
        self.supabase.table("plan_version_entitlements").delete().eq(
            "plan_version_id", str(version_id)
        ).execute()
        if not entitlements:
            return
        rows = [
            {
                "plan_version_id": str(version_id),
                "entitlement_key": item.entitlement_key,
                "value": item.value,
                "display_order": display_order,
            }
            for display_order, item in enumerate(entitlements)
        ]
        self.supabase.table("plan_version_entitlements").insert(rows).execute()


admin_plan_catalog_service = AdminPlanCatalogService()
