"""
Tests for embed routes.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID


class TestEmbedRoutes:
    """Test cases for embed routes."""

    @pytest.mark.asyncio
    async def test_get_agent_info_success(self):
        """Test successful retrieval of agent info for embed."""
        from src.voice_agents.embed_routes import get_agent_info
        from shared.voice_agents.models import VoiceAgent
        from fastapi import Request

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = {"origin": "https://example.com"}

        with patch("src.voice_agents.embed_routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_supabase = Mock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
                data=[{
                    "id": str(UUID("00000000-0000-0000-0000-000000000003")),
                    "agent_id": str(test_agent_id),
                    "is_active": True,
                    "allowed_domains": None,
                }]
            )
            mock_voice_service.supabase = mock_supabase

            result = await get_agent_info(agent_id=test_agent_id, request=mock_request)

            assert result.id == test_agent_id
            assert result.name == "Test Agent"
            assert result.is_active is True

    @pytest.mark.asyncio
    async def test_get_agent_info_agent_not_found(self):
        """Test agent info when agent doesn't exist."""
        from src.voice_agents.embed_routes import get_agent_info
        from fastapi import HTTPException, Request

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        with patch("src.voice_agents.embed_routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(
                return_value=(None, "Agent not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_info(agent_id=test_agent_id, request=mock_request)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agent_info_agent_inactive(self):
        """Test agent info when agent is inactive."""
        from src.voice_agents.embed_routes import get_agent_info
        from shared.voice_agents.models import VoiceAgent
        from fastapi import HTTPException, Request

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test Agent",
            phone_number="+1234567890",
            is_active=False,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        with patch("src.voice_agents.embed_routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_info(agent_id=test_agent_id, request=mock_request)

            assert exc_info.value.status_code == 400
            assert "not active" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_agent_info_domain_not_authorized(self):
        """Test agent info when domain is not authorized."""
        from src.voice_agents.embed_routes import get_agent_info
        from shared.voice_agents.models import VoiceAgent
        from fastapi import HTTPException, Request

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = {"origin": "https://unauthorized.com"}

        with patch("src.voice_agents.embed_routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_supabase = Mock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
                data=[{
                    "id": str(UUID("00000000-0000-0000-0000-000000000003")),
                    "agent_id": str(test_agent_id),
                    "is_active": True,
                    "allowed_domains": ["allowed.com", "example.com"],
                }]
            )
            mock_voice_service.supabase = mock_supabase

            with patch("src.voice_agents.embed_routes.embed_service") as mock_embed:
                mock_embed.validate_domain.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    await get_agent_info(agent_id=test_agent_id, request=mock_request)

                assert exc_info.value.status_code == 403
                assert "not authorized" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_generate_public_embed_token_success(self):
        """Test successful generation of public embed token."""
        from src.voice_agents.embed_routes import generate_public_embed_token
        from shared.voice_agents.models import VoiceAgent
        from fastapi import Request

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_config_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = {"origin": "https://example.com", "user-agent": "TestAgent"}
        mock_request.client = Mock(host="127.0.0.1")

        with patch("src.voice_agents.embed_routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_supabase = Mock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
                data=[{
                    "id": str(test_config_id),
                    "agent_id": str(test_agent_id),
                    "is_active": True,
                    "allowed_domains": None,
                    "daily_call_limit": 100,
                }],
                count=0,
            )
            mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock()
            mock_voice_service.supabase = mock_supabase

            with patch("src.voice_agents.embed_routes.embed_service") as mock_embed:
                mock_embed.validate_domain.return_value = True
                mock_embed.check_rate_limit.return_value = True
                mock_embed.generate_embed_token.return_value = (
                    "embed_token",
                    "livekit_token",
                    "wss://livekit.example.com",
                    "embed_room_123",
                )

                result = await generate_public_embed_token(
                    agent_id=test_agent_id, request=mock_request
                )

                assert result.livekit_token == "livekit_token"
                assert result.server_url == "wss://livekit.example.com"
                assert result.room_name == "embed_room_123"

    @pytest.mark.asyncio
    async def test_generate_public_embed_token_rate_limited(self):
        """Test embed token generation when rate limited."""
        from src.voice_agents.embed_routes import generate_public_embed_token
        from shared.voice_agents.models import VoiceAgent
        from fastapi import HTTPException, Request

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_config_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=UUID("00000000-0000-0000-0000-000000000002"),
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = {"origin": "https://example.com"}
        mock_request.client = Mock(host="127.0.0.1")

        with patch("src.voice_agents.embed_routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_supabase = Mock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
                data=[{
                    "id": str(test_config_id),
                    "agent_id": str(test_agent_id),
                    "is_active": True,
                    "allowed_domains": None,
                    "daily_call_limit": 10,
                }],
                count=10,
            )
            mock_voice_service.supabase = mock_supabase

            with patch("src.voice_agents.embed_routes.embed_service") as mock_embed:
                mock_embed.validate_domain.return_value = True
                mock_embed.check_rate_limit.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    await generate_public_embed_token(
                        agent_id=test_agent_id, request=mock_request
                    )

                assert exc_info.value.status_code == 429
                assert "limit exceeded" in exc_info.value.detail.lower()
