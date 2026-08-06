"""Tests for OAuth session handoff API route."""

import time
from unittest.mock import patch
from uuid import UUID

import jwt
import pytest
from src.auth.models import AuthResponse, UserProfile
from src.auth.oauth_handoff import HANDOFF_PURPOSE
from starlette.requests import Request


USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/session/handoff",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 8000),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


@pytest.mark.asyncio
async def test_session_handoff_returns_supabase_tokens() -> None:
    from src.auth.models import SessionHandoffRequest
    from src.auth.routes import session_handoff

    handoff = jwt.encode(
        {
            "purpose": HANDOFF_PURPOSE,
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "token_type": "bearer",
            "exp": int(time.time()) + 60,
        },
        "test-jwt-secret",
        algorithm="HS256",
    )

    with patch("src.auth.routes.consume_session_handoff_token") as consume:
        consume.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "token_type": "bearer",
        }

        response = await session_handoff(
            request=_request(),
            body=SessionHandoffRequest(handoff=handoff),
        )

    assert response.access_token == "access-token"
    assert response.refresh_token == "refresh-token"
