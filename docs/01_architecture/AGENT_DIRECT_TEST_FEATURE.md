# Agent Direct Test Feature — Architecture (Pipecat WebSocket)

**Status:** Implemented via `voice-ws` + session JWT  
**Related:** [voice-ws README](../../voice-ws/README.md), [ADR_VOICE_WS_PIPECAT.md](ADR_VOICE_WS_PIPECAT.md)

## Phone call path (Twilio Media Streams)

```
Caller → Twilio → Webhook → TwiML Stream → voice-ws /twilio → Agent
```

1. User dials the agent's Twilio number
2. Twilio POSTs to `/api/v1/voice/twilio/incoming`
3. Backend returns TwiML `<Connect><Stream url="wss://…/twilio?token=JWT"/>`
4. Twilio opens a Media Stream WebSocket to `voice-ws`
5. `voice-ws` verifies JWT, loads agent preset, starts Pipecat session

See **[Twilio call flow](twilio_call_flow.md)** for full sequence diagrams.

## Browser test call path

```
Dashboard → Backend test-token → Pipecat client → voice-ws /ws → Agent
```

1. User clicks **Test Call** on an agent in the dashboard
2. Frontend calls backend for a short-lived voice session token
3. Backend returns `{ token, wsUrl, sessionId }` (`VOICE_WS_PUBLIC_URL` + JWT)
4. Frontend connects with `@pipecat-ai/client-js` + `@pipecat-ai/websocket-transport`
5. `voice-ws` verifies JWT and runs the same agent session as phone calls

## API contract (test token)

**Endpoint:** `POST /api/v1/voice/agents/{agent_id}/test-token`

**Response:**

```json
{
  "token": "<voice_ws_session JWT>",
  "wsUrl": "ws://localhost:7860/ws",
  "sessionId": "<uuid>"
}
```

## Key files

| File | Role |
|------|------|
| `shared/voice_agents/voice_session_service.py` | Create/verify session JWT |
| `backend/src/voice_agents/voice_routes.py` | Test token + Twilio webhooks |
| `voice-ws/src/main.py` | `/ws` and `/twilio` WebSocket endpoints |
| `voice-ws/src/session_setup.py` | Agent load, preset, tools, MCP |
| `frontend/src/lib/pipecat-voice-client.ts` | Browser Pipecat client |

## Environment

- `JWT_SECRET_KEY` — shared by backend and `voice-ws`
- `VOICE_WS_PUBLIC_URL` — browser WebSocket base (backend embeds in `wsUrl`)
- `VOICE_WS_TWILIO_URL` — public `wss://` base for Twilio (phone only)
- `GEMINI_API_KEY` — platform fallback for realtime presets

## Tests

- `backend/tests/voice_agents/test_voice_routes_pipecat.py` — test token + Twilio TwiML
- `voice-ws/tests/` — WebSocket session and tool runtime tests

**Historical note:** An earlier design used LiveKit rooms and `@pipecat-ai/client-js` in the browser. That path was removed; git history retains the old implementation.
