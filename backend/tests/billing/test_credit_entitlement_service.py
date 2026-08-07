"""Tests for plan-version credit grant and PAYG consumption evaluation."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.billing.credit_entitlement_service import CreditEntitlementService
from src.billing.entitlement_models import (
    EntitlementKind,
    OrgEntitlements,
    ResolvedEntitlement,
)


def _org_entitlements(
    limits: dict[str, int] | None = None,
    features: dict[str, bool] | None = None,
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
    feature_map = {
        key: ResolvedEntitlement(
            key=key,
            kind=EntitlementKind.FEATURE,
            assigned=True,
            raw_value={"type": "boolean", "value": value},
            effective_value=value,
        )
        for key, value in (features or {}).items()
    }
    return OrgEntitlements(
        organization_id=org_id,
        plan_version_id=uuid4(),
        plan_product_slug="starter",
        plan_version_number=1,
        is_entitled=True,
        limits=limit_map,
        features=feature_map,
    )


class TestCreditEntitlementService:
    """PAYG and monthly credit resolution."""

    def test_included_credits_from_entitlements(self):
        entitlements = _org_entitlements(limits={"included_credits_monthly": 750})
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
            CreditEntitlementService.included_credits_from_entitlements(entitlements) == 0
        )

    def test_evaluate_consumption_allows_when_balance_sufficient(self):
        entitlements = _org_entitlements()
        decision = CreditEntitlementService.evaluate_consumption_with_entitlements(
            entitlements, current_balance=100, credits_needed=10
        )
        assert decision.allowed is True
        assert decision.used_payg is False

    def test_evaluate_consumption_denies_without_payg(self):
        entitlements = _org_entitlements()
        decision = CreditEntitlementService.evaluate_consumption_with_entitlements(
            entitlements, current_balance=5, credits_needed=10
        )
        assert decision.allowed is False

    def test_evaluate_consumption_allows_payg_within_cap(self):
        entitlements = _org_entitlements(
            limits={"payg_credit_cap": 100},
            features={"payg_enabled": True},
        )
        decision = CreditEntitlementService.evaluate_consumption_with_entitlements(
            entitlements, current_balance=5, credits_needed=50
        )
        assert decision.allowed is True
        assert decision.used_payg is True

    def test_evaluate_consumption_denies_payg_beyond_cap(self):
        entitlements = _org_entitlements(
            limits={"payg_credit_cap": 20},
            features={"payg_enabled": True},
        )
        decision = CreditEntitlementService.evaluate_consumption_with_entitlements(
            entitlements, current_balance=5, credits_needed=50
        )
        assert decision.allowed is False
        assert "cap" in (decision.denial_message or "").lower()

    @pytest.mark.asyncio
    async def test_get_included_credits_monthly_delegates_to_entitlements(self):
        org_id = uuid4()
        entitlements = _org_entitlements(limits={"included_credits_monthly": 1200})
        service = CreditEntitlementService()
        with patch(
            "src.billing.credit_entitlement_service.entitlement_service.get_org_entitlements",
            new=AsyncMock(return_value=entitlements),
        ):
            result = await service.get_included_credits_monthly(org_id)
        assert result == 1200
