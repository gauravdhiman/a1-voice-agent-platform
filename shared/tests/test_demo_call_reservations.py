"""Tests for race-safe demo call budgets and reservation RPC adapters."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import shared.billing.voice_session_entitlement as entitlement
from shared.billing.voice_session_entitlement import (
    DEMO_CALL_ALREADY_USED,
    DEMO_CALL_LIMIT_REACHED,
    DEMO_CALL_RESERVATION_INVALID,
    DEMO_CALL_RESERVATION_UNAVAILABLE,
    DemoCallReservation,
    VoiceSessionEntitlementError,
    assert_demo_call_available,
    consume_demo_call_reservation,
    is_demo_agent,
    reserve_demo_call_if_needed,
    reserve_demo_call_slot,
)


def _agent(*, is_demo: bool, calls_remaining: int = -1):
    return SimpleNamespace(
        id=uuid4(),
        is_demo=is_demo,
        demo_calls_remaining=calls_remaining,
    )


def _rpc_client(data):
    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=data)
    return client


def test_assert_demo_call_available_allows_non_demo_and_unlimited_agents():
    assert_demo_call_available(_agent(is_demo=False, calls_remaining=0))
    assert_demo_call_available(_agent(is_demo=True, calls_remaining=-1))


def test_is_demo_agent_requires_an_explicit_boolean_true():
    assert is_demo_agent(_agent(is_demo=True)) is True
    assert is_demo_agent(_agent(is_demo=False)) is False
    assert is_demo_agent(SimpleNamespace(is_demo=MagicMock())) is False


@pytest.mark.parametrize("raw", [None, True, "not-an-integer"])
def test_assert_demo_call_available_treats_malformed_agent_budget_as_unlimited(raw):
    agent = _agent(is_demo=True)
    agent.demo_calls_remaining = raw
    assert_demo_call_available(agent)


def test_assert_demo_call_available_rejects_exhausted_agent():
    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        assert_demo_call_available(_agent(is_demo=True, calls_remaining=0))

    assert exc_info.value.code == DEMO_CALL_LIMIT_REACHED


@pytest.mark.asyncio
async def test_reserve_demo_call_slot_returns_post_reservation_budget(monkeypatch):
    agent_id = uuid4()
    client = _rpc_client(
        [
            {
                "success": True,
                "reservation_id": "reservation-1",
                "calls_remaining": 2,
                "max_call_duration_seconds": 600,
            }
        ]
    )
    monkeypatch.setattr(entitlement, "supabase_config", SimpleNamespace(client=client))

    result = await reserve_demo_call_slot(agent_id, session_id="session-1")

    assert result == DemoCallReservation(
        reservation_id="reservation-1",
        session_id="session-1",
        calls_remaining=2,
        max_call_duration_seconds=600,
    )
    client.rpc.assert_called_once_with(
        "reserve_demo_voice_call",
        {"p_agent_id": str(agent_id), "p_session_id": "session-1"},
    )


@pytest.mark.asyncio
async def test_reserve_demo_call_slot_maps_limit_error(monkeypatch):
    client = _rpc_client([{"success": False, "error": "demo_call_limit_reached"}])
    monkeypatch.setattr(entitlement, "supabase_config", SimpleNamespace(client=client))

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await reserve_demo_call_slot(uuid4(), session_id="session-1")

    assert exc_info.value.code == DEMO_CALL_LIMIT_REACHED


@pytest.mark.asyncio
async def test_reserve_demo_call_slot_requires_a_configured_client(monkeypatch):
    monkeypatch.setattr(entitlement, "supabase_config", SimpleNamespace(client=None))

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await reserve_demo_call_slot(uuid4())

    assert exc_info.value.code == DEMO_CALL_RESERVATION_UNAVAILABLE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        {"success": False, "error": "demo_agent_unavailable"},
        {"success": True, "reservation_id": "r"},
        {
            "success": True,
            "reservation_id": "r",
            "calls_remaining": 0,
            "max_call_duration_seconds": 0,
        },
        {
            "success": True,
            "reservation_id": "r",
            "calls_remaining": "not-an-integer",
            "max_call_duration_seconds": 600,
        },
    ],
)
async def test_reserve_demo_call_slot_rejects_unusable_rpc_results(
    monkeypatch, response
):
    monkeypatch.setattr(
        entitlement,
        "supabase_config",
        SimpleNamespace(client=_rpc_client([response])),
    )

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await reserve_demo_call_slot(uuid4())

    assert exc_info.value.code == DEMO_CALL_RESERVATION_UNAVAILABLE


@pytest.mark.asyncio
async def test_reserve_demo_call_slot_maps_provider_and_malformed_results(monkeypatch):
    unavailable_client = MagicMock()
    unavailable_client.rpc.side_effect = RuntimeError("provider down")
    monkeypatch.setattr(
        entitlement,
        "supabase_config",
        SimpleNamespace(client=unavailable_client),
    )

    with pytest.raises(VoiceSessionEntitlementError) as provider_error:
        await reserve_demo_call_slot(uuid4())
    assert provider_error.value.code == DEMO_CALL_RESERVATION_UNAVAILABLE

    monkeypatch.setattr(
        entitlement,
        "supabase_config",
        SimpleNamespace(client=_rpc_client([{"success": True}])),
    )
    with pytest.raises(VoiceSessionEntitlementError) as malformed_error:
        await reserve_demo_call_slot(uuid4())
    assert malformed_error.value.code == DEMO_CALL_RESERVATION_UNAVAILABLE


@pytest.mark.asyncio
async def test_reserve_demo_call_if_needed_skips_non_demo_and_checks_demo(monkeypatch):
    reserve = AsyncMock(return_value=DemoCallReservation("r", "s", 1, 60))
    monkeypatch.setattr(entitlement, "reserve_demo_call_slot", reserve)

    assert await reserve_demo_call_if_needed(_agent(is_demo=False)) is None
    demo = _agent(is_demo=True, calls_remaining=1)
    result = await reserve_demo_call_if_needed(demo)

    assert result is not None
    reserve.assert_awaited_once_with(demo.id)


@pytest.mark.asyncio
async def test_reserve_demo_call_if_needed_rejects_exhausted_before_rpc(monkeypatch):
    reserve = AsyncMock()
    monkeypatch.setattr(entitlement, "reserve_demo_call_slot", reserve)

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await reserve_demo_call_if_needed(_agent(is_demo=True, calls_remaining=0))

    assert exc_info.value.code == DEMO_CALL_LIMIT_REACHED
    reserve.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_demo_call_reservation_accepts_success(monkeypatch):
    client = _rpc_client([{"success": True}])
    monkeypatch.setattr(entitlement, "supabase_config", SimpleNamespace(client=client))
    agent_id = uuid4()

    await consume_demo_call_reservation(
        agent_id=agent_id,
        session_id="session-1",
        reservation_id="reservation-1",
    )

    client.rpc.assert_called_once_with(
        "consume_demo_voice_call",
        {
            "p_agent_id": str(agent_id),
            "p_session_id": "session-1",
            "p_reservation_id": "reservation-1",
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        ("demo_call_already_used", DEMO_CALL_ALREADY_USED),
        ("demo_call_reservation_not_found", DEMO_CALL_RESERVATION_INVALID),
    ],
)
async def test_consume_demo_call_reservation_maps_rpc_errors(
    monkeypatch, error, expected_code
):
    monkeypatch.setattr(
        entitlement,
        "supabase_config",
        SimpleNamespace(client=_rpc_client([{"success": False, "error": error}])),
    )

    with pytest.raises(VoiceSessionEntitlementError) as exc_info:
        await consume_demo_call_reservation(
            agent_id=uuid4(),
            session_id="session-1",
            reservation_id="reservation-1",
        )

    assert exc_info.value.code == expected_code


@pytest.mark.asyncio
async def test_consume_demo_call_reservation_maps_missing_client_and_provider_failure(
    monkeypatch,
):
    monkeypatch.setattr(entitlement, "supabase_config", SimpleNamespace(client=None))
    with pytest.raises(VoiceSessionEntitlementError) as missing_error:
        await consume_demo_call_reservation(
            agent_id=uuid4(), session_id="s", reservation_id="r"
        )
    assert missing_error.value.code == DEMO_CALL_RESERVATION_UNAVAILABLE

    client = MagicMock()
    client.rpc.side_effect = RuntimeError("provider down")
    monkeypatch.setattr(entitlement, "supabase_config", SimpleNamespace(client=client))
    with pytest.raises(VoiceSessionEntitlementError) as provider_error:
        await consume_demo_call_reservation(
            agent_id=uuid4(), session_id="s", reservation_id="r"
        )
    assert provider_error.value.code == DEMO_CALL_RESERVATION_UNAVAILABLE
