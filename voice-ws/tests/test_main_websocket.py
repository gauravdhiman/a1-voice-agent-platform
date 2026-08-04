"""WebSocket auth tests for voice-ws main entrypoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from shared.voice_agents.voice_session_service import voice_session_service


@pytest.fixture
def client() -> TestClient:
    from src.main import app

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
