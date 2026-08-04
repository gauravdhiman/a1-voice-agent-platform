"""Embed call button token and validation service.

Issues short-lived ``voice_ws_session`` JWTs for browser embed calls over the
Pipecat WebSocket transport. Domain validation and rate limiting remain here;
LiveKit room tokens are no longer used.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from shared.config.settings import settings
from shared.voice_agents.voice_session_service import voice_session_service

logger = logging.getLogger(__name__)


class EmbedTokenError(Exception):
    """Exception raised for embed token errors."""


class EmbedValidationError(Exception):
    """Exception raised for embed validation errors."""


class EmbedService:
    """Service for embed call button functionality.

    Generates:
    - An audit ``embed_token`` JWT scoped to the embed configuration
    - A ``voice_ws_session`` JWT for the Pipecat WebSocket connection

    Attributes:
        jwt_secret: Secret for signing embed audit tokens.
        embed_token_expiry: Lifetime for embed audit tokens.
    """

    def __init__(self) -> None:
        self.jwt_secret: str = settings.jwt_secret_key or "embed-dev-secret-key-change-in-production"
        self.embed_token_expiry: timedelta = timedelta(hours=1)

    def generate_embed_token(
        self,
        agent_id: str,
        embed_config_id: str,
        domain: Optional[str],
        ip_address: Optional[str],
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Generate tokens for an embed-based browser voice call.

        Args:
            agent_id: UUID of the agent to connect to.
            embed_config_id: UUID of the embed configuration.
            domain: Domain that initiated the request (for validation/audit).
            ip_address: Visitor IP address (for tracking).

        Returns:
            Tuple of ``(embed_token, voice_token, ws_url, session_id)`` or
            ``(None, None, None, None)`` if generation failed.
        """
        try:
            visitor_id = f"embed_{embed_config_id}"
            voice_token, session_id = voice_session_service.create_session_token(
                agent_id=agent_id,
                user_id=visitor_id,
                purpose="embed",
                expires_in=self.embed_token_expiry,
            )

            embed_payload: dict[str, Any] = {
                "sub": embed_config_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "domain": domain,
                "ip_address": ip_address,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + self.embed_token_expiry,
                "jti": str(uuid.uuid4()),
                "type": "embed_access",
            }
            embed_token = jwt.encode(embed_payload, self.jwt_secret, algorithm="HS256")

            base = (settings.voice_ws_public_url or "ws://localhost:7860").rstrip("/")
            ws_url = f"{base}/ws"

            logger.info(
                "Generated embed voice session agent=%s config=%s session=%s",
                agent_id,
                embed_config_id,
                session_id,
            )
            return embed_token, voice_token, ws_url, session_id
        except Exception as e:
            logger.error("Failed to generate embed token: %s", e, exc_info=True)
            return None, None, None, None

    def validate_embed_token(self, token: str) -> dict[str, Any]:
        """Validate an embed audit token and return its payload."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            if payload.get("type") != "embed_access":
                raise EmbedValidationError("Invalid token type")
            return payload
        except jwt.ExpiredSignatureError as exc:
            raise EmbedValidationError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise EmbedValidationError(f"Invalid token: {exc}") from exc

    def validate_domain(
        self,
        allowed_domains: Optional[list[str]],
        request_domain: Optional[str],
    ) -> bool:
        """Return whether ``request_domain`` is allowed for this embed config."""
        if not allowed_domains:
            return True
        if not request_domain:
            logger.warning("Embed request without domain rejected")
            return False

        normalized_request = self._normalize_domain(request_domain)
        for allowed in allowed_domains:
            normalized_allowed = self._normalize_domain(allowed)
            if normalized_request == normalized_allowed:
                return True
            if normalized_request.endswith(f".{normalized_allowed}"):
                return True

        logger.warning(
            "Domain %s not in allowed list: %s", request_domain, allowed_domains
        )
        return False

    def _normalize_domain(self, domain: str) -> str:
        """Normalize a domain string for comparison."""
        domain = domain.lower()
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        if domain.startswith("www."):
            domain = domain[4:]
        domain = domain.split("/", 1)[0]
        if ":" in domain:
            domain = domain.rsplit(":", 1)[0]
        return domain

    def check_rate_limit(
        self,
        embed_config_id: str,
        daily_limit: int,
        current_usage: int,
    ) -> bool:
        """Return whether embed usage is within the configured daily limit."""
        if current_usage >= daily_limit:
            logger.warning(
                "Embed config %s exceeded daily limit (%s/%s)",
                embed_config_id,
                current_usage,
                daily_limit,
            )
            return False
        return True


embed_service = EmbedService()
