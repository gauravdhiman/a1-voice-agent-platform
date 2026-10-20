"""WebSocket auth tests for voice-ws main entrypoint."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from shared.voice_agents.voice_session_service import voice_session_service


@pytest.fixture
def client(monkeypatch) -> TestClient:
    from src.main import app, session_service

    secret = "isolated-voice-test-signing-key-at-least-32-bytes"
    monkeypatch.setattr(voice_session_service, "jwt_secret", secret)
    monkeypatch.setattr(session_service, "jwt_secret", secret)

    return TestClient(app)


class TestVoiceWsWebSocketAuth:
    """Ensure /ws rejects bad tokens before accepting the socket."""

    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "voice-ws"

    def test_ws_rejects_invalid_token(self, client: TestClient) -> None:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=not-a-valid-jwt"):
                pass

    def test_ws_accepts_valid_token_and_runs_bot(self, client: TestClient) -> None:
        token, _ = voice_session_service.create_session_token(
            agent_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000002",
            purpose="test_call",
        )
        with patch("src.main.run_bot", new=AsyncMock()) as run_bot_mock:
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.send_text("ping")
            run_bot_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_demo_precheck_consumes_reservation_and_returns_duration(
        self,
    ) -> None:
        from src.main import _precheck_voice_session

        from shared.voice_agents.voice_session_service import VoiceSessionClaims

        agent_id = uuid4()
        claims = VoiceSessionClaims(
            agent_id=str(agent_id),
            user_id="public-visitor",
            session_id="demo-session",
            purpose="public",
            demo_reservation_id="reservation-1",
            demo_max_call_duration_seconds=600,
        )
        agent = SimpleNamespace(
            id=agent_id,
            organization_id=uuid4(),
            is_demo=True,
        )

        with patch(
            "src.main.voice_agent_service.get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ), patch(
            "src.main.consume_demo_call_reservation",
            new=AsyncMock(),
        ) as consume:
            result = await _precheck_voice_session(claims)

        assert result == 600
        consume.assert_awaited_once_with(
            agent_id=agent_id,
            session_id="demo-session",
            reservation_id="reservation-1",
        )

    @pytest.mark.asyncio
    async def test_demo_precheck_rejects_token_without_reservation(self) -> None:
        from src.main import _precheck_voice_session

        from shared.billing.voice_session_entitlement import (
            VoiceSessionEntitlementError,
        )
        from shared.voice_agents.voice_session_service import VoiceSessionClaims

        agent_id = uuid4()
        claims = VoiceSessionClaims(
            agent_id=str(agent_id),
            user_id="public-visitor",
            session_id="demo-session",
            purpose="public",
        )
        agent = SimpleNamespace(
            id=agent_id,
            organization_id=uuid4(),
            is_demo=True,
        )

        with patch(
            "src.main.voice_agent_service.get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ):
            with pytest.raises(VoiceSessionEntitlementError) as exc_info:
                await _precheck_voice_session(claims)

        assert exc_info.value.code == "DEMO_CALL_RESERVATION_INVALID"

    @pytest.mark.asyncio
    async def test_duration_timer_cancels_pipeline(self) -> None:
        from src.bot import _cancel_pipeline_after

        task = MagicMock()
        task.cancel = AsyncMock()

        await _cancel_pipeline_after(task, 0, "demo-session")

        task.cancel.assert_awaited_once_with()
