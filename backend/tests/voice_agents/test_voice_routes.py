"""
Tests for voice routes (Twilio webhook handling — LiveKit SIP path).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import Response

from src.voice_agents.voice_routes import handle_twilio_incoming


@pytest.mark.asyncio
class TestVoiceRoutes:
    """Test cases for voice webhook routes (VOICE_TRANSPORT=livekit)."""

    async def test_handle_twilio_incoming_agent_found(self):
        """Test successful Twilio incoming call with agent found."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(return_value={
            "To": "+1234567890",
            "From": "+0987654321",
            "CallSid": "CA123456789"
        })

        mock_agent = MagicMock()
        mock_agent.phone_number = "+1234567890"

        with patch('src.voice_agents.voice_routes.voice_agent_service') as mock_service, \
             patch('src.voice_agents.voice_routes.settings') as mock_settings, \
             patch.dict('os.environ', {'LIVEKIT_SIP_DOMAIN': 'sip.example.com'}):

            mock_settings.voice_transport = "livekit"
            mock_service.get_agent_by_phone = AsyncMock(return_value=(mock_agent, None))

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            assert response.media_type == "application/xml"
            content = response.body.decode()
            assert "sip:+1234567890@sip.example.com" in content

    async def test_handle_twilio_incoming_agent_not_found(self):
        """Test Twilio incoming call when agent not found."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(return_value={
            "To": "+1234567890",
            "From": "+0987654321",
            "CallSid": "CA123456789"
        })

        with patch('src.voice_agents.voice_routes.voice_agent_service') as mock_service:
            mock_service.get_agent_by_phone = AsyncMock(return_value=(None, "Agent not found"))

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            assert response.media_type == "application/xml"
            content = response.body.decode()
            assert "this number is not assigned to an active agent" in content.lower()

    async def test_handle_twilio_incoming_missing_sip_domain(self):
        """Test Twilio incoming call when SIP domain is not configured."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(return_value={
            "To": "+1234567890",
            "From": "+0987654321",
            "CallSid": "CA123456789"
        })

        mock_agent = MagicMock()
        mock_agent.phone_number = "+1234567890"

        with patch('src.voice_agents.voice_routes.voice_agent_service') as mock_service, \
             patch('src.voice_agents.voice_routes.settings') as mock_settings, \
             patch.dict('os.environ', {}, clear=True):

            mock_settings.voice_transport = "livekit"
            mock_service.get_agent_by_phone = AsyncMock(return_value=(mock_agent, None))

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            assert response.media_type == "application/xml"
            content = response.body.decode()
            assert "Internal configuration error" in content

    async def test_handle_twilio_incoming_sip_domain_with_sip_prefix(self):
        """Test Twilio incoming call when SIP domain includes sip: prefix."""
        mock_request = MagicMock()
        mock_request.form = AsyncMock(return_value={
            "To": "+1234567890",
            "From": "+0987654321",
            "CallSid": "CA123456789"
        })

        mock_agent = MagicMock()
        mock_agent.phone_number = "+1234567890"

        with patch('src.voice_agents.voice_routes.voice_agent_service') as mock_service, \
             patch('src.voice_agents.voice_routes.settings') as mock_settings, \
             patch.dict('os.environ', {'LIVEKIT_SIP_DOMAIN': 'sip:sip.example.com'}):

            mock_settings.voice_transport = "livekit"
            mock_service.get_agent_by_phone = AsyncMock(return_value=(mock_agent, None))

            response = await handle_twilio_incoming(mock_request)

            assert isinstance(response, Response)
            content = response.body.decode()
            assert "sip:+1234567890@sip.example.com" in content
