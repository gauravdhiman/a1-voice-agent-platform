# Voice WebSocket Phase 1 — Implementation notes

**Branch:** `feature/dump-livekit-use-websockets-or-pipecat`  
**ADR:** [ADR_VOICE_WS_PIPECAT.md](../01_architecture/ADR_VOICE_WS_PIPECAT.md)

## What shipped

| Area | Change |
|------|--------|
| `voice-ws/` | New Pipecat + FastAPI container (`/health`, `/ws`) |
| `shared/.../voice_session_service.py` | Session JWT create/verify |
| Backend `test-token` | Branches on `VOICE_TRANSPORT` |
| Frontend `use-test-call` | Pipecat WebSocket client (LiveKit kept as fallback) |
| `docker-compose.dev.yml` | `voice-ws-dev` on `:7860`; LiveKit `worker-dev` under profile `livekit` |

## How to test

1. Ensure `.env` has:
   - `VOICE_TRANSPORT=pipecat`
   - `VOICE_WS_PUBLIC_URL=ws://localhost:7860`
   - `JWT_SECRET_KEY` (same value backend + voice-ws use)
   - `GEMINI_API_KEY`
2. Start stack: `./start.sh start dev` (or build/start `voice-ws-dev`)
3. Open `http://localhost:3000`, log in, open an agent → **Test Call**
4. Allow microphone; agent should greet and respond over WebSocket

Health check: `curl http://localhost:7860/health`

## Rollback to LiveKit

```bash
# .env
VOICE_TRANSPORT=livekit
docker compose -f docker-compose.dev.yml --profile livekit up -d worker-dev
```

## Not in Phase 1

- Phone / Twilio Media Streams → see [Phase 2](voice_ws_phase2.md)
- Tools, MCP, skills on the Pipecat path (Phase 3)
- Pipeline STT→LLM→TTS (Phase 3)
- Persisted call recording (tee hook only)
