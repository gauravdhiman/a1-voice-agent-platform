"""Tests for WebSocket voice session JWT create/verify (Pipecat transport)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from shared.voice_agents.voice_session_service import (
    VOICE_SESSION_TOKEN_TYPE,
    VoiceSessionClaims,
    VoiceSessionService,
)


@pytest.fixture
def session_service() -> VoiceSessionService:
    return VoiceSessionService(jwt_secret="test-voice-ws-secret")


class TestVoiceSessionService:
    """Unit tests for voice session token lifecycle."""

    def test_create_session_returns_token_and_ids(
        self, session_service: VoiceSessionService
    ) -> None:
        agent_id = str(uuid4())
        user_id = str(uuid4())

        token, session_id = session_service.create_session_token(
            agent_id=agent_id,
            user_id=user_id,
            purpose="test_call",
        )

        assert token
        assert session_id
        claims = session_service.verify_session_token(token)
        assert claims is not None
        assert claims.agent_id == agent_id
        assert claims.user_id == user_id
        assert claims.session_id == session_id
        assert claims.purpose == "test_call"
        assert claims.token_type == VOICE_SESSION_TOKEN_TYPE

    def test_verify_rejects_wrong_secret(self) -> None:
        service_a = VoiceSessionService(jwt_secret="secret-a")
        service_b = VoiceSessionService(jwt_secret="secret-b")
        token, _ = service_a.create_session_token(
            agent_id=str(uuid4()),
            user_id=str(uuid4()),
        )
        assert service_b.verify_session_token(token) is None

    def test_phone_session_round_trips_twilio_call_sid(
        self, session_service: VoiceSessionService
    ) -> None:
        """Phone claims preserve the provider CallSid for lifecycle tracking."""
        call_sid = "CA123456789"
        token, _ = session_service.create_session_token(
            agent_id=str(uuid4()),
            user_id="+15551234567",
            purpose="phone",
            call_sid=call_sid,
        )

        claims = session_service.verify_session_token(token)

        assert claims is not None
        assert claims.call_sid == call_sid

    def test_verify_rejects_wrong_token_type(
        self, session_service: VoiceSessionService
    ) -> None:
        bad = jwt.encode(
            {
                "type": "embed_access",
                "agent_id": str(uuid4()),
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "purpose": "test_call",
            },
            "test-voice-ws-secret",
            algorithm="HS256",
        )
        assert session_service.verify_session_token(bad) is None

    def test_verify_rejects_expired_token(
        self, session_service: VoiceSessionService
    ) -> None:
        token, _ = session_service.create_session_token(
            agent_id=str(uuid4()),
            user_id=str(uuid4()),
            expires_in=timedelta(seconds=-1),
        )
        assert session_service.verify_session_token(token) is None

    def test_claims_dataclass_fields(self) -> None:
        claims = VoiceSessionClaims(
            agent_id="a",
            user_id="u",
            session_id="s",
            purpose="test_call",
            token_type=VOICE_SESSION_TOKEN_TYPE,
        )
        assert claims.purpose == "test_call"
