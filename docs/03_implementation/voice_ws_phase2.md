# Voice WebSocket Phase 2 — Twilio Media Streams

**Branch:** `feature/dump-livekit-use-websockets-or-pipecat`  
**ADR:** [ADR_VOICE_WS_PIPECAT.md](../01_architecture/ADR_VOICE_WS_PIPECAT.md)  
**Depends on:** [Phase 1](voice_ws_phase1.md)

## What shipped

| Area | Change |
|------|--------|
| Backend `POST /api/v1/voice/twilio/incoming` | When `VOICE_TRANSPORT=pipecat`, returns `<Connect><Stream url="wss://…/twilio?token=JWT"/>` instead of LiveKit SIP |
| `voice-ws` | New `WS /twilio` endpoint using Pipecat `parse_telephony_websocket` + `TwilioFrameSerializer` + shared Gemini pipeline |
| Settings | `VOICE_WS_TWILIO_URL` — public `wss://` base Twilio can reach (ngrok / tunnel) |
| LiveKit path | Unchanged when `VOICE_TRANSPORT=livekit` (SIP dial); SIP username/password now from env |

## How to test (local phone call)

Twilio’s cloud must reach your laptop’s `voice-ws`. Use a tunnel:

```bash
# Example: ngrok HTTP tunnel to voice-ws
ngrok http 7860
# Copy the https host → convert to wss, e.g. wss://abc123.ngrok-free.app
```

1. In `.env`:
   - `VOICE_TRANSPORT=pipecat`
   - `VOICE_WS_PUBLIC_URL=ws://localhost:7860` (browser test calls)
   - `VOICE_WS_TWILIO_URL=wss://<your-ngrok-host>` (**required** for phone; localhost is rejected)
   - `JWT_SECRET_KEY` shared by backend + voice-ws
   - `GEMINI_API_KEY`
   - `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` (optional but enables auto hang-up)
2. Restart backend (and voice-ws if needed): `./start.sh restart dev`
3. Point the Twilio number’s **A Call Comes In** webhook at:
   `https://<public-backend>/api/v1/voice/twilio/incoming`  
   (For local backend, tunnel port 8000 as well, or use a deployed backend that points `VOICE_WS_TWILIO_URL` at your voice-ws tunnel.)
4. Ensure the agent has that Twilio number assigned.
5. Call the number — you should hear the Gemini greeting over Media Streams.

Health: `curl http://localhost:7860/health`

## Rollback to LiveKit SIP

```bash
# .env
VOICE_TRANSPORT=livekit
LIVEKIT_SIP_DOMAIN=<your-sip-domain>
# optional:
# LIVEKIT_SIP_USERNAME=...
# LIVEKIT_SIP_PASSWORD=...
docker compose -f docker-compose.dev.yml --profile livekit up -d worker-dev
```

## Not in Phase 2

- Tools, MCP, skills on the Pipecat path (Phase 3)
- Pipeline STT→LLM→TTS (Phase 3)
- Persisted call recording (tee hook only)
