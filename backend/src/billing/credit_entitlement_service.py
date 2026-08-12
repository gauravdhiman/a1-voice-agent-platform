"""
Credit grant and low-balance threshold helpers driven by plan-version entitlements.

Resolves ``included_credits_per_billing_period`` from the bound plan version
for renewal grants, and evaluates prepaid low-balance notification thresholds
(20% / 10% / 5% of the period's included credits).

New activities are admitted only when the organization can cover at least one
billable unit. A call already in progress is allowed to finish and its final
metered debit may temporarily take the plan pool negative; the next activity
is blocked until the balance is restored.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from .entitlement_models import OrgEntitlements
from .entitlement_service import entitlement_service

logger = logging.getLogger(__name__)

#: Low-balance warning thresholds, expressed as a percentage of the billing
#: period's included credits. Emailed at most once per threshold per cycle.
LOW_CREDIT_WARNING_THRESHOLDS: tuple[int, ...] = (20, 10, 5)


class CreditEntitlementService:
    """Plan-version-aware credit grant and low-balance notification rules."""

    async def get_included_credits_per_billing_period(
        self, organization_id: UUID
    ) -> int:
        """Return included credits from the org's bound plan version per billing period.

        Falls back to ``0`` when the entitlement is absent or unlimited.

        Args:
            organization_id: Organization UUID.

        Returns:
            Integer credits to grant on subscription renewal/invoice paid.
        """
        entitlements = await entitlement_service.get_org_entitlements(organization_id)
        return self.included_credits_from_entitlements(entitlements)

    async def get_included_credits_monthly(self, organization_id: UUID) -> int:
        """Deprecated alias for ``get_included_credits_per_billing_period``."""
        return await self.get_included_credits_per_billing_period(organization_id)

    @staticmethod
    def included_credits_from_entitlements(entitlements: OrgEntitlements) -> int:
        """Extract ``included_credits_per_billing_period`` from resolved entitlements."""
        resolved = entitlements.limits.get("included_credits_per_billing_period")
        if resolved is None or not resolved.assigned:
            return 0
        if resolved.is_unlimited:
            return 0
        try:
            return max(0, int(resolved.effective_value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def low_credit_threshold_to_notify(
        remaining_credits: int,
        included_credits: int,
        last_notified: Optional[int],
    ) -> Optional[int]:
        """Return the threshold percentage to notify now, or None.

        Compares ``remaining_credits`` against ``included_credits`` (the
        billing period's plan allotment) and picks the largest configured
        threshold (20/10/5) that the remaining percentage is at or below.
        A notification fires only when that threshold is lower than the last
        one already notified this cycle, so each threshold is emailed at most
        once per billing cycle (purchases/renewals re-arm via NULL).

        Args:
            remaining_credits: Combined prepaid balance (plan + purchased).
            included_credits: Plan's included credits for the billing period.
            last_notified: Last threshold percentage emailed this cycle, or
                None if none has been sent yet.

        Returns:
            Threshold percentage to notify (e.g. 20), or None when no new
            threshold is crossed.

        Example:
            ```python
            # 180 credits left on a 1000-credit plan -> warn at 20%
            low_credit_threshold_to_notify(180, 1000, None)  # -> 20
            # Already warned at 20%, now at 9% -> warn at 10%
            low_credit_threshold_to_notify(90, 1000, 20)      # -> 10
            # At 18% but already warned at 20% this cycle -> no email
            low_credit_threshold_to_notify(180, 1000, 20)    # -> None
            ```
        """
        if included_credits <= 0:
            return None

        # A completed call may settle below zero so the customer is charged for
        # the full call. Treat that state as the 5% floor rather than suppressing
        # the final warning.
        remaining_pct = (max(0, remaining_credits) / included_credits) * 100
        candidate: Optional[int] = None
        for threshold in LOW_CREDIT_WARNING_THRESHOLDS:
            if remaining_pct <= threshold:
                candidate = threshold
            else:
                break

        if candidate is None:
            return None
        if last_notified is not None and candidate >= last_notified:
            return None
        return candidate


credit_entitlement_service = CreditEntitlementService()
