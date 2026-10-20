"""A storage outage must stop voice setup before any provider pipeline starts."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from src import bot

from shared.voice_agents.voice_session_service import VoiceSessionClaims


@pytest.mark.asyncio
@pytest.mark.parametrize("tracked", [None, "raise"])
async def test_tracking_failure_closes_mcp_and_never_starts_transport(
    monkeypatch, tracked
):
    connector = SimpleNamespace(close=AsyncMock())
    bundle = SimpleNamespace(
        agent=SimpleNamespace(id=uuid4(), organization_id=uuid4()),
        tools=SimpleNamespace(mcp_clients=[connector]),
        speech_config=Mock(),
    )
    monkeypatch.setattr(bot, "prepare_voice_session", AsyncMock(return_value=bundle))
    monkeypatch.setattr(bot, "annotate_speech_configuration", Mock())
    monkeypatch.setattr(
        bot,
        "start_call_tracking",
        AsyncMock(
            return_value=None,
            side_effect=RuntimeError("storage offline") if tracked else None,
        ),
    )
    transport, runner = Mock(), Mock()
    monkeypatch.setattr(bot, "FastAPIWebsocketTransport", transport)
    monkeypatch.setattr(bot, "PipelineRunner", runner)
    claims = VoiceSessionClaims(
        agent_id=str(bundle.agent.id),
        user_id="test",
        session_id="tracking-failure",
        purpose="test_call",
    )
    with pytest.raises(RuntimeError):
        await bot.run_bot(Mock(), claims)
    connector.close.assert_awaited_once()
    transport.assert_not_called()
    runner.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [False, True])
async def test_lost_lease_stops_provider_work(monkeypatch, error):
    monkeypatch.setattr(bot.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(
        bot,
        "renew_call_lease",
        AsyncMock(return_value=False, side_effect=TimeoutError() if error else None),
    )
    task = SimpleNamespace(cancel=AsyncMock())
    state = bot.CallFailureState()
    await bot._maintain_call_lease(task, "call-test", "session-test", state)
    task.cancel.assert_awaited_once()
    assert state.failure.code == "call_storage_unavailable"


@pytest.mark.asyncio
async def test_healthy_lease_does_not_cancel_provider(monkeypatch):
    monkeypatch.setattr(
        bot.asyncio, "sleep", AsyncMock(side_effect=[None, asyncio.CancelledError()])
    )
    renew = AsyncMock(return_value=True)
    monkeypatch.setattr(bot, "renew_call_lease", renew)
    task = SimpleNamespace(cancel=AsyncMock())
    with pytest.raises(asyncio.CancelledError):
        await bot._maintain_call_lease(
            task, "call-test", "session-test", bot.CallFailureState()
        )
    renew.assert_awaited_once_with("call-test", "session-test")
    task.cancel.assert_not_awaited()
