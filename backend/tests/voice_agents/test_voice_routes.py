"""
Tests for voice routes (Twilio webhook handling — Pipecat Media Streams).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Response
from src.voice_agents.voice_routes import handle_twilio_incoming


@pytest.mark.asyncio
class TestVoiceRoutes:
    """Test cases for voice webhook routes (Pipecat transport)."""

    async def test_handle_twilio_incoming_agent_found(self):
        """Test successful Twilio incoming call returns Media Stream TwiML."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(
            return_value={
                "To": "+1234567890",
                "From": "+0987654321",
                "CallSid": "CA123456789",
            }
        )
        mock_request.query_params = {}

        agent_id = uuid4()
        org_id = uuid4()
        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.organization_id = org_id

        with patch(
            "src.voice_agents.voice_routes.phone_number_service"
        ) as mock_phone_service, patch(
            "src.voice_agents.voice_routes.voice_agent_service"
        ) as mock_service, patch(
            "src.voice_agents.voice_routes.settings"
        ) as mock_settings, patch(
            "src.voice_agents.voice_routes.voice_session_service"
        ) as mock_sessions, patch(
            "src.call_logs.service.call_log_service"
        ) as mock_logs:

            mock_settings.voice_ws_twilio_url = "wss://tunnel.example.com"
            mock_settings.voice_ws_public_url = "ws://localhost:7860"
            mock_settings.twilio_webhook_signature_validation_enabled = False
            mock_phone_service.get_routable_agent_id = AsyncMock(
                return_value=(agent_id, None)
            )
            mock_service.get_agent_by_id = AsyncMock(return_value=(mock_agent, None))
            mock_sessions.create_session_token.return_value = ("sess.jwt", "sess-1")
            mock_logs.create_call_log = AsyncMock()

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            assert response.media_type == "application/xml"
            content = response.body.decode()
            assert "<Stream" in content
            assert "wss://tunnel.example.com/twilio?token=sess.jwt" in content
            assert "<Sip" not in content

    async def test_handle_twilio_incoming_agent_not_found(self):
        """Test Twilio incoming call when agent not found."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(
            return_value={
                "To": "+1234567890",
                "From": "+0987654321",
                "CallSid": "CA123456789",
            }
        )
        mock_request.query_params = {}

        with patch(
            "src.voice_agents.voice_routes.phone_number_service"
        ) as mock_phone_service, patch(
            "src.voice_agents.voice_routes.settings"
        ) as mock_settings:
            mock_settings.twilio_webhook_signature_validation_enabled = False
            mock_phone_service.get_routable_agent_id = AsyncMock(
                return_value=(None, "Agent not found")
            )

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            assert response.media_type == "application/xml"
            content = response.body.decode()
            assert "this number is not assigned to an active agent" in content.lower()

    async def test_handle_twilio_incoming_missing_public_url(self):
        """Test Twilio incoming call when voice-ws URL is not configured."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(
            return_value={
                "To": "+1234567890",
                "From": "+0987654321",
                "CallSid": "CA123456789",
            }
        )
        mock_request.query_params = {}

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.organization_id = uuid4()

        with patch(
            "src.voice_agents.voice_routes.phone_number_service"
        ) as mock_phone_service, patch(
            "src.voice_agents.voice_routes.voice_agent_service"
        ) as mock_service, patch(
            "src.voice_agents.voice_routes.settings"
        ) as mock_settings, patch(
            "src.call_logs.service.call_log_service"
        ) as mock_logs:

            mock_settings.voice_ws_twilio_url = ""
            mock_settings.voice_ws_public_url = ""
            mock_settings.twilio_webhook_signature_validation_enabled = False
            mock_phone_service.get_routable_agent_id = AsyncMock(
                return_value=(mock_agent.id, None)
            )
            mock_service.get_agent_by_id = AsyncMock(return_value=(mock_agent, None))
            mock_logs.create_call_log = AsyncMock()

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            assert response.media_type == "application/xml"
            content = response.body.decode()
            assert "configuration error" in content.lower()
