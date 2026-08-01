"""
Unit tests for LiveKitService.create_agent_dispatch.

Explicit agent dispatch is required for browser test calls — Cloud automatic
dispatch rules alone do not reliably start the worker.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.voice_agents.livekit_service import LiveKitService


@pytest.mark.asyncio
class TestLiveKitServiceAgentDispatch:
    """create_agent_dispatch calls the LiveKit Agent Dispatch API."""

    async def test_create_agent_dispatch_calls_livekit_api(self):
        service = LiveKitService()
        service.api_key = "key"
        service.api_secret = "secret"
        service.url = "wss://example.livekit.cloud"

        mock_dispatch = MagicMock()
        mock_dispatch.id = "AD_test"

        mock_lkapi = MagicMock()
        mock_lkapi.agent_dispatch.create_dispatch = AsyncMock(return_value=mock_dispatch)
        mock_lkapi.aclose = AsyncMock()

        with patch.object(service, "get_api_client", return_value=mock_lkapi):
            result = await service.create_agent_dispatch(room_name="test_room_abc")

        assert result.id == "AD_test"
        mock_lkapi.agent_dispatch.create_dispatch.assert_awaited_once()
        req = mock_lkapi.agent_dispatch.create_dispatch.call_args.args[0]
        assert req.room == "test_room_abc"
        assert req.agent_name == "voice-agent"
        mock_lkapi.aclose.assert_awaited_once()
