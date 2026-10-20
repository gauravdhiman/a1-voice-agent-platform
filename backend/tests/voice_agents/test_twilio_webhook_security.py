"""Security and routing tests for Twilio phone-number webhooks."""

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from fastapi import HTTPException
from src.voice_agents.voice_routes import (
    _validated_form,
    handle_twilio_incoming,
    handle_twilio_status_callback,
)
from starlette.requests import Request
from twilio.request_validator import RequestValidator


def _request(form: dict[str, str], *, signature: str = "signature"):
    request = MagicMock()
    request.form = AsyncMock(return_value=form)
    request.headers = {"X-Twilio-Signature": signature}
    request.url = "https://api.example.com/api/v1/voice/twilio/incoming"
    request.query_params = {}
    return request


@pytest.mark.asyncio
async def test_signed_bounded_urlencoded_body_is_parsed_and_verified():
    """Real streamed form parsing preserves Twilio's signature contract."""
    params = {"CallSid": "CA123", "To": "+14155550100"}
    url = "https://api.example.test/api/v1/voice/twilio/incoming"
    signature = RequestValidator("test-token").compute_signature(url, params)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "server": ("api.example.test", 443),
            "path": "/api/v1/voice/twilio/incoming",
            "query_string": b"",
            "headers": [
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"x-twilio-signature", signature.encode()),
            ],
        },
        AsyncMock(
            return_value={
                "type": "http.request",
                "body": urlencode(params).encode(),
                "more_body": False,
            }
        ),
    )
    with patch("src.voice_agents.voice_routes.settings") as settings:
        settings.twilio_webhook_signature_validation_enabled = True
        settings.twilio_auth_token = "test-token"
        assert await _validated_form(request) == params


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
async def test_unsigned_twilio_payload_is_not_parsed():
    """Missing signatures are denied before any potentially costly parsing."""
    request = _request({}, signature="")
    with patch("src.voice_agents.voice_routes.settings") as settings:
        settings.twilio_webhook_signature_validation_enabled = True
        settings.twilio_auth_token = "test-token"
        with pytest.raises(HTTPException) as exc:
            await _validated_form(request)
    assert exc.value.status_code == 403
    request.form.assert_not_awaited()


@pytest.mark.asyncio
async def test_multipart_is_rejected_even_with_a_signature():
    """Voice callbacks never need file uploads or multipart parsing."""
    request = _request({})
    request.headers["content-type"] = "multipart/form-data; boundary=test"
    with patch("src.voice_agents.voice_routes.settings") as settings:
        settings.twilio_webhook_signature_validation_enabled = True
        settings.twilio_auth_token = "test-token"
        with pytest.raises(HTTPException) as exc:
            await _validated_form(request)
    assert exc.value.status_code == 415
    request.form.assert_not_awaited()


@pytest.mark.asyncio
async def test_chunked_twilio_body_has_a_hard_limit():
    """A forged/absent Content-Length cannot bypass the stream byte bound."""
    from starlette.requests import Request

    receive = AsyncMock(return_value={"type": "http.request", "body": b"x" * 65537})
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"x-twilio-signature", b"test"),
            ],
        },
        receive,
    )
    with patch("src.voice_agents.voice_routes.settings") as settings:
        settings.twilio_webhook_signature_validation_enabled = True
        settings.twilio_auth_token = "test-token"
        with pytest.raises(HTTPException) as exc:
            await _validated_form(request)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_incoming_call_routes_from_phone_numbers_source_of_truth():
    """Inbound routing resolves the agent through the phone_numbers relation."""
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
