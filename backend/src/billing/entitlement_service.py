"""
Entitlement resolution and limit enforcement for organization subscriptions.

Subscriptions bind to immutable ``plan_versions`` via
``organization_subscriptions.plan_version_id``. Enforcement reads the bound
version — never the latest catalog version — so grandfathering is preserved.

Cancellation policy (P9): while ``status`` is ``active`` or ``trial``, including
when ``cancel_at_period_end=true``, full plan entitlements apply until
``current_period_end``.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from opentelemetry import trace

from shared.config import supabase_config

from .entitlement_handlers import get_handler, parse_entitlement_value
from .entitlement_models import (
    EntitlementDefinition,
    EntitlementDenied,
    EntitlementKind,
    LimitCheckResult,
    OrgEntitlements,
    ResolvedEntitlement,
)
from .models import SubscriptionStatus
from .plan_migration_service import plan_migration_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

ACTIVE_SUBSCRIPTION_STATUSES = frozenset(
    {
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.TRIAL.value,
    }
)

FREE_PLAN_PRODUCT_SLUG = "free"


class EntitlementService:
    """Resolve and enforce plan-version entitlements per organization."""

    def __init__(self) -> None:
        self.supabase = supabase_config.client
        self._free_plan_version_id: Optional[UUID] = None
        self._definitions_cache: Optional[list[EntitlementDefinition]] = None

    @tracer.start_as_current_span("billing.entitlement.get_org_entitlements")
    async def get_org_entitlements(self, organization_id: UUID) -> OrgEntitlements:
        """Resolve full entitlement view for an organization."""
        subscription = await self._get_subscription(organization_id)
        definitions = await self._get_definitions()

        is_entitled = False
        cancel_at_period_end = False
        access_until: Optional[str] = None
        plan_version_id: UUID

        if subscription and subscription.get("status") in ACTIVE_SUBSCRIPTION_STATUSES:
            is_entitled = True
            cancel_at_period_end = bool(subscription.get("cancel_at_period_end"))
            access_until = subscription.get("current_period_end")
            raw_version_id = subscription.get("plan_version_id")
            if not raw_version_id:
                raise ValueError(
                    f"Active subscription for org {organization_id} missing plan_version_id"
                )
            plan_version_id = UUID(str(raw_version_id))
        else:
            plan_version_id = await self._resolve_free_plan_version_id()

        version_row = await self._get_plan_version(plan_version_id)
        product = version_row.get("plan_products") or {}
        assigned = await self._get_version_entitlements(plan_version_id)
        assigned_by_key = {row["entitlement_key"]: row["value"] for row in assigned}

        display_label = version_row.get("display_label")
        product_name = product.get("display_name", FREE_PLAN_PRODUCT_SLUG.title())
        version_number = int(version_row.get("version_number", 1))
        plan_version_label = display_label or f"{product_name} v{version_number}"
        is_legacy_version = not bool(version_row.get("is_current_for_signup", False))

        migration = await plan_migration_service.get_active_migration_for_organization(
            organization_id
        )
        if migration is not None:
            is_legacy_version = True

        limits: dict[str, ResolvedEntitlement] = {}
        features: dict[str, ResolvedEntitlement] = {}

        for definition in definitions:
            raw = assigned_by_key.get(definition.key)
            if raw is None and definition.default_when_absent is not None:
                raw = definition.default_when_absent
            effective, is_unlimited = parse_entitlement_value(raw)
            resolved = ResolvedEntitlement(
                key=definition.key,
                kind=definition.kind,
                assigned=definition.key in assigned_by_key,
                raw_value=raw,
                effective_value=effective,
                is_unlimited=is_unlimited,
            )
            if definition.kind == EntitlementKind.LIMIT:
                limits[definition.key] = resolved
            else:
                features[definition.key] = resolved

        return OrgEntitlements(
            organization_id=organization_id,
            plan_version_id=plan_version_id,
            plan_product_slug=product.get("slug", FREE_PLAN_PRODUCT_SLUG),
            plan_version_number=version_number,
            plan_version_label=plan_version_label,
            is_legacy_version=is_legacy_version,
            is_entitled=is_entitled,
            cancel_at_period_end=cancel_at_period_end,
            access_until=access_until,
            limits=limits,
            features=features,
            migration=migration,
        )

    @tracer.start_as_current_span("billing.entitlement.check_limit")
    async def check_limit(
        self,
        organization_id: UUID,
        limit_key: str,
        *,
        increment: int = 1,
    ) -> LimitCheckResult:
        """Check whether ``increment`` usage is allowed for ``limit_key``."""
        entitlements = await self.get_org_entitlements(organization_id)
        resolved = entitlements.limits.get(limit_key)
        if resolved is None:
            return LimitCheckResult(
                allowed=True,
                code=limit_key.upper(),
                message=f"Unknown limit '{limit_key}' — allowed by default.",
            )

        definitions = await self._get_definitions()
        definition = next((d for d in definitions if d.key == limit_key), None)
        if definition is None:
            return LimitCheckResult(allowed=True, code=limit_key.upper())

        handler = get_handler(
            definition.enforcement_handler, limit_key, supabase=self.supabase
        )
        return await handler.check_limit(
            organization_id, entitlements, resolved, increment=increment
        )

    @tracer.start_as_current_span("billing.entitlement.assert_limit")
    async def assert_limit(
        self,
        organization_id: UUID,
        limit_key: str,
        *,
        increment: int = 1,
    ) -> None:
        """Raise ``EntitlementDenied`` if the limit would be exceeded."""
        result = await self.check_limit(
            organization_id, limit_key, increment=increment
        )
        if not result.allowed:
            raise EntitlementDenied(
                result.code,
                result.message or f"Plan limit '{limit_key}' exceeded.",
                limit=result.limit,
                current=result.current,
                upgrade_plan_product_slug=result.upgrade_plan_product_slug,
            )

    @tracer.start_as_current_span("billing.entitlement.check_feature")
    async def check_feature(self, organization_id: UUID, feature_key: str) -> bool:
        """Return whether a boolean feature is enabled for the organization."""
        entitlements = await self.get_org_entitlements(organization_id)
        resolved = entitlements.features.get(feature_key)
        if resolved is None:
            return False
        return bool(resolved.effective_value)

    async def _get_subscription(
        self, organization_id: UUID
    ) -> Optional[dict[str, Any]]:
        result = (
            self.supabase.table("organization_subscriptions")
            .select("*")
            .eq("organization_id", str(organization_id))
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    async def _get_plan_version(self, plan_version_id: UUID) -> dict[str, Any]:
        result = (
            self.supabase.table("plan_versions")
            .select("*, plan_products(slug, display_name)")
            .eq("id", str(plan_version_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            raise ValueError(f"Plan version {plan_version_id} not found")
        return result.data[0]

    async def _get_version_entitlements(
        self, plan_version_id: UUID
    ) -> list[dict[str, Any]]:
        result = (
            self.supabase.table("plan_version_entitlements")
            .select("*")
            .eq("plan_version_id", str(plan_version_id))
            .execute()
        )
        return result.data or []

    async def _get_definitions(self) -> list[EntitlementDefinition]:
        if self._definitions_cache is not None:
            return self._definitions_cache

        result = (
            self.supabase.table("entitlement_definitions")
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        definitions = [EntitlementDefinition(**row) for row in (result.data or [])]
        self._definitions_cache = definitions
        return definitions

    async def _resolve_free_plan_version_id(self) -> UUID:
        if self._free_plan_version_id is not None:
            return self._free_plan_version_id

        result = (
            self.supabase.table("plan_versions")
            .select("id, plan_products!inner(slug)")
            .eq("plan_products.slug", FREE_PLAN_PRODUCT_SLUG)
            .eq("is_current_for_signup", True)
            .eq("status", "published")
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise ValueError(
                f"No published free plan version found (slug={FREE_PLAN_PRODUCT_SLUG})"
            )
        version_id = UUID(str(result.data[0]["id"]))
        self._free_plan_version_id = version_id
        return version_id


entitlement_service = EntitlementService()
