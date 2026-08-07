"""
Registered handlers for evaluating plan entitlements at runtime.

Each ``entitlement_definitions.enforcement_handler`` key maps to a handler
class. Generic handlers cover most count/boolean limits; specialized handlers
can be added without schema changes.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID

from shared.config import supabase_config

from .entitlement_models import LimitCheckResult, OrgEntitlements, ResolvedEntitlement


class EntitlementHandler(ABC):
    """Base class for entitlement enforcement handlers."""

    def __init__(self, supabase: Any = None) -> None:
        self._supabase = supabase

    def _client(self) -> Any:
        if self._supabase is not None:
            return self._supabase
        return supabase_config.client

    @abstractmethod
    async def check_limit(
        self,
        org_id: UUID,
        entitlements: OrgEntitlements,
        resolved: ResolvedEntitlement,
        *,
        increment: int = 1,
    ) -> LimitCheckResult:
        """Evaluate whether ``increment`` usage is allowed."""


class MaxCountHandler(EntitlementHandler):
    """Enforces integer count limits (max_agents, max_phone_numbers, …)."""

    count_table: str = ""
    count_column: str = "organization_id"

    async def _current_count(self, org_id: UUID) -> int:
        client = self._client()
        if client is None:
            return 0
        result = (
            client.table(self.count_table)
            .select("id", count="exact")
            .eq(self.count_column, str(org_id))
            .execute()
        )
        if getattr(result, "count", None) is not None:
            count = result.count
            if isinstance(count, int):
                return count
        return len(result.data or [])

    async def check_limit(
        self,
        org_id: UUID,
        entitlements: OrgEntitlements,
        resolved: ResolvedEntitlement,
        *,
        increment: int = 1,
    ) -> LimitCheckResult:
        code = resolved.key.upper()
        if resolved.is_unlimited:
            current = await self._current_count(org_id)
            return LimitCheckResult(
                allowed=True,
                code=code,
                limit=None,
                current=current,
            )

        limit = int(resolved.effective_value or 0)
        current = await self._current_count(org_id)
        allowed = (current + increment) <= limit
        message = None
        if not allowed:
            message = (
                f"Your plan allows {limit} {resolved.key.replace('max_', '').replace('_', ' ')}. "
                f"You currently have {current}."
            )

        return LimitCheckResult(
            allowed=allowed,
            code=code,
            limit=limit,
            current=current,
            message=message,
            upgrade_plan_product_slug=_suggest_upgrade_slug(entitlements),
        )


class MaxAgentsHandler(MaxCountHandler):
    """Count active voice agents for an organization."""

    count_table = "voice_agents"


class FeatureFlagHandler(EntitlementHandler):
    """Boolean feature gates — not used for increment checks."""

    async def check_limit(
        self,
        org_id: UUID,
        entitlements: OrgEntitlements,
        resolved: ResolvedEntitlement,
        *,
        increment: int = 1,
    ) -> LimitCheckResult:
        enabled = bool(resolved.effective_value)
        return LimitCheckResult(
            allowed=enabled,
            code=resolved.key.upper(),
            message=None if enabled else f"Feature '{resolved.key}' is not enabled on your plan.",
        )


HANDLERS: dict[str, type[EntitlementHandler]] = {
    "limit.max_count": MaxCountHandler,
    "limit.max_agents": MaxAgentsHandler,
    "feature.flag": FeatureFlagHandler,
}


def get_handler(
    handler_key: str,
    entitlement_key: str,
    *,
    supabase: Any = None,
) -> EntitlementHandler:
    """Instantiate handler; specialize max_agents when keyed generically."""
    if handler_key == "limit.max_count" and entitlement_key == "max_agents":
        return MaxAgentsHandler(supabase=supabase)
    handler_cls = HANDLERS.get(handler_key)
    if handler_cls is None:
        raise ValueError(f"No entitlement handler registered for '{handler_key}'")
    return handler_cls(supabase=supabase)


def _suggest_upgrade_slug(entitlements: OrgEntitlements) -> Optional[str]:
    """Placeholder upgrade hint — later resolve current signup version per product."""
    if entitlements.plan_product_slug == "free":
        return "starter"
    return None


def parse_entitlement_value(raw: Optional[dict[str, Any]]) -> tuple[Any, bool]:
    """Parse JSONB value payload into effective Python value."""
    if not raw:
        return None, False
    value_type = raw.get("type")
    if value_type == "unlimited":
        return None, True
    if value_type == "integer":
        return raw.get("value"), False
    if value_type == "boolean":
        return bool(raw.get("value")), False
    if value_type == "decimal":
        return raw.get("value"), False
    if value_type == "enum":
        return raw.get("value"), False
    return raw.get("value"), False
