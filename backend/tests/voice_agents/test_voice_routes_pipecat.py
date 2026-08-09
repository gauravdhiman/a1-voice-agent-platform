"""Tests for Twilio inbound → Pipecat Media Streams TwiML (Phase 2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Response

from src.voice_agents.voice_routes import (
    build_pipecat_stream_twiml,
    handle_twilio_incoming,
    is_twilio_reachable_stream_base,
    resolve_twilio_stream_base_url,
)


class TestTwimlBuilders:
    """Unit tests for TwiML helpers (no FastAPI request needed)."""

    def test_build_pipecat_stream_twiml_contains_connect_stream(self) -> None:
        xml = build_pipecat_stream_twiml(
            stream_url="wss://example.com/twilio?token=abc.def",
            agent_id="agent-1",
            session_token="abc.def",
            from_number="+15551111111",
            to_number="+15552222222",
        )
        assert "<Connect>" in xml
        assert "<Stream" in xml
        assert "wss://example.com/twilio?token=abc.def" in xml
        assert 'name="agent_id"' in xml
        assert "agent-1" in xml
        # Token also as Stream Parameter — Twilio often delivers custom
        # parameters more reliably than query strings on Media Streams.
        assert 'name="token"' in xml
        assert "abc.def" in xml
        assert "<Sip" not in xml

    def test_resolve_twilio_stream_base_url_prefers_twilio_url(self) -> None:
        with patch("src.voice_agents.voice_routes.settings") as mock_settings:
            mock_settings.voice_ws_twilio_url = "wss://tunnel.example.com"
            mock_settings.voice_ws_public_url = "ws://localhost:7860"
            assert resolve_twilio_stream_base_url() == "wss://tunnel.example.com"

    def test_resolve_twilio_stream_base_url_upgrades_ws_to_wss(self) -> None:
        with patch("src.voice_agents.voice_routes.settings") as mock_settings:
            mock_settings.voice_ws_twilio_url = ""
            mock_settings.voice_ws_public_url = "ws://localhost:7860"
            assert resolve_twilio_stream_base_url() == "wss://localhost:7860"

    def test_localhost_stream_base_is_not_twilio_reachable(self) -> None:
        assert is_twilio_reachable_stream_base("wss://localhost:7860") is False
        assert is_twilio_reachable_stream_base("wss://tunnel.example.com") is True


@pytest.mark.asyncio
class TestTwilioIncomingPipecat:
    """Route-level tests for VOICE_TRANSPORT=pipecat."""

    async def test_pipecat_returns_media_stream_twiml(self) -> None:
        mock_request = MagicMock()
        mock_request.form = AsyncMock(
            return_value={
                "To": "+1234567890",
                "From": "+0987654321",
                "CallSid": "CA123456789",
            }
        )
        agent_id = uuid4()
        org_id = uuid4()
        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.organization_id = org_id
        mock_agent.phone_number = "+1234567890"

        with (
            patch("src.voice_agents.voice_routes.settings") as mock_settings,
            patch(
                "src.voice_agents.voice_routes.voice_agent_service"
            ) as mock_service,
            patch(
                "src.voice_agents.voice_routes.voice_session_service"
            ) as mock_sessions,
            patch("src.call_logs.service.call_log_service") as mock_logs,
        ):
            mock_settings.voice_ws_twilio_url = "wss://tunnel.example.com"
            mock_settings.voice_ws_public_url = "ws://localhost:7860"
            mock_service.get_agent_by_phone = AsyncMock(
                return_value=(mock_agent, None)
            )
            mock_sessions.create_session_token = MagicMock(
                return_value=("sess.jwt", "sess-1")
            )
            mock_logs.create_call_log = AsyncMock()

            response = await handle_twilio_incoming(mock_request)

        assert isinstance(response, Response)
        content = response.body.decode()
        assert "<Stream" in content
        assert "wss://tunnel.example.com/twilio?token=sess.jwt" in content
        assert "<Sip" not in content
        mock_sessions.create_session_token.assert_called_once()
        kwargs = mock_sessions.create_session_token.call_args.kwargs
        assert kwargs["purpose"] == "phone"
        assert kwargs["agent_id"] == str(agent_id)
        assert kwargs["call_sid"] == "CA123456789"

    async def test_pipecat_missing_twilio_url_returns_config_error(self) -> None:
        mock_request = MagicMock()
        mock_request.form = AsyncMock(
            return_value={
                "To": "+1234567890",
                "From": "+0987654321",
                "CallSid": "CA123",
            }
        )
        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.organization_id = uuid4()

        with (
            patch("src.voice_agents.voice_routes.settings") as mock_settings,
            patch(
                "src.voice_agents.voice_routes.voice_agent_service"
            ) as mock_service,
            patch("src.call_logs.service.call_log_service") as mock_logs,
        ):
            mock_settings.voice_ws_twilio_url = ""
            mock_settings.voice_ws_public_url = ""
            mock_service.get_agent_by_phone = AsyncMock(
                return_value=(mock_agent, None)
            )
            mock_logs.create_call_log = AsyncMock()

            response = await handle_twilio_incoming(mock_request)

        content = response.body.decode()
        assert "configuration error" in content.lower()
        assert "not public" in content.lower()

    async def test_pipecat_localhost_url_rejected(self) -> None:
        mock_request = MagicMock()
        mock_request.form = AsyncMock(
            return_value={
                "To": "+1234567890",
                "From": "+0987654321",
                "CallSid": "CA123",
            }
        )
        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.organization_id = uuid4()

        with (
            patch("src.voice_agents.voice_routes.settings") as mock_settings,
            patch(
                "src.voice_agents.voice_routes.voice_agent_service"
            ) as mock_service,
            patch("src.call_logs.service.call_log_service") as mock_logs,
        ):
            mock_settings.voice_ws_twilio_url = ""
            mock_settings.voice_ws_public_url = "ws://localhost:7860"
            mock_service.get_agent_by_phone = AsyncMock(
                return_value=(mock_agent, None)
            )
            mock_logs.create_call_log = AsyncMock()

            response = await handle_twilio_incoming(mock_request)

        content = response.body.decode()
        assert "not public" in content.lower()
