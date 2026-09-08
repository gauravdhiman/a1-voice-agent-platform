"""Public organization page access tokens and Pipecat voice session tokens.

Unauthenticated visitors on ``/o/{slug}`` receive short-lived access tokens
(passphrase gate) and ``voice_ws_session`` JWTs for browser calls over
``voice-ws`` WebSocket transport.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from shared.billing.voice_session_entitlement import DemoCallReservation
from shared.config.settings import settings
from shared.voice_agents.source_metadata import normalize_domain, normalize_source_url
from shared.voice_agents.voice_session_service import voice_session_service

logger = logging.getLogger(__name__)


class PublicPageAccessError(Exception):
    """Raised when public-page access token validation fails."""


class PublicPageService:
    """JWT access tokens and Pipecat voice session tokens for public org pages."""

    def __init__(self) -> None:
        self.jwt_secret: str = (
            settings.jwt_secret_key or "public-page-dev-secret-change-in-prod"
        )
        self.access_token_expiry = timedelta(hours=12)
        self.call_token_expiry = timedelta(hours=1)

    def generate_access_token(self, *, organization_id: str, slug: str) -> str:
        """Issue a short-lived access token after passphrase verification."""
        payload: dict[str, Any] = {
            "type": "public_page_access",
            "organization_id": organization_id,
            "slug": slug,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + self.access_token_expiry,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def validate_access_token(
        self, token: str, *, organization_id: str, slug: str
    ) -> None:
        """Validate a public-page access token for the given org slug."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise PublicPageAccessError("Access token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise PublicPageAccessError("Invalid access token") from exc

        if payload.get("type") != "public_page_access":
            raise PublicPageAccessError("Invalid access token type")
        if payload.get("organization_id") != organization_id:
            raise PublicPageAccessError("Access token organization mismatch")
        if payload.get("slug") != slug:
            raise PublicPageAccessError("Access token slug mismatch")

    def generate_call_token(
        self,
        *,
        agent_id: str,
        demo_reservation: Optional[DemoCallReservation] = None,
        source_type: str = "web_public",
        source_url: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Generate a Pipecat voice session for a public-page visitor call.

        Returns:
            Tuple of ``(voice_token, ws_url, session_id)``.
        """
        try:
            normalized_source_url = normalize_source_url(source_url)
            source_domain = normalize_domain(normalized_source_url)
            visitor_id = f"public_visitor_{uuid.uuid4().hex[:8]}"
            voice_token, session_id = voice_session_service.create_session_token(
                agent_id=agent_id,
                user_id=visitor_id,
                purpose="public",
                expires_in=self.call_token_expiry,
                session_id=(demo_reservation.session_id if demo_reservation else None),
                source_type=source_type,
                source_url=normalized_source_url,
                source_domain=source_domain,
                demo_reservation_id=(
                    demo_reservation.reservation_id if demo_reservation else None
                ),
                demo_max_call_duration_seconds=(
                    demo_reservation.max_call_duration_seconds
                    if demo_reservation
                    else None
                ),
            )
            base = (settings.voice_ws_public_url or "ws://localhost:7860").rstrip("/")
            ws_url = f"{base}/ws"
            return voice_token, ws_url, session_id
        except Exception as exc:
            logger.error("Failed to generate public call token: %s", exc, exc_info=True)
            return None, None, None


public_page_service = PublicPageService()

__all__ = [
    "PublicPageAccessError",
    "PublicPageService",
    "public_page_service",
]
