"""Tests for test-token transport switching (pipecat vs livekit)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from shared.voice_agents.voice_session_service import VOICE_SESSION_TOKEN_TYPE


@pytest.mark.asyncio
async def test_get_test_token_pipecat_returns_ws_url() -> None:
    """When VOICE_TRANSPORT=pipecat, return session JWT + wsUrl (no LiveKit)."""
    import sys

    from src.voice_agents.routes import get_test_token

    routes_mod = sys.modules["src.voice_agents.routes"]

    agent_id = uuid4()
    org_id = uuid4()
    user_id = uuid4()

    agent = MagicMock()
    agent.id = agent_id
    agent.organization_id = org_id
    user_profile = MagicMock()

    with (
        patch.object(routes_mod.settings, "voice_transport", "pipecat"),
        patch.object(routes_mod.settings, "voice_ws_public_url", "ws://localhost:7860"),
        patch.object(
            routes_mod.voice_agent_service,
            "get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ),
        patch.object(routes_mod, "assert_has_permission"),
        patch.object(
            routes_mod.voice_session_service,
            "create_session_token",
            return_value=("session.jwt.token", "sess-123"),
        ) as create_tok,
        patch.object(routes_mod.livekit_service, "generate_test_token") as livekit_tok,
    ):
        result = await get_test_token(
            agent_id=agent_id,
            user_data=(user_id, user_profile),
        )

    assert result.transport == "pipecat"
    assert result.token == "session.jwt.token"
    assert result.wsUrl == "ws://localhost:7860/ws"
    assert result.sessionId == "sess-123"
    assert result.serverUrl is None
    assert result.roomName is None
    create_tok.assert_called_once()
    livekit_tok.assert_not_called()


@pytest.mark.asyncio
async def test_get_test_token_livekit_path_unchanged() -> None:
    """When VOICE_TRANSPORT=livekit, keep LiveKit room token + dispatch."""
    import sys

    from src.voice_agents.routes import get_test_token

    routes_mod = sys.modules["src.voice_agents.routes"]

    agent_id = uuid4()
    org_id = uuid4()
    user_id = uuid4()

    agent = MagicMock()
    agent.id = agent_id
    agent.organization_id = org_id
    user_profile = MagicMock()

    with (
        patch.object(routes_mod.settings, "voice_transport", "livekit"),
        patch.object(
            routes_mod.voice_agent_service,
            "get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ),
        patch.object(routes_mod, "assert_has_permission"),
        patch.object(
            routes_mod.livekit_service,
            "generate_test_token",
            return_value=("lk-token", "wss://lk.example", f"test_{agent_id}_abc"),
        ),
        patch.object(
            routes_mod.livekit_service,
            "create_room",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            routes_mod.livekit_service,
            "create_agent_dispatch",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await get_test_token(
            agent_id=agent_id,
            user_data=(user_id, user_profile),
        )

    assert result.transport == "livekit"
    assert result.token == "lk-token"
    assert result.serverUrl == "wss://lk.example"
    assert result.roomName.startswith("test_")
    assert result.wsUrl is None


@pytest.mark.asyncio
async def test_get_test_token_pipecat_requires_jwt_secret() -> None:
    """Pipecat path returns 503 when session JWT cannot be created."""
    import sys

    from src.voice_agents.routes import get_test_token

    routes_mod = sys.modules["src.voice_agents.routes"]

    agent_id = uuid4()
    agent = MagicMock()
    agent.organization_id = uuid4()

    with (
        patch.object(routes_mod.settings, "voice_transport", "pipecat"),
        patch.object(
            routes_mod.voice_agent_service,
            "get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ),
        patch.object(routes_mod, "assert_has_permission"),
        patch.object(
            routes_mod.voice_session_service,
            "create_session_token",
            side_effect=ValueError("JWT secret is not configured"),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_test_token(
                agent_id=agent_id,
                user_data=(uuid4(), MagicMock()),
            )
    assert exc.value.status_code == 503


def test_voice_session_token_type_constant() -> None:
    assert VOICE_SESSION_TOKEN_TYPE == "voice_ws_session"
