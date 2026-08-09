"""Tests for test-token Pipecat WebSocket bootstrap."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from shared.billing.voice_session_entitlement import VoiceSessionEntitlementError
from shared.voice_agents.voice_session_service import VOICE_SESSION_TOKEN_TYPE


@pytest.mark.asyncio
async def test_get_test_token_pipecat_returns_ws_url() -> None:
    """Return session JWT + wsUrl for browser test calls."""
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
        patch.object(routes_mod.settings, "voice_ws_public_url", "ws://localhost:7860"),
        patch.object(
            routes_mod.voice_agent_service,
            "get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ),
        patch.object(routes_mod, "assert_has_permission"),
        patch.object(
            routes_mod,
            "assert_voice_session_allowed",
            new=AsyncMock(),
            create=True,
        ),
        patch.object(
            routes_mod.voice_session_service,
            "create_session_token",
            return_value=("session.jwt.token", "sess-123"),
        ) as create_tok,
    ):
        result = await get_test_token(
            agent_id=agent_id,
            user_data=(user_id, user_profile),
        )

    assert result.transport == "pipecat"
    assert result.token == "session.jwt.token"
    assert result.wsUrl == "ws://localhost:7860/ws"
    assert result.sessionId == "sess-123"
    create_tok.assert_called_once()


@pytest.mark.asyncio
async def test_get_test_token_pipecat_requires_jwt_secret() -> None:
    """Returns 503 when session JWT cannot be created."""
    import sys

    from src.voice_agents.routes import get_test_token

    routes_mod = sys.modules["src.voice_agents.routes"]

    agent_id = uuid4()
    agent = MagicMock()
    agent.organization_id = uuid4()

    with (
        patch.object(
            routes_mod.voice_agent_service,
            "get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ),
        patch.object(routes_mod, "assert_has_permission"),
        patch.object(
            routes_mod,
            "assert_voice_session_allowed",
            new=AsyncMock(),
            create=True,
        ),
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


@pytest.mark.asyncio
async def test_get_test_token_rejects_insufficient_credits_before_issuing_token() -> (
    None
):
    """Return a billing error before a browser receives a rejected WS token."""
    import sys

    from src.voice_agents.routes import get_test_token

    routes_mod = sys.modules["src.voice_agents.routes"]

    agent_id = uuid4()
    organization_id = uuid4()
    agent = MagicMock()
    agent.organization_id = organization_id

    with (
        patch.object(
            routes_mod.voice_agent_service,
            "get_agent_by_id",
            new=AsyncMock(return_value=(agent, None)),
        ),
        patch.object(routes_mod, "assert_has_permission"),
        patch.object(
            routes_mod,
            "assert_voice_session_allowed",
            new=AsyncMock(
                side_effect=VoiceSessionEntitlementError(
                    "INSUFFICIENT_CREDITS",
                    "Insufficient credits to start a voice call.",
                )
            ),
            create=True,
        ) as assert_allowed,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_test_token(
                agent_id=agent_id,
                user_data=(uuid4(), MagicMock()),
            )

    assert exc.value.status_code == 402
    assert exc.value.detail == {
        "code": "INSUFFICIENT_CREDITS",
        "message": "Insufficient credits to start a voice call.",
    }
    assert_allowed.assert_awaited_once_with(organization_id)


def test_voice_session_token_type_constant() -> None:
    assert VOICE_SESSION_TOKEN_TYPE == "voice_ws_session"


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [("MAX_CONCURRENT_CALLS", 409), ("UNKNOWN", 403)],
)
def test_voice_session_entitlement_errors_map_to_http_status(
    code: str, expected_status: int
) -> None:
    """Map non-credit entitlement failures to stable API statuses."""
    from src.voice_agents.routes import _voice_session_http_exception

    error = _voice_session_http_exception(
        VoiceSessionEntitlementError(code, "voice session denied")
    )

    assert error.status_code == expected_status
    assert error.detail == {"code": code, "message": "voice session denied"}
