import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import jwt
from livekit import api

from shared.config.settings import settings
from shared.voice_agents.livekit_service import LiveKitService

logger = logging.getLogger(__name__)


class EmbedTokenError(Exception):
    """Exception raised for embed token errors."""

    pass


class EmbedValidationError(Exception):
    """Exception raised for embed validation errors."""

    pass


class EmbedService:
    """Service for managing embed call button functionality.

    This service handles:
    - Generating time-limited embed tokens for WebRTC connections
    - Validating embed tokens and domain restrictions
    - Tracking embed usage and rate limits
    - Creating LiveKit rooms for embed calls

    The embed token is a JWT that grants temporary access to a specific
    LiveKit room. It's scoped to a single agent and expires after 1 hour.

    Attributes:
        livekit_service: LiveKitService instance for token generation
        jwt_secret: Secret key for signing embed tokens
    """

    def __init__(self) -> None:
        self.livekit_service = LiveKitService()
        # Use LiveKit secret as JWT secret for consistency
        self.jwt_secret: str = (
            settings.livekit_api_secret or "embed-dev-secret-key-change-in-production"
        )
        self.embed_token_expiry: timedelta = timedelta(hours=1)

    def generate_embed_token(
        self,
        agent_id: str,
        embed_config_id: str,
        domain: Optional[str],
        ip_address: Optional[str],
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Generate an embed token for browser-based agent calls.

        This method creates a JWT token that grants access to a LiveKit room
        for embed-based calls. The token is scoped to a specific agent and
        includes metadata for tracking and validation.

        Args:
            agent_id: UUID of the agent to connect to
            embed_config_id: UUID of the embed configuration
            domain: Domain that initiated the request (for validation)
            ip_address: IP address of the visitor (for tracking)

        Returns:
            Tuple of (embed_token, livekit_token, server_url, room_name)
            or (None, None, None, None) if generation failed

        Raises:
            EmbedTokenError: If token generation fails
        """
        try:
            # Generate unique room name for this embed session
            # Format: embed_{agent_id}_{random}
            random_suffix = uuid.uuid4().hex[:8]
            room_name = f"embed_{agent_id}_{random_suffix}"

            # Generate LiveKit token for the room
            livekit_token = self.livekit_service.generate_token(
                room_name=room_name,
                identity=f"embed_user_{random_suffix}",
                name="Website Visitor",
                expiration=self.embed_token_expiry,
            )

            # Generate embed JWT with metadata
            embed_payload: dict[str, Any] = {
                "sub": embed_config_id,
                "agent_id": agent_id,
                "room_name": room_name,
                "domain": domain,
                "ip_address": ip_address,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + self.embed_token_expiry,
                "jti": str(uuid.uuid4()),  # Unique token ID for revocation
                "type": "embed_access",
            }

            embed_token = jwt.encode(embed_payload, self.jwt_secret, algorithm="HS256")

            logger.info(
                f"Generated embed token for agent {agent_id}, "
                f"config {embed_config_id}, room {room_name}"
            )

            return (
                embed_token,
                livekit_token,
                self.livekit_service.url or "",
                room_name,
            )

        except Exception as e:
            logger.error(f"Failed to generate embed token: {e}", exc_info=True)
            return None, None, None, None

    def validate_embed_token(self, token: str) -> dict[str, Any]:
        """Validate an embed token and return its payload.

        Args:
            token: JWT token to validate

        Returns:
            Decoded token payload

        Raises:
            EmbedValidationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Verify token type
            if payload.get("type") != "embed_access":
                raise EmbedValidationError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise EmbedValidationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise EmbedValidationError(f"Invalid token: {e}")

    def validate_domain(
        self,
        allowed_domains: Optional[list[str]],
        request_domain: Optional[str],
    ) -> bool:
        """Validate if a domain is in the allowed list.

        Args:
            allowed_domains: List of allowed domains (None = allow all)
            request_domain: Domain making the request

        Returns:
            True if domain is allowed, False otherwise
        """
        # If no domains specified, allow all
        if not allowed_domains:
            return True

        # If request has no domain, reject (shouldn't happen in normal flow)
        if not request_domain:
            logger.warning("Embed request without domain rejected")
            return False

        # Normalize domain (remove protocol, www, trailing slash)
        normalized_request = self._normalize_domain(request_domain)

        for allowed in allowed_domains:
            normalized_allowed = self._normalize_domain(allowed)

            # Exact match
            if normalized_request == normalized_allowed:
                return True

            # Subdomain match (e.g., app.example.com matches example.com)
            if normalized_request.endswith(f".{normalized_allowed}"):
                return True

        logger.warning(f"Domain {request_domain} not in allowed list: {allowed_domains}")
        return False

    def _normalize_domain(self, domain: str) -> str:
        """Normalize a domain for comparison.

        Args:
            domain: Domain string to normalize

        Returns:
            Normalized domain (lowercase, no protocol, no www, no trailing slash)
        """
        # Convert to lowercase
        domain = domain.lower()

        # Remove protocol
        if "://" in domain:
            domain = domain.split("://", 1)[1]

        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove trailing slash and path
        domain = domain.split("/", 1)[0]

        # Remove port if present
        if ":" in domain:
            domain = domain.rsplit(":", 1)[0]

        return domain

    def check_rate_limit(
        self,
        embed_config_id: str,
        daily_limit: int,
        current_usage: int,
    ) -> bool:
        """Check if embed usage is within rate limits.

        Args:
            embed_config_id: UUID of the embed configuration
            daily_limit: Maximum allowed calls per day
            current_usage: Current day's usage count

        Returns:
            True if within limit, False if exceeded
        """
        if current_usage >= daily_limit:
            logger.warning(
                f"Embed config {embed_config_id} exceeded daily limit "
                f"({current_usage}/{daily_limit})"
            )
            return False

        return True


embed_service = EmbedService()
