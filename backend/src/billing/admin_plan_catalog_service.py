"""
Platform-admin CRUD for plan products, versions, and entitlement catalog.

Draft versions are editable; published versions are immutable (clone to edit).
Publish flow delegates to ``PlanVersionService.publish_plan_version``.

See ``docs/03_implementation/plan_entitlements_and_limits.md`` §10.3.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from shared.config import supabase_config

from .admin_plan_models import (
    EntitlementDefinitionUpdate,
    PlanProduct,
    PlanProductCreate,
    PlanProductWithVersions,
    PlanVersionDetail,
    PlanVersionDraftCreate,
    PlanVersionDraftUpdate,
    PlanVersionEntitlement,
    PlanVersionEntitlementInput,
)
from .entitlement_models import EntitlementDefinition
from .plan_version_models import PlanVersionStatus

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
            versions = await self._list_versions_for_product(UUID(str(product["id"])))
            output.append(PlanProductWithVersions(**product, versions=versions))
        return output

    async def create_plan_product(self, data: PlanProductCreate) -> PlanProduct:
        """Create a new plan product family."""
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
        return PlanProduct(**result.data[0])

    async def create_draft_version(
        self, product_id: UUID, data: PlanVersionDraftCreate
    ) -> PlanVersionDetail:
        """Create a new draft version for a product."""
        await self._get_product(product_id)
        version_number = await self._next_version_number(product_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        version_row = {
            "plan_product_id": str(product_id),
            "version_number": version_number,
            "status": PlanVersionStatus.DRAFT.value,
            "display_label": data.display_label,
            "price_amount_cents": data.price_amount_cents,
            "currency": data.currency.upper(),
            "billing_interval": data.billing_interval,
            "trial_period_days": data.trial_period_days,
            "stripe_product_id": data.stripe_product_id,
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

    async def clone_plan_version(
        self,
        source_version_id: UUID,
        *,
        display_label: Optional[str] = None,
        price_amount_cents: Optional[int] = None,
    ) -> PlanVersionDetail:
        """Clone a version (any status) into a new draft with incremented version number."""
        source = await self.get_plan_version(source_version_id)
        entitlements = [
            PlanVersionEntitlementInput(
                entitlement_key=e.entitlement_key, value=e.value
            )
            for e in source.entitlements
        ]
        create_data = PlanVersionDraftCreate(
            display_label=display_label or source.display_label,
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
        if "currency" in fields:
            fields["currency"] = str(fields["currency"]).upper()
        if fields:
            fields["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.supabase.table("plan_versions").update(fields).eq(
                "id", str(version_id)
            ).execute()

        if data.entitlements is not None:
            await self._replace_entitlements(version_id, data.entitlements)

        return await self.get_plan_version(version_id)

    async def _list_versions_for_product(
        self, product_id: UUID
    ) -> list[PlanVersionDetail]:
        """List all versions for a product ordered by version_number desc."""
        result = (
            self.supabase.table("plan_versions")
            .select("*")
            .eq("plan_product_id", str(product_id))
            .order("version_number", desc=True)
            .execute()
        )
        versions: list[PlanVersionDetail] = []
        for row in result.data or []:
            vid = UUID(str(row["id"]))
            entitlements = await self._get_entitlements_for_version(vid)
            versions.append(PlanVersionDetail(**row, entitlements=entitlements))
        return versions

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
            .execute()
        )
        return [PlanVersionEntitlement(**row) for row in (result.data or [])]

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
            }
            for item in entitlements
        ]
        self.supabase.table("plan_version_entitlements").insert(rows).execute()


admin_plan_catalog_service = AdminPlanCatalogService()
