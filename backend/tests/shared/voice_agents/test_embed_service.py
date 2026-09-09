"""
Tests for embed service.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone


class TestEmbedService:
    """Test cases for embed service."""

    def test_validate_domain_no_restrictions(self):
        """Test domain validation when no restrictions are set."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.validate_domain(None, "https://any-domain.com")
        assert result is True

        result = embed_service.validate_domain([], "https://any-domain.com")
        assert result is True

    def test_validate_domain_exact_match(self):
        """Test domain validation with exact match."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.validate_domain(
            ["example.com", "other.com"],
            "https://example.com"
        )
        assert result is True

    def test_validate_domain_subdomain_match(self):
        """Test domain validation with subdomain match."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.validate_domain(
            ["example.com"],
            "https://app.example.com"
        )
        assert result is True

        result = embed_service.validate_domain(
            ["example.com"],
            "https://www.example.com"
        )
        assert result is True

    def test_validate_domain_no_match(self):
        """Test domain validation when domain is not in allowed list."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.validate_domain(
            ["allowed.com", "example.com"],
            "https://unauthorized.com"
        )
        assert result is False

    def test_validate_domain_missing_request_domain(self):
        """Test domain validation when request has no domain."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.validate_domain(
            ["example.com"],
            None
        )
        assert result is False

        result = embed_service.validate_domain(
            ["example.com"],
            ""
        )
        assert result is False

    def test_normalize_domain(self):
        """Test domain normalization."""
        from shared.voice_agents.embed_service import embed_service

        assert embed_service._normalize_domain("https://Example.com") == "example.com"
        assert embed_service._normalize_domain("https://www.Example.com/path") == "example.com"
        assert embed_service._normalize_domain("http://example.com:8080") == "example.com"
        assert embed_service._normalize_domain("WWW.EXAMPLE.COM") == "example.com"
        assert embed_service._normalize_domain("example.com/") == "example.com"
        assert embed_service._normalize_domain("app.example.com") == "app.example.com"

    def test_invalid_domains_are_rejected(self):
        """Malformed browser origins must not satisfy an allowlist."""
        from shared.voice_agents.embed_service import embed_service

        assert embed_service.validate_domain(["example.com"], "not a domain") is False
        assert embed_service.validate_domain(["https://[bad"], "example.com") is False

    def test_check_rate_limit_within_limit(self):
        """Test rate limit check when within limit."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.check_rate_limit(
            embed_config_id="test-config-id",
            daily_limit=100,
            current_usage=50
        )
        assert result is True

        result = embed_service.check_rate_limit(
            embed_config_id="test-config-id",
            daily_limit=100,
            current_usage=99
        )
        assert result is True

    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit is exceeded."""
        from shared.voice_agents.embed_service import embed_service

        result = embed_service.check_rate_limit(
            embed_config_id="test-config-id",
            daily_limit=100,
            current_usage=100
        )
        assert result is False

        result = embed_service.check_rate_limit(
            embed_config_id="test-config-id",
            daily_limit=10,
            current_usage=15
        )
        assert result is False

    def test_generate_embed_token(self):
        """Test embed token generation returns Pipecat session credentials."""
        from shared.voice_agents.embed_service import embed_service

        with patch(
            "shared.voice_agents.embed_service.voice_session_service"
        ) as mock_sessions:
            mock_sessions.create_session_token.return_value = (
                "voice.jwt.token",
                "sess-embed-123",
            )

            embed_token, voice_token, ws_url, session_id = (
                embed_service.generate_embed_token(
                    agent_id="test-agent-id",
                    embed_config_id="test-config-id",
                    domain="https://example.com",
                    ip_address="127.0.0.1",
                    source_url="https://www.example.com/support?customer=private",
                )
            )

            assert embed_token is not None
            assert voice_token == "voice.jwt.token"
            assert ws_url.endswith("/ws")
            assert session_id == "sess-embed-123"
            call_kwargs = mock_sessions.create_session_token.call_args.kwargs
            assert call_kwargs["source_type"] == "web_embed"
            assert call_kwargs["source_url"] == "https://example.com/support"
            assert call_kwargs["source_domain"] == "example.com"
            mock_sessions.create_session_token.assert_called_once()

    def test_validate_embed_token(self):
        """Test embed token validation."""
        from shared.voice_agents.embed_service import embed_service
        import jwt

        payload = {
            "sub": "config-id",
            "agent_id": "agent-id",
            "room_name": "test-room",
            "type": "embed_access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, embed_service.jwt_secret, algorithm="HS256")

        result = embed_service.validate_embed_token(token)
        assert result["sub"] == "config-id"
        assert result["agent_id"] == "agent-id"
        assert result["type"] == "embed_access"

    def test_validate_embed_token_expired(self):
        """Test embed token validation with expired token."""
        from shared.voice_agents.embed_service import embed_service, EmbedValidationError
        import jwt

        payload = {
            "sub": "config-id",
            "agent_id": "agent-id",
            "type": "embed_access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, embed_service.jwt_secret, algorithm="HS256")

        with pytest.raises(EmbedValidationError) as exc_info:
            embed_service.validate_embed_token(token)

        assert "expired" in str(exc_info.value).lower()

    def test_validate_embed_token_invalid_type(self):
        """Test embed token validation with invalid token type."""
        from shared.voice_agents.embed_service import embed_service, EmbedValidationError
        import jwt

        payload = {
            "sub": "config-id",
            "agent_id": "agent-id",
            "type": "invalid_type",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, embed_service.jwt_secret, algorithm="HS256")

        with pytest.raises(EmbedValidationError) as exc_info:
            embed_service.validate_embed_token(token)

        assert "invalid token type" in str(exc_info.value).lower()
