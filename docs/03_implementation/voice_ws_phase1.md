# Voice WebSocket Phase 1 — Implementation notes

**Branch:** `feature/dump-livekit-use-websockets-or-pipecat`  
**ADR:** [ADR_VOICE_WS_PIPECAT.md](../01_architecture/ADR_VOICE_WS_PIPECAT.md)

## What shipped

| Area | Change |
|------|--------|
| `voice-ws/` | New Pipecat + FastAPI container (`/health`, `/ws`) |
| `shared/.../voice_session_service.py` | Session JWT create/verify |
| Backend `test-token` | Returns `{ token, wsUrl, sessionId }` for Pipecat |
| Frontend `use-test-call` | Pipecat WebSocket client (`@pipecat-ai/client-js`) |
| `docker-compose.dev.yml` | `voice-ws-dev` on `:7860` |

## How to test

1. Ensure the selected root environment file has:
   - `VOICE_WS_PUBLIC_URL=ws://localhost:7860`
   - `JWT_SECRET_KEY` (same value backend + voice-ws use)
   - `GEMINI_API_KEY`
2. Start stack: `./start.sh start dev` (or build/start `voice-ws-dev`)
3. Open `http://localhost:3000`, log in, open an agent → **Test Call**
4. Allow microphone; agent should greet and respond over WebSocket

Health check: `curl http://localhost:7860/health`

## Call status and teardown

The voice worker creates an `initiated` call-log row for an admitted session
and finalizes it as `completed`, with duration and end time, in the session
teardown path. Browser call clients must retain the Pipecat client as soon as
it is created, before the WebSocket handshake completes. This lets Hang Up
close a call that is ended immediately after connection and allows the worker
to run its finalization path; late connection results from an already-cancelled
attempt are discarded and disconnected.

## Not in Phase 1

- Phone / Twilio Media Streams → see [Phase 2](voice_ws_phase2.md)
- Tools, MCP, skills on the Pipecat path (Phase 3)
- Pipeline STT→LLM→TTS (Phase 3)
- Persisted call recording (tee hook only)

**Note:** LiveKit and the legacy `voice-ws/` package were removed after Phases 1–3; Pipecat WebSocket is the only voice transport.
