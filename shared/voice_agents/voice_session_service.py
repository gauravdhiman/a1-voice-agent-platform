"""Voice WebSocket session tokens for the Pipecat transport.

Creates and verifies short-lived JWTs (`voice_ws_session`) that authorize a
browser or Twilio Media Streams bridge to open a WebSocket against the
``voice-ws`` service. These JWTs are distinct from Supabase auth tokens.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import jwt

from shared.config.settings import settings

logger = logging.getLogger(__name__)

VOICE_SESSION_TOKEN_TYPE = "voice_ws_session"

VoiceSessionPurpose = Literal["test_call", "embed", "public", "phone"]


@dataclass(frozen=True)
class VoiceSessionClaims:
    """Verified claims from a voice WebSocket session JWT."""

    agent_id: str
    user_id: str
    session_id: str
    purpose: str
    call_sid: Optional[str] = None
    demo_reservation_id: Optional[str] = None
    demo_max_call_duration_seconds: Optional[int] = None
    token_type: str = VOICE_SESSION_TOKEN_TYPE


class VoiceSessionService:
    """Issue and validate Pipecat/WebSocket voice session tokens.

    Attributes:
        jwt_secret: HS256 secret shared by backend and ``voice-ws``.
        default_ttl: Token lifetime when ``expires_in`` is omitted.
    """

    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        default_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        """Initialize the session service.

        Args:
            jwt_secret: Signing secret. Defaults to ``settings.jwt_secret_key``.
            default_ttl: Default token lifetime (15 minutes).
        """
        self.jwt_secret = jwt_secret or settings.jwt_secret_key or ""
        self.default_ttl = default_ttl

    def create_session_token(
        self,
        *,
        agent_id: str,
        user_id: str,
        purpose: VoiceSessionPurpose = "test_call",
        expires_in: Optional[timedelta] = None,
        session_id: Optional[str] = None,
        call_sid: Optional[str] = None,
        demo_reservation_id: Optional[str] = None,
        demo_max_call_duration_seconds: Optional[int] = None,
    ) -> tuple[str, str]:
        """Create a signed session JWT for the voice-ws WebSocket.

        Args:
            agent_id: Voice agent UUID string the session may speak as.
            user_id: Authenticated (or anonymous) caller identity.
            purpose: Call surface (test_call, embed, public, phone).
            expires_in: Optional TTL override.
            session_id: Optional pre-assigned session id; generated if omitted.
            call_sid: Optional provider call identifier for phone sessions.
            demo_reservation_id: Optional one-time reservation for a demo call.
            demo_max_call_duration_seconds: Optional duration captured when the
                demo reservation was created; ``-1`` means unlimited.

        Returns:
            Tuple of ``(jwt_token, session_id)``.

        Raises:
            ValueError: If JWT secret is not configured.
        """
        if not self.jwt_secret:
            raise ValueError("JWT secret is not configured for voice sessions")
        if demo_reservation_id is not None and (
            not isinstance(demo_reservation_id, str) or not demo_reservation_id
        ):
            raise ValueError("Demo reservation id must be a non-empty string")
        if demo_max_call_duration_seconds is not None and (
            isinstance(demo_max_call_duration_seconds, bool)
            or not isinstance(demo_max_call_duration_seconds, int)
            or (
                demo_max_call_duration_seconds != -1
                and demo_max_call_duration_seconds <= 0
            )
        ):
            raise ValueError(
                "Demo max call duration must be -1 (unlimited) or greater than 0"
            )

        sid = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ttl = expires_in if expires_in is not None else self.default_ttl
        payload = {
            "type": VOICE_SESSION_TOKEN_TYPE,
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": sid,
            "purpose": purpose,
            "iat": now,
            "exp": now + ttl,
            "jti": str(uuid.uuid4()),
        }
        if call_sid:
            payload["call_sid"] = call_sid
        if demo_reservation_id is not None:
            payload["demo_reservation_id"] = demo_reservation_id
        if demo_max_call_duration_seconds is not None:
            payload["demo_max_call_duration_seconds"] = demo_max_call_duration_seconds
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        logger.info(
            "Created voice_ws session token session_id=%s agent_id=%s purpose=%s",
            sid,
            agent_id,
            purpose,
        )
        return token, sid

    def verify_session_token(self, token: str) -> Optional[VoiceSessionClaims]:
        """Verify a voice session JWT and return claims, or None if invalid.

        Args:
            token: Bearer / query JWT from the WebSocket client.

        Returns:
            :class:`VoiceSessionClaims` on success, else ``None``.
        """
        if not self.jwt_secret or not token:
            return None
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
            )
        except jwt.PyJWTError as exc:
            logger.warning("voice_ws session token rejected: %s", exc)
            return None

        if payload.get("type") != VOICE_SESSION_TOKEN_TYPE:
            logger.warning("voice_ws session token has unexpected type")
            return None

        agent_id = payload.get("agent_id")
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        purpose = payload.get("purpose")
        call_sid = payload.get("call_sid")
        demo_reservation_id = payload.get("demo_reservation_id")
        demo_max_call_duration_seconds = payload.get("demo_max_call_duration_seconds")
        if call_sid is not None and (not isinstance(call_sid, str) or not call_sid):
            return None
        if demo_reservation_id is not None and (
            not isinstance(demo_reservation_id, str) or not demo_reservation_id
        ):
            return None
        if demo_max_call_duration_seconds is not None and (
            isinstance(demo_max_call_duration_seconds, bool)
            or not isinstance(demo_max_call_duration_seconds, int)
            or (
                demo_max_call_duration_seconds != -1
                and demo_max_call_duration_seconds <= 0
            )
        ):
            return None
        if not all(
            isinstance(v, str) and v for v in (agent_id, user_id, session_id, purpose)
        ):
            return None

        return VoiceSessionClaims(
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            purpose=purpose,
            call_sid=call_sid,
            demo_reservation_id=demo_reservation_id,
            demo_max_call_duration_seconds=demo_max_call_duration_seconds,
            token_type=VOICE_SESSION_TOKEN_TYPE,
        )


voice_session_service = VoiceSessionService()
