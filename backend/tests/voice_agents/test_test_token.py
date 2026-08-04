"""
Tests for test token endpoint (Pipecat WebSocket transport).
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID


class TestTestTokenEndpoint:
    """Test cases for test token endpoint."""

    @pytest.mark.asyncio
    async def test_get_test_token_success(self):
        """Test successful test token generation."""
        from src.voice_agents.routes import get_test_token
        import sys

        _routes_mod = sys.modules["src.voice_agents.routes"]
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            persona="Support Specialist",
            tone="Professional",
            mission="Help customers",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch.object(
            _routes_mod.settings, "voice_ws_public_url", "ws://localhost:7860"
        ), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch(
                "src.voice_agents.routes.voice_session_service"
            ) as mock_sessions:
                mock_sessions.create_session_token.return_value = (
                    "test_token",
                    "sess-123",
                )

                result = await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                assert result.transport == "pipecat"
                assert result.token == "test_token"
                assert result.wsUrl == "ws://localhost:7860/ws"
                assert result.sessionId == "sess-123"

    @pytest.mark.asyncio
    async def test_get_test_token_agent_not_found(self):
        """Test test token when agent doesn't exist."""
        from src.voice_agents.routes import get_test_token
        import sys

        _routes_mod = sys.modules["src.voice_agents.routes"]
        from fastapi import HTTPException

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(
                return_value=(None, "Agent not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_test_token_permission_denied(self):
        """Test test token without proper permissions."""
        from src.voice_agents.routes import get_test_token
        import sys

        _routes_mod = sys.modules["src.voice_agents.routes"]
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=False)
        mock_user_profile.has_permission = Mock(return_value=False)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_test_token_allows_inactive_agent(self):
        """Inactive agents may still bootstrap browser test calls."""
        from src.voice_agents.routes import get_test_token
        import sys

        _routes_mod = sys.modules["src.voice_agents.routes"]
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=False,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch.object(
            _routes_mod.settings, "voice_ws_public_url", "ws://localhost:7860"
        ), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch(
                "src.voice_agents.routes.voice_session_service"
            ) as mock_sessions:
                mock_sessions.create_session_token.side_effect = ValueError(
                    "JWT secret is not configured"
                )

                with pytest.raises(HTTPException) as exc_info:
                    await get_test_token(
                        agent_id=test_agent_id,
                        user_data=(test_user_id, mock_user_profile),
                    )

                assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_get_test_token_voice_session_not_configured(self):
        """Test test token when voice session JWT cannot be created."""
        from src.voice_agents.routes import get_test_token
        import sys

        _routes_mod = sys.modules["src.voice_agents.routes"]
        from fastapi import HTTPException
        from shared.voice_agents.models import VoiceAgent

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_org_id = UUID("00000000-0000-0000-0000-000000000002")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        agent = VoiceAgent(
            id=test_agent_id,
            organization_id=test_org_id,
            name="Test Agent",
            phone_number="+1234567890",
            is_active=True,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch(
                "src.voice_agents.routes.voice_session_service"
            ) as mock_sessions:
                mock_sessions.create_session_token.side_effect = ValueError(
                    "JWT secret is not configured"
                )

                with pytest.raises(HTTPException) as exc_info:
                    await get_test_token(
                        agent_id=test_agent_id,
                        user_data=(test_user_id, mock_user_profile),
                    )

                assert exc_info.value.status_code == 503
                assert "JWT_SECRET_KEY" in exc_info.value.detail
