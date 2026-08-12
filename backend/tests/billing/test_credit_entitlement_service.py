"""Tests for plan-version credit grants and low-balance threshold evaluation."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from src.billing.credit_entitlement_service import (
    LOW_CREDIT_WARNING_THRESHOLDS,
    CreditEntitlementService,
)
from src.billing.entitlement_models import (
    EntitlementKind,
    OrgEntitlements,
    ResolvedEntitlement,
)


def _org_entitlements(
    limits: dict[str, int] | None = None,
) -> OrgEntitlements:
    org_id = uuid4()
    limit_map = {
        key: ResolvedEntitlement(
            key=key,
            kind=EntitlementKind.LIMIT,
            assigned=True,
            raw_value={"type": "integer", "value": value},
            effective_value=value,
        )
        for key, value in (limits or {}).items()
    }
    return OrgEntitlements(
        organization_id=org_id,
        plan_version_id=uuid4(),
        plan_product_slug="starter",
        plan_version_number=1,
        is_entitled=True,
        limits=limit_map,
        features={},
    )


class TestCreditEntitlementService:
    """Monthly credit resolution (PAYG removed)."""

    def test_included_credits_from_entitlements(self):
        entitlements = _org_entitlements(
            limits={"included_credits_per_billing_period": 750}
        )
        assert (
            CreditEntitlementService.included_credits_from_entitlements(entitlements)
            == 750
        )

    def test_included_credits_missing_returns_zero(self):
        entitlements = OrgEntitlements(
            organization_id=uuid4(),
            plan_version_id=uuid4(),
            plan_product_slug="free",
            plan_version_number=1,
            is_entitled=False,
        )
        assert (
            CreditEntitlementService.included_credits_from_entitlements(entitlements)
            == 0
        )

    def test_included_credits_unlimited_returns_zero(self):
        entitlements = OrgEntitlements(
            organization_id=uuid4(),
            plan_version_id=uuid4(),
            plan_product_slug="starter",
            plan_version_number=1,
            is_entitled=True,
            limits={
                "included_credits_per_billing_period": ResolvedEntitlement(
                    key="included_credits_per_billing_period",
                    kind=EntitlementKind.LIMIT,
                    assigned=True,
                    raw_value={"type": "unlimited"},
                    effective_value=None,
                    is_unlimited=True,
                )
            },
            features={},
        )
        assert (
            CreditEntitlementService.included_credits_from_entitlements(entitlements)
            == 0
        )

    @pytest.mark.asyncio
    async def test_get_included_credits_per_billing_period_delegates_to_entitlements(
        self,
    ):
        org_id = uuid4()
        entitlements = _org_entitlements(
            limits={"included_credits_per_billing_period": 1200}
        )
        service = CreditEntitlementService()
        with patch(
            "src.billing.credit_entitlement_service.entitlement_service.get_org_entitlements",
            new=AsyncMock(return_value=entitlements),
        ):
            result = await service.get_included_credits_per_billing_period(org_id)
        assert result == 1200


class TestLowCreditThresholdToNotify:
    """20/10/5% thresholds relative to the period's included credits."""

    def test_thresholds_ordered_descending(self):
        assert LOW_CREDIT_WARNING_THRESHOLDS == (20, 10, 5)

    def test_no_warning_above_highest_threshold(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(250, 1000, None)
            is None
        )

    def test_warns_at_20_percent(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(180, 1000, None)
            == 20
        )

    def test_warns_at_10_after_20(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(90, 1000, 20) == 10
        )

    def test_warns_at_5_after_10(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(40, 1000, 10) == 5
        )

    def test_no_repeat_when_still_below_same_threshold(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(180, 1000, 20)
            is None
        )

    def test_exact_threshold_boundary_warns(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(200, 1000, None)
            == 20
        )

    def test_purchased_credits_buffer_prevents_warning(self):
        # 180 plan-remaining + 800 purchased = 980 total vs 1000 included
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(980, 1000, None)
            is None
        )

    def test_zero_included_credits_never_warns(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(50, 0, None) is None
        )

    def test_negative_remaining_warns_at_five_percent_floor(self):
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(-5, 1000, None) == 5
        )

    def test_rearm_after_purchase_restarts_cycle(self):
        # After a purchase the notified marker is cleared (None), so the
        # 20% threshold fires again even though usage is the same.
        assert (
            CreditEntitlementService.low_credit_threshold_to_notify(180, 1000, None)
            == 20
        )
