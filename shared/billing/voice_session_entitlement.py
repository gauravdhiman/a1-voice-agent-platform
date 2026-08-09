"""
Voice session entitlement pre-checks shared by the voice-ws worker.

Resolves plan-version entitlements from Supabase (same binding rules as backend
``EntitlementService``) and enforces concurrent call limits plus minimum credit
headroom before a WebSocket session starts.

Credits are strictly prepaid (no pay-as-you-go): the pre-check passes when the
combined balance (plan credits + purchased credits) covers at least one
billable voice minute.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from shared.billing.call_status import ACTIVE_VOICE_CALL_STATUSES
from shared.config import supabase_config

logger = logging.getLogger(__name__)

FREE_PLAN_PRODUCT_SLUG = "free"
ACTIVE_SUBSCRIPTION_STATUSES = frozenset({"active", "trial"})
DEFAULT_VOICE_MINUTE_EVENT = "voice_call_minute"


class VoiceSessionEntitlementError(Exception):
    """Raised when a voice session cannot start due to plan limits."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _parse_entitlement_value(raw: Optional[dict[str, Any]]) -> tuple[Any, bool]:
    if not raw:
        return None, False
    value_type = raw.get("type")
    if value_type == "unlimited":
        return None, True
    if value_type == "integer":
        return raw.get("value"), False
    if value_type == "boolean":
        return bool(raw.get("value")), False
    return raw.get("value"), False


async def assert_voice_session_allowed(
    organization_id: UUID,
    *,
    min_event_name: str = DEFAULT_VOICE_MINUTE_EVENT,
    current_call_sid: Optional[str] = None,
) -> None:
    """Raise ``VoiceSessionEntitlementError`` if the org cannot start a call.

    Checks:
    - ``max_concurrent_calls`` against active ``call_logs`` rows
    - Combined credit balance (plan + purchased) for at least one billable
      voice minute. No pay-as-you-go: consumption is strictly prepaid.

    Args:
        organization_id: Tenant owning the voice agent.
        min_event_name: Credit event used to estimate minimum session cost.
        current_call_sid: Optional provider call identifier for a PSTN call
            already persisted by the backend webhook. That row is excluded
            from the active count before admitting the same call.

    Raises:
        VoiceSessionEntitlementError: When concurrent or credit pre-check fails.
    """
    client = supabase_config.client
    if client is None:
        logger.warning("Supabase unavailable — skipping voice entitlement pre-check")
        return

    entitlements = await _resolve_org_entitlements(client, organization_id)

    concurrent = entitlements["limits"].get("max_concurrent_calls")
    if concurrent is not None:
        effective, is_unlimited = _parse_entitlement_value(concurrent)
        if not is_unlimited:
            limit = int(effective or 0)
            active = await _count_active_calls(
                client,
                organization_id,
                current_call_sid=current_call_sid,
            )
            if active + 1 > limit:
                raise VoiceSessionEntitlementError(
                    "MAX_CONCURRENT_CALLS",
                    f"Your plan allows {limit} concurrent call(s). "
                    f"You currently have {active} active.",
                )

    min_cost = await _minimum_voice_credit_cost(client, min_event_name)
    if min_cost <= 0:
        return

    balance = await _get_credit_balance(client, organization_id)
    allowed, message = _evaluate_credit_headroom(balance, min_cost)
    if not allowed:
        raise VoiceSessionEntitlementError(
            "INSUFFICIENT_CREDITS",
            message or "Insufficient credits to start a voice call.",
        )


async def _resolve_org_entitlements(
    client: Any, organization_id: UUID
) -> dict[str, dict[str, Any]]:
    """Return sparse limits/features maps keyed by entitlement key."""
    sub_result = (
        client.table("organization_subscriptions")
        .select("status, plan_version_id")
        .eq("organization_id", str(organization_id))
        .limit(1)
        .execute()
    )
    plan_version_id: Optional[str] = None
    if sub_result.data and sub_result.data[0].get("status") in ACTIVE_SUBSCRIPTION_STATUSES:
        plan_version_id = sub_result.data[0].get("plan_version_id")

    if not plan_version_id:
        free_result = (
            client.table("plan_versions")
            .select("id, plan_products!inner(slug)")
            .eq("plan_products.slug", FREE_PLAN_PRODUCT_SLUG)
            .eq("is_current_for_signup", True)
            .eq("status", "published")
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        if not free_result.data:
            return {"limits": {}, "features": {}}
        plan_version_id = free_result.data[0]["id"]

    assigned_result = (
        client.table("plan_version_entitlements")
        .select("entitlement_key, value")
        .eq("plan_version_id", str(plan_version_id))
        .execute()
    )
    catalog_result = (
        client.table("entitlement_definitions")
        .select("key, kind, default_when_absent")
        .eq("is_active", True)
        .execute()
    )
    assigned_by_key = {
        row["entitlement_key"]: row["value"]
        for row in (assigned_result.data or [])
    }
    limits: dict[str, Any] = {}
    features: dict[str, Any] = {}
    for row in catalog_result.data or []:
        key = row["key"]
        raw = assigned_by_key.get(key)
        if raw is None:
            raw = row.get("default_when_absent")
        if row["kind"] == "limit":
            limits[key] = raw
        else:
            effective, _ = _parse_entitlement_value(raw)
            features[key] = effective
    return {"limits": limits, "features": features}


async def _count_active_calls(
    client: Any,
    organization_id: UUID,
    *,
    current_call_sid: Optional[str] = None,
) -> int:
    result = (
        client.table("call_logs")
        .select("id, call_sid", count="exact")
        .eq("organization_id", str(organization_id))
        .in_("status", sorted(ACTIVE_VOICE_CALL_STATUSES))
        .execute()
    )
    if current_call_sid is not None:
        return sum(
            1
            for row in (result.data or [])
            if row.get("call_sid") != current_call_sid
        )
    count = getattr(result, "count", None)
    if isinstance(count, int):
        return count
    return len(result.data or [])


async def _get_credit_balance(client: Any, organization_id: UUID) -> int:
    """Return combined prepaid balance (plan credits + purchased credits)."""
    result = (
        client.table("organizations")
        .select("credit_balance, purchased_credit_balance")
        .eq("id", str(organization_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        return 0
    plan_credits = int(result.data[0].get("credit_balance") or 0)
    purchased_credits = int(result.data[0].get("purchased_credit_balance") or 0)
    return plan_credits + purchased_credits


async def _minimum_voice_credit_cost(client: Any, event_name: str) -> int:
    result = (
        client.table("credit_events")
        .select("credit_cost")
        .eq("name", event_name)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return 0
    return int(result.data[0].get("credit_cost") or 0)


def _evaluate_credit_headroom(
    balance: int,
    credits_needed: int,
) -> tuple[bool, Optional[str]]:
    """Evaluate whether the prepaid balance covers ``credits_needed``.

    No pay-as-you-go: consumption never goes below zero, so the check is a
    plain balance comparison.

    Args:
        balance: Combined prepaid balance (plan + purchased credits).
        credits_needed: Credits required to start the session.

    Returns:
        Tuple of (allowed, message). ``allowed`` is True when
        ``balance >= credits_needed``, else False with a denial message.
    """
    if balance >= credits_needed:
        return True, None
    return False, "Insufficient credits to start a voice call."
