"""Billing summary includes canonical versioned subscription plan details."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.billing.models import (
    OrganizationBillingSummary,
    OrganizationSubscriptionWithPlan,
    SubscriptionStatus,
)

ORG_ID = UUID("00000000-0000-0000-0000-000000000201")
SUBSCRIPTION_ID = UUID("00000000-0000-0000-0000-000000000202")
PLAN_VERSION_ID = UUID("00000000-0000-0000-0000-000000000203")


@pytest.mark.asyncio
async def test_billing_summary_displays_version_only_paid_plan_and_price():
    """Version-only plans keep the current plan and renewal price visible."""
    from src.billing.routes import get_billing_summary

    now = datetime.now(timezone.utc)
    subscription = OrganizationSubscriptionWithPlan(
        id=SUBSCRIPTION_ID,
        organization_id=ORG_ID,
        subscription_plan_id=None,
        plan_version_id=PLAN_VERSION_ID,
        stripe_subscription_id="sub_versioned",
        stripe_customer_id="cus_versioned",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now,
        trial_start=None,
        trial_end=None,
        cancel_at_period_end=False,
        cancelled_at=None,
        metadata={"billing_mode": "paid"},
        created_at=now,
        updated_at=now,
        plan=None,
    )
    summary = OrganizationBillingSummary(
        organization_id=ORG_ID,
        subscription=subscription,
        credit_balance=2500,
        current_period_usage=0,
    )
    plan_version = MagicMock()
    plan_version.price_amount_cents = 4900
    plan_version.model_dump.return_value = {
        "id": str(PLAN_VERSION_ID),
        "product_name": "Starter",
        "display_label": "Starter:Month v1",
        "price_amount_cents": 4900,
        "billing_interval": "monthly",
        "billing_mode": "paid",
        "entitlements": {
            "included_credits_per_billing_period": {
                "type": "integer",
                "value": 2500,
            }
        },
    }

    with patch(
        "src.billing.routes.billing_service.get_organization_billing_summary",
        new_callable=AsyncMock,
        return_value=summary,
    ), patch(
        "src.billing.routes.versioned_subscription_service.get_plan_version_for_display",
        new_callable=AsyncMock,
        return_value=plan_version,
    ) as get_plan_version:
        result = await get_billing_summary(ORG_ID, (UUID(int=1), SimpleNamespace()))

    get_plan_version.assert_awaited_once_with(PLAN_VERSION_ID)
    assert result.amount_due == 4900
    assert result.subscription.plan_version["product_name"] == "Starter"
