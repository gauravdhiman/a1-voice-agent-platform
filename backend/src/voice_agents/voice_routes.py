"""Twilio voice webhooks for inbound calls and status callbacks.

Inbound calls return TwiML that opens a Media Stream WebSocket to ``voice-ws``
(``/twilio``) using a short-lived ``voice_ws_session`` JWT.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote, urlparse

from fastapi import APIRouter, HTTPException, Request, Response, status
from src.phone_numbers.service import phone_number_service
from src.voice_agents.public_voice_messages import get_public_voice_session_error
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    assert_voice_session_allowed,
    is_demo_agent,
    reserve_demo_call_if_needed,
)
from shared.config.settings import settings
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.voice_session_service import voice_session_service

logger = logging.getLogger(__name__)
voice_router = APIRouter(prefix="/api/v1/voice", tags=["Voice Webhooks"])

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def resolve_twilio_stream_base_url() -> str:
    """Resolve the public wss:// base URL for Twilio Media Streams.

    Prefers ``VOICE_WS_TWILIO_URL``, otherwise falls back to
    ``VOICE_WS_PUBLIC_URL``. ``ws://`` / ``http(s)://`` schemes are normalized
    to ``wss://`` because Twilio only connects over TLS WebSockets.

    Returns:
        Base URL without a trailing slash (e.g. ``wss://tunnel.example.com``),
        or an empty string when neither setting is configured.
    """
    raw = (
        (settings.voice_ws_twilio_url or settings.voice_ws_public_url or "")
        .strip()
        .rstrip("/")
    )
    if not raw:
        return ""

    if raw.startswith("wss://"):
        return raw
    if raw.startswith("ws://"):
        return "wss://" + raw[len("ws://") :]
    if raw.startswith("https://"):
        return "wss://" + raw[len("https://") :]
    if raw.startswith("http://"):
        return "wss://" + raw[len("http://") :]
    # Bare host / path — assume wss
    return f"wss://{raw}"


def is_twilio_reachable_stream_base(base_url: str) -> bool:
    """Return True when ``base_url`` looks reachable by Twilio's cloud.

    Twilio cannot dial loopback hosts. Local ``wss://localhost`` values are
    rejected so operators set ``VOICE_WS_TWILIO_URL`` (ngrok / public tunnel).

    Args:
        base_url: Normalized ``wss://`` base from
            :func:`resolve_twilio_stream_base_url`.

    Returns:
        False for empty URLs or localhost / loopback hosts; True otherwise.
    """
    if not base_url:
        return False
    host = (urlparse(base_url).hostname or "").lower()
    if not host or host in _LOCAL_HOSTS:
        return False
    return True


def build_pipecat_stream_twiml(
    *,
    stream_url: str,
    agent_id: str,
    session_token: str,
    from_number: Optional[str],
    to_number: Optional[str],
) -> str:
    """Build TwiML that connects the call to a Pipecat Media Stream.

    Args:
        stream_url: Full ``wss://.../twilio?token=...`` URL (query is a
            best-effort auth channel).
        agent_id: Agent UUID string mirrored as a Stream parameter.
        session_token: ``voice_ws_session`` JWT also sent as a Stream
            ``<Parameter name="token">`` so auth survives when Twilio omits
            query strings on the Media Streams WebSocket URL.
        from_number: Caller E.164 (optional Stream custom parameter).
        to_number: Called E.164 (optional Stream custom parameter).

    Returns:
        XML string for Twilio ``application/xml`` response.
    """
    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=stream_url)
    stream.parameter(name="token", value=session_token)
    stream.parameter(name="agent_id", value=agent_id)
    if from_number:
        stream.parameter(name="from_number", value=str(from_number))
    if to_number:
        stream.parameter(name="to_number", value=str(to_number))
    connect.append(stream)
    response.append(connect)
    return str(response)


def _xml_response(content: str) -> Response:
    """Wrap TwiML XML in a FastAPI Response."""
    return Response(content=content, media_type="application/xml")


def _say_response(message: str) -> Response:
    """Return a spoken error / info TwiML response."""
    response = VoiceResponse()
    response.say(message)
    return _xml_response(str(response))


async def _handle_pipecat_incoming(
    *,
    agent,
    from_number: Optional[str],
    to_number: Optional[str],
    call_sid: Optional[str],
) -> Response:
    """Issue a voice-ws session JWT and return Media Streams TwiML."""
    base = resolve_twilio_stream_base_url()
    if not is_twilio_reachable_stream_base(base):
        logger.error(
            "Pipecat phone transport needs a public VOICE_WS_TWILIO_URL "
            "(got base=%r). Twilio cannot reach localhost.",
            base,
        )
        return _say_response(
            "Internal configuration error. Voice stream URL is not public."
        )

    reservation = None
    try:
        reservation = await reserve_demo_call_if_needed(agent)
        await assert_voice_session_allowed(
            agent.organization_id,
            current_call_sid=call_sid,
            agent_is_demo=is_demo_agent(agent),
        )
    except VoiceSessionEntitlementError as exc:
        _public_code, public_message = get_public_voice_session_error(exc.code)
        logger.info(
            "Twilio voice session denied agent_id=%s call_sid=%s code=%s",
            agent.id,
            call_sid,
            exc.code,
        )
        return _say_response(public_message)

    try:
        token, session_id = voice_session_service.create_session_token(
            agent_id=str(agent.id),
            user_id=str(from_number or "anonymous"),
            purpose="phone",
            call_sid=call_sid,
            session_id=(reservation.session_id if reservation else None),
            demo_reservation_id=(reservation.reservation_id if reservation else None),
            demo_max_call_duration_seconds=(
                reservation.max_call_duration_seconds if reservation else None
            ),
        )
    except ValueError as exc:
        logger.error("Failed to create voice session token: %s", exc)
        return _say_response("Internal configuration error. Session secret missing.")

    # JWT is base64url + dots; keep those unescaped for Twilio Stream URLs.
    stream_url = f"{base}/twilio?token={quote(token, safe='.-_')}"
    twiml = build_pipecat_stream_twiml(
        stream_url=stream_url,
        agent_id=str(agent.id),
        session_token=token,
        from_number=from_number,
        to_number=to_number,
    )
    logger.info(
        "Bridging Twilio call %s to voice-ws Media Streams session_id=%s url_host=%s",
        call_sid,
        session_id,
        urlparse(base).hostname,
    )
    return _xml_response(twiml)


async def _validated_form(request: Request) -> dict[str, str]:
    """Read a Twilio form and reject requests with an invalid signature."""
    form_data = await request.form()
    params = {str(key): str(value) for key, value in form_data.items()}
    if not getattr(settings, "twilio_webhook_signature_validation_enabled", True):
        return params

    auth_token = getattr(settings, "twilio_auth_token", None)
    signature = request.headers.get("X-Twilio-Signature")
    if not auth_token or not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio webhook signature",
        )
    validator = RequestValidator(auth_token)
    if not validator.validate(str(request.url), params, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio webhook signature",
        )
    return params


@voice_router.post("/twilio/incoming")
async def handle_twilio_incoming(request: Request):
    """
    Handle incoming calls from Twilio.
    This endpoint should be configured as the "A Call Comes In" webhook in Twilio.
    """
    from src.call_logs.models import CallLogCreate
    from src.call_logs.service import call_log_service

    form_data = await _validated_form(request)
    to_number = form_data.get("To")
    from_number = form_data.get("From")
    call_sid = form_data.get("CallSid")

    logger.info(
        "Incoming call from %s to %s (CallSid: %s)",
        from_number,
        to_number,
        call_sid,
    )

    if not to_number:
        return _say_response("We could not identify the called number.")

    connection_token = request.query_params.get("connection_token")
    if connection_token:
        if not to_number or not await phone_number_service.verify_customer_number(
            to_number, connection_token
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number verification failed",
            )

    agent_id, error = await phone_number_service.get_routable_agent_id(to_number)
    agent = None
    if agent_id:
        agent, error = await voice_agent_service.get_agent_by_id(agent_id)

    if error or not agent:
        logger.warning("No agent found for phone number %s", to_number)
        return _say_response(
            "I'm sorry, this number is not assigned to an active agent."
        )

    if call_sid:
        try:
            await call_log_service.create_call_log(
                CallLogCreate(
                    call_sid=call_sid,
                    organization_id=agent.organization_id,
                    agent_id=agent.id,
                    caller_number=from_number,
                    called_number=to_number,
                    status="initiated",
                    started_at=datetime.now(timezone.utc),
                )
            )
        except Exception as log_err:  # noqa: BLE001 — never fail the call on logging
            logger.warning("Failed to create call log for %s: %s", call_sid, log_err)

    return await _handle_pipecat_incoming(
        agent=agent,
        from_number=from_number,
        to_number=to_number,
        call_sid=call_sid,
    )


@voice_router.post("/twilio/status")
async def handle_twilio_status_callback(request: Request):
    """
    Handle Twilio call status callbacks.
    Configure this as the "Call Status Changes" webhook URL in Twilio.
    Updates the call log with final duration and status.
    """
    from src.call_logs.models import CallLogUpdate
    from src.call_logs.service import call_log_service

    form_data = await _validated_form(request)
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus", "")
    call_duration = form_data.get("CallDuration", "0")

    connection_token = request.query_params.get("connection_token")
    if connection_token:
        to_number = form_data.get("To")
        if not to_number or not await phone_number_service.verify_customer_number(
            to_number, connection_token
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number verification failed",
            )

    logger.info(
        "Twilio status callback: CallSid=%s, Status=%s, Duration=%s",
        call_sid,
        call_status,
        call_duration,
    )

    if call_sid:
        status_map = {
            "completed": "completed",
            "busy": "busy",
            "failed": "failed",
            "no-answer": "no-answer",
            "canceled": "missed",
            "in-progress": "answered",
            "ringing": "ringing",
            "queued": "initiated",
        }
        internal_status = status_map.get(call_status, call_status)

        try:
            duration_seconds = max(0, int(call_duration or 0))
        except (TypeError, ValueError):
            duration_seconds = 0

        update_data = CallLogUpdate(
            status=internal_status,
            duration=duration_seconds,
            ended_at=(
                datetime.now(timezone.utc)
                if call_status
                in ("completed", "busy", "failed", "no-answer", "canceled")
                else None
            ),
        )

        _, err = await call_log_service.update_call_log_by_sid(call_sid, update_data)
        if err:
            logger.warning("Failed to update call log for %s: %s", call_sid, err)

    return Response(status_code=200)
