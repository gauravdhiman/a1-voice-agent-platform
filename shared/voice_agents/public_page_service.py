"""Public organization page call tokens (unauthenticated visitor calls).

Generates LiveKit rooms with the ``public_{agent_id}_{random}`` prefix so the
worker can dispatch without embed configuration.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from shared.config.settings import settings
from shared.voice_agents.livekit_service import LiveKitService

logger = logging.getLogger(__name__)


class PublicPageAccessError(Exception):
    """Raised when public-page access token validation fails."""


class PublicPageService:
    """JWT access tokens and LiveKit call tokens for public org pages."""

    def __init__(self) -> None:
        self.livekit_service = LiveKitService()
        self.jwt_secret: str = (
            settings.livekit_api_secret or "public-page-dev-secret-change-in-prod"
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
        self, *, agent_id: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Generate a LiveKit token for a public-page voice call.

        Returns:
            Tuple of (livekit_token, server_url, room_name).
        """
        if not all(
            [
                self.livekit_service.api_key,
                self.livekit_service.api_secret,
                self.livekit_service.url,
            ]
        ):
            logger.error("LiveKit not configured — cannot generate public call token")
            return None, None, None

        random_suffix = uuid.uuid4().hex[:8]
        room_name = f"public_{agent_id}_{random_suffix}"
        try:
            livekit_token = self.livekit_service.generate_token(
                room_name=room_name,
                identity=f"public_visitor_{random_suffix}",
                name="Visitor",
                expiration=self.call_token_expiry,
            )
            return livekit_token, self.livekit_service.url or "", room_name
        except Exception as exc:
            logger.error("Failed to generate public call token: %s", exc, exc_info=True)
            return None, None, None


public_page_service = PublicPageService()

__all__ = [
    "PublicPageAccessError",
    "PublicPageService",
    "public_page_service",
]
