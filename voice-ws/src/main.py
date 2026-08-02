"""FastAPI entrypoint for the Pipecat WebSocket voice worker.

Exposes:
- ``GET /health`` — liveness
- ``WS /ws?token=...`` — browser audio session (Phase 1 test call)
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from shared.voice_agents.voice_session_service import VoiceSessionService

from src.bot import run_bot

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("voice-ws")

app = FastAPI(
    title="CogniEnts Voice WebSocket Worker",
    description="Pipecat + Gemini Realtime voice sessions (Phase 1)",
    version="0.1.0",
)

session_service = VoiceSessionService()


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
