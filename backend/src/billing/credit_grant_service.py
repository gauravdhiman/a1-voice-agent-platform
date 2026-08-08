"""Policy-aware subscription credit grants.

This module is the single entry point for credits included with a plan. It
reads the immutable plan-version policy, supports one-time free trial grants,
and passes a stable idempotency key to the ledger so webhook retries cannot
double-credit an organization.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from .models import CreditTransaction
from .plan_version_models import CreditGrantPolicy
from .service import billing_service

logger = logging.getLogger(__name__)

INCLUDED_CREDITS_ENTITLEMENT = "included_credits_per_billing_period"


class CreditGrantService:
    """Resolve plan credit policy and create idempotent ledger grants."""

    def __init__(self) -> None:
        """Initialize the service with the configured Supabase client."""
        from shared.config import supabase_config

        self.supabase = supabase_config.client

    async def grant_for_subscription(
        self,
        subscription: dict[str, Any],
        *,
        grant_reason: str,
        period_start: datetime,
        period_end: Optional[datetime],
        grant_key: str,
        fallback_credits: int = 0,
    ) -> Optional[CreditTransaction]:
        """Grant included credits according to a subscription's plan policy.

        Args:
            subscription: Subscription row containing ids and ``plan_version_id``.
            grant_reason: ``activation``, ``invoice_paid``, or ``free_renewal``.
            period_start: Start of the period represented by this grant.
            period_end: Expiry boundary for recurring plan credits.
            grant_key: Stable event/cycle key used for idempotency.
            fallback_credits: Legacy-plan amount when no version is available.

        Returns:
            The created or reused credit transaction, or ``None`` when the
            policy does not grant credits for this event or the amount is zero.
        """
        version_id = subscription.get("plan_version_id")
        policy = CreditGrantPolicy.RECURRING
        credits = max(0, int(fallback_credits))

        if version_id:
            version = await self._get_plan_version(UUID(str(version_id)))
            policy = CreditGrantPolicy(
                version.get("credit_grant_policy", CreditGrantPolicy.RECURRING.value)
            )
            credits = await self._get_included_credits(UUID(str(version_id)))

        if policy == CreditGrantPolicy.ONE_TIME and grant_reason != "activation":
            return None
        if credits <= 0:
            return None

        subscription_id = UUID(str(subscription["id"]))
        organization_id = UUID(str(subscription["organization_id"]))
        expires_at = period_end if policy == CreditGrantPolicy.RECURRING else None
        metadata = {
            "grant_key": grant_key,
            "grant_reason": grant_reason,
            "period_start": period_start.isoformat(),
            "credit_grant_policy": policy.value,
        }
        if version_id:
            metadata["plan_version_id"] = str(version_id)

        return await billing_service.add_subscription_credits(
            organization_id=organization_id,
            credits=credits,
            subscription_id=subscription_id,
            expires_at=expires_at,
            metadata=metadata,
            idempotency_key=grant_key,
        )

    async def _get_plan_version(self, plan_version_id: UUID) -> dict[str, Any]:
        """Read the immutable version fields needed for credit policy."""
        result = (
            self.supabase.table("plan_versions")
            .select("id, credit_grant_policy")
            .eq("id", str(plan_version_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            raise ValueError(f"Plan version {plan_version_id} not found")
        return result.data[0]

    async def _get_included_credits(self, plan_version_id: UUID) -> int:
        """Read the included-credit entitlement from an immutable version."""
        result = (
            self.supabase.table("plan_version_entitlements")
            .select("value")
            .eq("plan_version_id", str(plan_version_id))
            .eq("entitlement_key", INCLUDED_CREDITS_ENTITLEMENT)
            .limit(1)
            .execute()
        )
        if not result.data:
            return 0
        value = result.data[0].get("value") or {}
        try:
            return max(0, int(value.get("value", 0)))
        except (TypeError, ValueError):
            logger.warning(
                "Invalid included-credit entitlement for %s", plan_version_id
            )
            return 0


credit_grant_service = CreditGrantService()
