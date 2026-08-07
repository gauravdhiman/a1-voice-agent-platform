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
    """PAYG headroom evaluation."""

    def test_allows_when_balance_covers_cost(self):
        allowed, message = _evaluate_credit_headroom(100, 10, payg_enabled=False, payg_cap=None)
        assert allowed is True
        assert message is None

    def test_allows_payg_within_cap(self):
        allowed, _ = _evaluate_credit_headroom(
            5,
            20,
            payg_enabled=True,
            payg_cap={"type": "integer", "value": 50},
        )
        assert allowed is True

    def test_denies_payg_beyond_cap(self):
        allowed, message = _evaluate_credit_headroom(
            5,
            100,
            payg_enabled=True,
            payg_cap={"type": "integer", "value": 10},
        )
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
    active_calls_execute = MagicMock(data=[{"id": "1"}], count=1)

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
