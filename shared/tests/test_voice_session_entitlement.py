"""Tests for shared voice session entitlement pre-checks."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    _evaluate_credit_headroom,
    assert_voice_session_allowed,
)


class TestEvaluateCreditHeadroom:
    """Prepaid-only headroom evaluation (PAYG removed)."""

    def test_allows_when_balance_covers_cost(self):
        allowed, message = _evaluate_credit_headroom(100, 10)
        assert allowed is True
        assert message is None

    def test_denies_when_balance_insufficient(self):
        allowed, message = _evaluate_credit_headroom(5, 10)
        assert allowed is False
        assert message is not None
        assert "Insufficient credits" in message

    def test_allows_when_balance_exactly_covers_cost(self):
        allowed, message = _evaluate_credit_headroom(10, 10)
        assert allowed is True
        assert message is None

    def test_zero_balance_denies(self):
        allowed, message = _evaluate_credit_headroom(0, 10)
        assert allowed is False
        assert message


@pytest.mark.asyncio
async def test_assert_voice_session_allowed_raises_on_concurrent_limit(monkeypatch):
    org_id = uuid4()
    client = MagicMock()

    sub_execute = MagicMock(
        data=[{"status": "active", "plan_version_id": str(uuid4())}]
    )
    ent_execute = MagicMock(
        data=[
            {
                "entitlement_key": "max_concurrent_calls",
                "value": {"type": "integer", "value": 1},
            }
        ]
    )
    catalog_execute = MagicMock(
        data=[
            {
                "key": "max_concurrent_calls",
                "kind": "limit",
                "default_when_absent": None,
            }
        ]
    )
    active_calls_execute = MagicMock(
        data=[{"id": "1"}, {"id": "2"}], count=2
    )

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.in_.return_value = table
    table.order.return_value = table
    table.execute.side_effect = [
        sub_execute,
        ent_execute,
        catalog_execute,
        active_calls_execute,
    ]
    client.table.return_value = table

    monkeypatch.setattr(
        "shared.billing.voice_session_entitlement.supabase_config",
        MagicMock(client=client),
    )

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await assert_voice_session_allowed(org_id)
    assert exc_info.value.code == "MAX_CONCURRENT_CALLS"


@pytest.mark.asyncio
async def test_assert_voice_session_allowed_allows_current_pstn_call_log(
    monkeypatch,
):
    """Allow the call already pre-logged by the PSTN webhook to start.

    The backend creates the inbound Twilio call log before the voice-ws
    entitlement check. That row represents the call being admitted and must
    not consume an additional concurrency slot.
    """
    org_id = uuid4()
    client = MagicMock()

    sub_execute = MagicMock(
        data=[{"status": "active", "plan_version_id": str(uuid4())}]
    )
    ent_execute = MagicMock(
        data=[
            {
                "entitlement_key": "max_concurrent_calls",
                "value": {"type": "integer", "value": 1},
            }
        ]
    )
    catalog_execute = MagicMock(
        data=[
            {
                "key": "max_concurrent_calls",
                "kind": "limit",
                "default_when_absent": None,
            }
        ]
    )
    active_calls_execute = MagicMock(
        data=[{"id": "current-call", "call_sid": "CA-current"}], count=1
    )
    min_cost_execute = MagicMock(data=[])

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.in_.return_value = table
    table.order.return_value = table
    table.execute.side_effect = [
        sub_execute,
        ent_execute,
        catalog_execute,
        active_calls_execute,
        min_cost_execute,
    ]
    client.table.return_value = table

    monkeypatch.setattr(
        "shared.billing.voice_session_entitlement.supabase_config",
        MagicMock(client=client),
    )

    await assert_voice_session_allowed(org_id, current_call_sid="CA-current")


@pytest.mark.asyncio
async def test_assert_voice_session_allowed_raises_on_insufficient_credits(monkeypatch):
    """Total balance (plan + purchased) below one billable minute raises."""
    org_id = uuid4()
    client = MagicMock()

    sub_execute = MagicMock(
        data=[{"status": "active", "plan_version_id": str(uuid4())}]
    )
    ent_execute = MagicMock(data=[])
    catalog_execute = MagicMock(data=[])
    min_cost_execute = MagicMock(data=[{"credit_cost": 10, "is_active": True}])
    org_execute = MagicMock(
        data=[{"credit_balance": 3, "purchased_credit_balance": 2}]
    )

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.in_.return_value = table
    table.order.return_value = table
    table.execute.side_effect = [
        sub_execute,
        ent_execute,
        catalog_execute,
        min_cost_execute,
        org_execute,
    ]
    client.table.return_value = table

    monkeypatch.setattr(
        "shared.billing.voice_session_entitlement.supabase_config",
        MagicMock(client=client),
    )

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await assert_voice_session_allowed(org_id)
    assert exc_info.value.code == "INSUFFICIENT_CREDITS"


@pytest.mark.asyncio
async def test_assert_voice_session_allowed_allows_with_purchased_credits(monkeypatch):
    """Purchased credits count toward the pre-check even when plan credits are gone."""
    org_id = uuid4()
    client = MagicMock()

    sub_execute = MagicMock(
        data=[{"status": "active", "plan_version_id": str(uuid4())}]
    )
    ent_execute = MagicMock(data=[])
    catalog_execute = MagicMock(data=[])
    min_cost_execute = MagicMock(data=[{"credit_cost": 10, "is_active": True}])
    org_execute = MagicMock(
        data=[
            {
                "credit_balance": 0,
                "admin_credit_balance": 50,
                "purchased_credit_balance": 0,
            }
        ]
    )

    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.in_.return_value = table
    table.order.return_value = table
    table.execute.side_effect = [
        sub_execute,
        ent_execute,
        catalog_execute,
        min_cost_execute,
        org_execute,
    ]
    client.table.return_value = table

    monkeypatch.setattr(
        "shared.billing.voice_session_entitlement.supabase_config",
        MagicMock(client=client),
    )

    await assert_voice_session_allowed(org_id)
