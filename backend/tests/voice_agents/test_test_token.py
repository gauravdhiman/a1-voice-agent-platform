"""
Tests for test token endpoint.
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
        _routes_mod = sys.modules['src.voice_agents.routes']
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

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.livekit_service") as mock_livekit:
                mock_livekit.generate_test_token = Mock(
                    return_value=("test_token", "wss://livekit.example.com", "test_agent_123")
                )
                mock_livekit.create_room = AsyncMock()
                mock_livekit.create_agent_dispatch = AsyncMock()

                result = await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                assert result.token == "test_token"
                assert result.serverUrl == "wss://livekit.example.com"
                assert result.roomName == "test_agent_123"

    @pytest.mark.asyncio
    async def test_get_test_token_pre_creates_room_and_dispatches_agent(self):
        """Test call must create the room AND explicitly dispatch the worker.

        Creating the room alone is not enough — LiveKit Cloud automatic dispatch
        rules are unreliable for web test rooms, so the worker never receives a
        job and the agent stays silent. Explicit agent_dispatch.create_dispatch
        after room creation reliably starts the worker (verified against LiveKit
        Cloud: room-only create → no job; create + dispatch → job received).
        """
        from src.voice_agents.routes import get_test_token
        import sys
        _routes_mod = sys.modules['src.voice_agents.routes']
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

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.livekit_service") as mock_livekit:
                mock_livekit.generate_test_token = Mock(
                    return_value=("test_token", "wss://livekit.example.com", "test_agent_123")
                )
                mock_livekit.create_room = AsyncMock()
                mock_livekit.create_agent_dispatch = AsyncMock()

                await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                mock_livekit.create_room.assert_awaited_once_with(room_name="test_agent_123")
                mock_livekit.create_agent_dispatch.assert_awaited_once_with(
                    room_name="test_agent_123",
                    agent_name="voice-agent",
                )

    @pytest.mark.asyncio
    async def test_get_test_token_pre_create_room_failure_is_non_fatal(self):
        """If room pre-creation fails, the token is still returned (best-effort).

        A LiveKit API hiccup during create_room must not block the test call — the
        caller still gets a token and can connect (implicit room creation remains
        a fallback). The failure is logged, not raised.
        """
        from src.voice_agents.routes import get_test_token
        import sys
        _routes_mod = sys.modules['src.voice_agents.routes']
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

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.livekit_service") as mock_livekit:
                mock_livekit.generate_test_token = Mock(
                    return_value=("test_token", "wss://livekit.example.com", "test_agent_123")
                )
                mock_livekit.create_room = AsyncMock(side_effect=RuntimeError("boom"))
                mock_livekit.create_agent_dispatch = AsyncMock()

                result = await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

                # Token still returned despite create_room failure.
                assert result.token == "test_token"
                assert result.roomName == "test_agent_123"
                # Dispatch must not run if room creation failed.
                mock_livekit.create_agent_dispatch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_test_token_agent_not_found(self):
        """Test test token when agent doesn't exist."""
        from src.voice_agents.routes import get_test_token
        import sys
        _routes_mod = sys.modules['src.voice_agents.routes']
        from fastapi import HTTPException

        test_agent_id = UUID("00000000-0000-0000-0000-000000000001")
        test_user_id = UUID("00000000-0000-0000-0000-000000000003")

        mock_user_profile = Mock()
        mock_user_profile.has_role = Mock(return_value=True)

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
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
        _routes_mod = sys.modules['src.voice_agents.routes']
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

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with pytest.raises(HTTPException) as exc_info:
                await get_test_token(
                    agent_id=test_agent_id,
                    user_data=(test_user_id, mock_user_profile),
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_test_token_allows_inactive_agent(self):
        """Test that inactive agents are allowed to generate test tokens.

        Browser-based testing via LiveKit doesn't require the agent to be
        active (active status only gates inbound phone calls, not test calls).
        Without LiveKit configured, this returns 503 — same as active agents.
        """
        from src.voice_agents.routes import get_test_token
        import sys
        _routes_mod = sys.modules['src.voice_agents.routes']
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

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.livekit_service") as mock_livekit:
                # Simulate LiveKit not configured
                mock_livekit.generate_test_token = Mock(return_value=(None, None, None))

                # Inactive agents proceed to LiveKit (not blocked by is_active check).
                with pytest.raises(HTTPException) as exc_info:
                    await get_test_token(
                        agent_id=test_agent_id,
                        user_data=(test_user_id, mock_user_profile),
                    )

                assert exc_info.value.status_code == 503
                assert "LiveKit" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_test_token_livekit_not_configured(self):
        """Test test token when LiveKit is not configured."""
        from src.voice_agents.routes import get_test_token
        import sys
        _routes_mod = sys.modules['src.voice_agents.routes']
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

        with patch.object(_routes_mod.settings, "voice_transport", "livekit"), patch("src.voice_agents.routes.voice_agent_service") as mock_voice_service:
            mock_voice_service.get_agent_by_id = AsyncMock(return_value=(agent, None))

            with patch("src.voice_agents.routes.livekit_service") as mock_livekit:
                mock_livekit.generate_test_token = Mock(
                    return_value=(None, None, None)
                )

                with pytest.raises(HTTPException) as exc_info:
                    await get_test_token(
                        agent_id=test_agent_id,
                        user_data=(test_user_id, mock_user_profile),
                    )

                assert exc_info.value.status_code == 503


class TestLiveKitService:
    """Test cases for LiveKit service."""

    def test_generate_test_token(self):
        """Test generating a test token."""
        from shared.voice_agents.livekit_service import LiveKitService
        from unittest.mock import patch

        service = LiveKitService()
        service.api_key = "test_key"
        service.api_secret = "test_secret"
        service.url = "wss://test.livekit.cloud"

        with patch.object(service, "generate_token") as mock_generate_token:
            mock_generate_token.return_value = "test_jwt_token"

            token, server_url, room_name = service.generate_test_token(
                agent_id="agent-123",
                user_id="user-456",
            )

            assert token == "test_jwt_token"
            assert server_url == "wss://test.livekit.cloud"
            assert room_name.startswith("test_agent-123_")

    def test_generate_test_token_not_configured(self):
        """Test generating test token when LiveKit is not configured."""
        from shared.voice_agents.livekit_service import LiveKitService

        service = LiveKitService()
        service.api_key = None
        service.api_secret = None
        service.url = None

        token, server_url, room_name = service.generate_test_token(
            agent_id="agent-123",
            user_id="user-456",
        )

        assert token is None
        assert server_url is None
        assert room_name is None
