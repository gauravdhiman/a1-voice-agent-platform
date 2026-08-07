"""
Credit consumption and monthly grant helpers driven by plan-version entitlements.

Resolves ``included_credits_monthly``, ``payg_enabled``, and ``payg_credit_cap``
from the bound plan version for renewal grants and PAYG consumption.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from .entitlement_models import OrgEntitlements
from .entitlement_service import entitlement_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreditConsumptionDecision:
    """Result of evaluating whether an org may consume credits."""

    allowed: bool
    used_payg: bool = False
    denial_message: Optional[str] = None


class CreditEntitlementService:
    """Plan-version-aware credit grant and PAYG consumption rules."""

    async def get_included_credits_monthly(self, organization_id: UUID) -> int:
        """Return included monthly credits from the org's bound plan version.

        Falls back to ``0`` when the entitlement is absent or unlimited.

        Args:
            organization_id: Organization UUID.

        Returns:
            Integer credits to grant on subscription renewal/invoice paid.
        """
        entitlements = await entitlement_service.get_org_entitlements(organization_id)
        return self.included_credits_from_entitlements(entitlements)

    @staticmethod
    def included_credits_from_entitlements(entitlements: OrgEntitlements) -> int:
        """Extract ``included_credits_monthly`` from resolved entitlements."""
        resolved = entitlements.limits.get("included_credits_monthly")
        if resolved is None or not resolved.assigned:
            return 0
        if resolved.is_unlimited:
            return 0
        try:
            return max(0, int(resolved.effective_value or 0))
        except (TypeError, ValueError):
            return 0

    async def evaluate_consumption(
        self,
        organization_id: UUID,
        credits_needed: int,
        *,
        current_balance: Optional[int] = None,
    ) -> CreditConsumptionDecision:
        """Evaluate PAYG-aware credit consumption for ``credits_needed``.

        Args:
            organization_id: Organization UUID.
            credits_needed: Credits to debit (positive integer).
            current_balance: Optional pre-fetched balance to avoid duplicate query.

        Returns:
            CreditConsumptionDecision with allow/deny and PAYG flag.
        """
        entitlements = await entitlement_service.get_org_entitlements(organization_id)
        balance = current_balance
        if balance is None:
            balance = await self._fetch_balance(organization_id)
        return self.evaluate_consumption_with_entitlements(
            entitlements, balance, credits_needed
        )

    @staticmethod
    def evaluate_consumption_with_entitlements(
        entitlements: OrgEntitlements,
        current_balance: int,
        credits_needed: int,
    ) -> CreditConsumptionDecision:
        """Pure PAYG evaluation using pre-resolved entitlements."""
        if credits_needed <= 0:
            return CreditConsumptionDecision(allowed=True)

        if current_balance >= credits_needed:
            return CreditConsumptionDecision(allowed=True)

        payg = entitlements.features.get("payg_enabled")
        if payg is None or not bool(payg.effective_value):
            return CreditConsumptionDecision(
                allowed=False,
                denial_message="Insufficient credits.",
            )

        cap_resolved = entitlements.limits.get("payg_credit_cap")
        cap = 0
        if cap_resolved is not None and cap_resolved.assigned:
            if cap_resolved.is_unlimited:
                return CreditConsumptionDecision(allowed=True, used_payg=True)
            try:
                cap = max(0, int(cap_resolved.effective_value or 0))
            except (TypeError, ValueError):
                cap = 0

        if cap <= 0:
            return CreditConsumptionDecision(
                allowed=False,
                denial_message="Pay-as-you-go is not configured on your plan.",
            )

        projected = current_balance - credits_needed
        if projected >= -cap:
            return CreditConsumptionDecision(allowed=True, used_payg=True)

        return CreditConsumptionDecision(
            allowed=False,
            denial_message="Pay-as-you-go credit cap exceeded.",
        )

    async def _fetch_balance(self, organization_id: UUID) -> int:
        result = (
            entitlement_service.supabase.table("organizations")
            .select("credit_balance")
            .eq("id", str(organization_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return 0
        return int(result.data[0].get("credit_balance") or 0)


credit_entitlement_service = CreditEntitlementService()
