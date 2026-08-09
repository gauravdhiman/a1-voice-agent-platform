"""Tests for policy-aware, idempotent subscription credit grants."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.billing.credit_grant_service import CreditGrantService

ORG_ID = UUID("00000000-0000-0000-0000-000000000201")
SUBSCRIPTION_ID = UUID("00000000-0000-0000-0000-000000000202")
VERSION_ID = UUID("00000000-0000-0000-0000-000000000203")


def _query(data):
    """Create a chainable Supabase query mock."""
    query = MagicMock()
    for method in ("select", "eq", "single", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=data)
    return query


@pytest.mark.asyncio
async def test_recurring_policy_grants_entitlement_with_idempotency_metadata():
    """Activation grants the versioned credit amount with a stable grant key."""
    service = CreditGrantService()
    service.supabase = MagicMock()
    version_query = _query(
        [{"id": str(VERSION_ID), "credit_grant_policy": "recurring"}]
    )
    entitlement_query = _query([{"value": {"type": "integer", "value": 100}}])
    service.supabase.table.side_effect = [version_query, entitlement_query]

    add_credits = AsyncMock(return_value="transaction")
    with patch(
        "src.billing.credit_grant_service.billing_service.add_subscription_credits",
        add_credits,
    ):
        result = await service.grant_for_subscription(
            {
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(VERSION_ID),
            },
            grant_reason="activation",
            period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            grant_key="subscription:202:activation",
        )

    assert result == "transaction"
    add_credits.assert_awaited_once()
    assert add_credits.await_args.kwargs["credits"] == 100
    assert add_credits.await_args.kwargs["subscription_id"] == SUBSCRIPTION_ID
    assert add_credits.await_args.kwargs["idempotency_key"] == (
        "subscription:202:activation"
    )
    assert add_credits.await_args.kwargs["metadata"]["grant_reason"] == "activation"


@pytest.mark.asyncio
async def test_one_time_policy_skips_recurring_grants():
    """A one-time free plan never receives a renewal grant."""
    service = CreditGrantService()
    service.supabase = MagicMock()
    service.supabase.table.return_value = _query(
        [{"id": str(VERSION_ID), "credit_grant_policy": "one_time"}]
    )
    add_credits = AsyncMock()

    with patch(
        "src.billing.credit_grant_service.billing_service.add_subscription_credits",
        add_credits,
    ):
        result = await service.grant_for_subscription(
            {
                "id": str(SUBSCRIPTION_ID),
                "organization_id": str(ORG_ID),
                "plan_version_id": str(VERSION_ID),
            },
            grant_reason="free_renewal",
            period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 9, 1, tzinfo=timezone.utc),
            grant_key="subscription:202:renewal:1",
        )

    assert result is None
    add_credits.assert_not_awaited()


@pytest.mark.asyncio
async def test_free_renewal_scheduler_advances_due_period_after_grant():
    """Due recurring free subscriptions receive credits and advance one period."""
    from src.billing.free_plan_renewal_scheduler import FreePlanRenewalService

    service = FreePlanRenewalService()
    service.supabase = MagicMock()
    subscription = {
        "id": str(SUBSCRIPTION_ID),
        "organization_id": str(ORG_ID),
        "status": "active",
        "current_period_start": "2026-07-01T00:00:00+00:00",
        "current_period_end": "2026-08-01T00:00:00+00:00",
        "metadata": {
            "billing_mode": "free",
            "credit_grant_policy": "recurring",
            "billing_interval": "monthly",
        },
    }
    subscriptions = _query([subscription])
    service.supabase.table.return_value = subscriptions
    service.credit_grant_service.grant_for_subscription = AsyncMock(
        return_value="transaction"
    )

    result = await service.process_due_renewals(
        now=datetime(2026, 8, 2, tzinfo=timezone.utc)
    )

    assert result.processed == 1
    service.credit_grant_service.grant_for_subscription.assert_awaited_once()
    subscriptions.update.assert_called_once()
    update_payload = subscriptions.update.call_args.args[0]
    assert update_payload["current_period_start"].startswith("2026-08-01")
    assert update_payload["current_period_end"].startswith("2026-09-01")


@pytest.mark.asyncio
async def test_free_renewal_scheduler_skips_missed_periods_after_downtime():
    """Downtime does not accrue multiple free recurring credit grants."""
    from src.billing.free_plan_renewal_scheduler import FreePlanRenewalService

    service = FreePlanRenewalService()
    service.supabase = MagicMock()
    subscription = {
        "id": str(SUBSCRIPTION_ID),
        "organization_id": str(ORG_ID),
        "status": "active",
        "current_period_start": "2026-05-01T00:00:00+00:00",
        "current_period_end": "2026-06-01T00:00:00+00:00",
        "metadata": {
            "billing_mode": "free",
            "credit_grant_policy": "recurring",
            "billing_interval": "monthly",
        },
    }
    subscriptions = _query([subscription])
    service.supabase.table.return_value = subscriptions
    service.credit_grant_service.grant_for_subscription = AsyncMock(
        return_value="transaction"
    )

    result = await service.process_due_renewals(
        now=datetime(2026, 8, 2, tzinfo=timezone.utc)
    )

    assert result.processed == 1
    service.credit_grant_service.grant_for_subscription.assert_awaited_once()
    grant_call = service.credit_grant_service.grant_for_subscription.await_args
    assert grant_call.kwargs["period_start"] == datetime(
        2026, 8, 1, tzinfo=timezone.utc
    )
    assert grant_call.kwargs["period_end"] == datetime(2026, 9, 1, tzinfo=timezone.utc)
