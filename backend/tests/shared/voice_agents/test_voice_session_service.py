"""Tests for WebSocket voice session JWT create/verify (Pipecat transport)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from shared.config.settings import settings
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

    def test_create_session_rejects_empty_demo_reservation(self) -> None:
        service = VoiceSessionService(jwt_secret="test-voice-ws-secret")

        with pytest.raises(ValueError, match="reservation id"):
            service.create_session_token(
                agent_id=str(uuid4()),
                user_id="public_visitor",
                demo_reservation_id="",
            )

    def test_create_session_requires_a_jwt_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "jwt_secret_key", None)
        service = VoiceSessionService(jwt_secret=None)

        with pytest.raises(ValueError, match="JWT secret"):
            service.create_session_token(agent_id=str(uuid4()), user_id="visitor")

    def test_verify_rejects_wrong_secret(self) -> None:
        service_a = VoiceSessionService(jwt_secret="secret-a")
        service_b = VoiceSessionService(jwt_secret="secret-b")
        token, _ = service_a.create_session_token(
            agent_id=str(uuid4()),
            user_id=str(uuid4()),
        )
        assert service_b.verify_session_token(token) is None

    def test_verify_returns_none_without_secret_or_token(
        self, session_service: VoiceSessionService
    ) -> None:
        assert session_service.verify_session_token("") is None
        assert (
            VoiceSessionService(jwt_secret=None).verify_session_token("token") is None
        )

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

    def test_demo_claims_round_trip(self, session_service: VoiceSessionService) -> None:
        reservation_id = str(uuid4())
        token, session_id = session_service.create_session_token(
            agent_id=str(uuid4()),
            user_id="public_visitor",
            purpose="public",
            session_id="demo-session-1",
            demo_reservation_id=reservation_id,
            demo_max_call_duration_seconds=600,
        )

        claims = session_service.verify_session_token(token)

        assert claims is not None
        assert session_id == "demo-session-1"
        assert claims.demo_reservation_id == reservation_id
        assert claims.demo_max_call_duration_seconds == 600

    @pytest.mark.parametrize("duration", [0, -2])
    def test_demo_claim_rejects_invalid_duration(
        self, session_service: VoiceSessionService, duration: int
    ) -> None:
        with pytest.raises(ValueError, match="Demo max call duration"):
            session_service.create_session_token(
                agent_id=str(uuid4()),
                user_id="public_visitor",
                demo_max_call_duration_seconds=duration,
            )

    def test_verify_rejects_malformed_demo_claims(
        self, session_service: VoiceSessionService
    ) -> None:
        token = jwt.encode(
            {
                "type": VOICE_SESSION_TOKEN_TYPE,
                "agent_id": str(uuid4()),
                "user_id": "visitor",
                "session_id": "session",
                "purpose": "public",
                "demo_reservation_id": "reservation",
                "demo_max_call_duration_seconds": 0,
            },
            "test-voice-ws-secret",
            algorithm="HS256",
        )

        assert session_service.verify_session_token(token) is None

    def test_verify_rejects_malformed_optional_claim_types(
        self, session_service: VoiceSessionService
    ) -> None:
        base_claims = {
            "type": VOICE_SESSION_TOKEN_TYPE,
            "agent_id": str(uuid4()),
            "user_id": "visitor",
            "session_id": "session",
            "purpose": "public",
        }
        for field, value in {
            "call_sid": 123,
            "demo_reservation_id": 123,
            "demo_max_call_duration_seconds": True,
        }.items():
            token = jwt.encode(
                {**base_claims, field: value},
                "test-voice-ws-secret",
                algorithm="HS256",
            )
            assert session_service.verify_session_token(token) is None

    def test_verify_rejects_missing_required_claims(
        self, session_service: VoiceSessionService
    ) -> None:
        token = jwt.encode(
            {
                "type": VOICE_SESSION_TOKEN_TYPE,
                "agent_id": str(uuid4()),
                "user_id": "visitor",
                "session_id": "session",
            },
            "test-voice-ws-secret",
            algorithm="HS256",
        )

        assert session_service.verify_session_token(token) is None

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
