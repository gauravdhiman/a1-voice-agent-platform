"""FastAPI entrypoint for the Pipecat WebSocket voice worker.

Exposes:
- ``GET /health`` — liveness
- ``WS /ws?token=...`` — browser audio session (Phase 1 test call)
- ``WS /twilio?token=...`` — Twilio Media Streams (Phase 2 phone)
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pipecat.runner.utils import parse_telephony_websocket

from uuid import UUID

from shared.billing.voice_session_entitlement import (
    VoiceSessionEntitlementError,
    assert_voice_session_allowed,
)
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.voice_session_service import VoiceSessionService

from src.bot import run_bot
from src.twilio_session import build_twilio_serializer, resolve_session_token

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("voice-ws")
tracer = trace.get_tracer(__name__)

try:
    from shared.config.opentelemetry import (
        instrument_fastapi,
        setup_manual_opentelemetry,
    )

    setup_manual_opentelemetry(app_name="voice-ws")
except Exception as exc:  # pragma: no cover - optional in minimal dev images
    logger.warning("OpenTelemetry setup skipped: %s", exc)
    instrument_fastapi = None  # type: ignore[misc, assignment]

app = FastAPI(
    title="24x7 AI Voice WebSocket Worker",
    description="Pipecat + Gemini Realtime voice sessions (web + Twilio)",
    version="0.2.0",
)

if instrument_fastapi is not None:
    try:
        instrument_fastapi(app)
    except Exception as exc:  # pragma: no cover
        logger.warning("FastAPI OpenTelemetry instrumentation skipped: %s", exc)

session_service = VoiceSessionService()


async def _precheck_voice_session(claims) -> None:
    """Enforce concurrent and credit entitlements before accepting a session."""
    agent, agent_error = await voice_agent_service.get_agent_by_id(UUID(claims.agent_id))
    if agent_error or agent is None or not agent.organization_id:
        return
    await assert_voice_session_allowed(agent.organization_id)


@app.get("/health")
async def health() -> JSONResponse:
    """Liveness probe for Docker / Cloud Run style checks."""
    return JSONResponse({"status": "healthy", "service": "voice-ws"})


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="voice_ws_session JWT from backend"),
) -> None:
    """Accept a browser WebSocket and run the Pipecat Gemini Live bot.

    The client (``@pipecat-ai/websocket-transport``) connects with a short-lived
    session JWT issued by ``POST /api/v1/agents/{id}/test-token``.
    """
    claims = session_service.verify_session_token(token)
    if claims is None:
        logger.warning("Rejecting WebSocket: invalid or expired session token")
        await websocket.close(code=4401, reason="Invalid session token")
        return

    try:
        await _precheck_voice_session(claims)
    except VoiceSessionEntitlementError as exc:
        logger.warning(
            "Rejecting WebSocket session_id=%s code=%s: %s",
            claims.session_id,
            exc.code,
            exc.message,
        )
        await websocket.close(code=4403, reason=exc.message[:120])
        return

    current_span = trace.get_current_span()
    current_span.set_attribute("voice.session_id", claims.session_id)
    current_span.set_attribute("voice.agent_id", claims.agent_id)
    current_span.set_attribute("voice.purpose", claims.purpose)

    await websocket.accept()
    logger.info(
        "WebSocket accepted session_id=%s agent_id=%s",
        claims.session_id,
        claims.agent_id,
    )
    try:
        await run_bot(websocket, claims)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected session_id=%s", claims.session_id)
    except Exception:
        logger.exception("voice-ws session failed session_id=%s", claims.session_id)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:  # noqa: BLE001
            pass


@app.websocket("/twilio")
async def twilio_websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(
        None, description="Optional voice_ws_session JWT (query may be stripped)"
    ),
) -> None:
    """Accept a Twilio Media Streams WebSocket and run the Gemini Live bot.

    Auth token may arrive as ``?token=`` on the Stream URL and/or as a Twilio
    Stream ``<Parameter name="token">`` (preferred fallback). We accept the
    socket first so the Twilio start handshake can be parsed, then verify.
    """
    # Accept before auth so Twilio can send the start event with customParameters.
    # Unauthenticated sockets are closed immediately after handshake parse.
    await websocket.accept()
    logger.info(
        "Twilio WebSocket accepted (pending auth) query_token_present=%s",
        bool(token and token.strip()),
    )
    try:
        transport_type, call_data = await parse_telephony_websocket(websocket)
        if transport_type != "twilio":
            raise ValueError(f"Expected twilio transport, got {transport_type!r}")

        session_token = resolve_session_token(
            query_token=token,
            call_data=call_data,
        )
        if not session_token:
            logger.warning(
                "Rejecting Twilio WebSocket: no session token in query or Stream params"
            )
            await websocket.close(code=4401, reason="Missing session token")
            return

        claims = session_service.verify_session_token(session_token)
        if claims is None:
            logger.warning(
                "Rejecting Twilio WebSocket: invalid or expired session token"
            )
            await websocket.close(code=4401, reason="Invalid session token")
            return

        try:
            await _precheck_voice_session(claims)
        except VoiceSessionEntitlementError as exc:
            logger.warning(
                "Rejecting Twilio WebSocket session_id=%s code=%s: %s",
                claims.session_id,
                exc.code,
                exc.message,
            )
            await websocket.close(code=4403, reason=exc.message[:120])
            return

        serializer = build_twilio_serializer(call_data)
        stream_id = getattr(call_data, "stream_id", None)
        call_id = getattr(call_data, "call_id", None)
        logger.info(
            "Twilio stream ready session_id=%s agent_id=%s stream_id=%s call_id=%s",
            claims.session_id,
            claims.agent_id,
            stream_id,
            call_id,
        )
        await run_bot(websocket, claims, serializer=serializer)
    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected before/during session")
    except Exception:
        logger.exception("Twilio voice-ws session failed")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:  # noqa: BLE001
            pass
