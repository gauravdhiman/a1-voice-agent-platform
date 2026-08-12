"""Security and routing tests for Twilio phone-number webhooks."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.voice_agents.voice_routes import (
    _validated_form,
    handle_twilio_incoming,
    handle_twilio_status_callback,
)


def _request(form: dict[str, str], *, signature: str = "signature"):
    request = MagicMock()
    request.form = AsyncMock(return_value=form)
    request.headers = {"X-Twilio-Signature": signature}
    request.url = "https://api.example.com/api/v1/voice/twilio/incoming"
    request.query_params = {}
    return request


@pytest.mark.asyncio
async def test_invalid_twilio_signature_is_rejected():
    """Unsigned or invalid callbacks cannot enter call routing."""
    request = _request({"To": "+14155550100"})
    with patch("src.voice_agents.voice_routes.settings") as settings, patch(
        "src.voice_agents.voice_routes.RequestValidator"
    ) as validator_cls:
        settings.twilio_webhook_signature_validation_enabled = True
        settings.twilio_auth_token = "auth-token"
        validator_cls.return_value.validate.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await _validated_form(request)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_incoming_call_routes_from_phone_numbers_source_of_truth():
    """Inbound routing resolves the agent through phone_numbers, not agent.phone_number."""
    request = _request(
        {"To": "+14155550100", "From": "+14155550199", "CallSid": "CA123"},
    )
    agent = MagicMock(id=uuid4(), organization_id=uuid4())
    with patch("src.voice_agents.voice_routes.settings") as settings, patch(
        "src.voice_agents.voice_routes.phone_number_service"
    ) as phone_service, patch(
        "src.voice_agents.voice_routes.voice_agent_service"
    ) as agent_service, patch(
        "src.voice_agents.voice_routes.resolve_twilio_stream_base_url",
        return_value="wss://voice.example.com",
    ), patch(
        "src.voice_agents.voice_routes.voice_session_service"
    ) as sessions, patch(
        "src.call_logs.service.call_log_service"
    ) as logs, patch(
        "src.voice_agents.voice_routes.assert_voice_session_allowed",
        new=AsyncMock(),
    ):
        settings.twilio_webhook_signature_validation_enabled = False
        phone_service.get_routable_agent_id = AsyncMock(return_value=(agent.id, None))
        agent_service.get_agent_by_id = AsyncMock(return_value=(agent, None))
        sessions.create_session_token.return_value = ("session.jwt", "session-1")
        logs.create_call_log = AsyncMock()

        response = await handle_twilio_incoming(request)

    assert response.status_code == 200
    phone_service.get_routable_agent_id.assert_awaited_once_with("+14155550100")
    agent_service.get_agent_by_id.assert_awaited_once_with(agent.id)
    agent_service.get_agent_by_phone.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_duration_does_not_fail_status_callback():
    """Twilio's non-numeric duration cannot turn a status callback into a 500."""
    request = _request(
        {
            "CallSid": "CA123",
            "CallStatus": "completed",
            "CallDuration": "not-a-number",
        }
    )
    with patch("src.voice_agents.voice_routes.settings") as settings, patch(
        "src.call_logs.service.call_log_service"
    ) as logs:
        settings.twilio_webhook_signature_validation_enabled = False
        logs.update_call_log_by_sid = AsyncMock(return_value=(MagicMock(), None))

        response = await handle_twilio_status_callback(request)

    assert response.status_code == 200
    update = logs.update_call_log_by_sid.call_args.args[1]
    assert update.duration == 0
