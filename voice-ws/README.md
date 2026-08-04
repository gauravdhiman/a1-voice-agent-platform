# voice-ws — Pipecat WebSocket voice worker

Active call path for **browser test calls**, **embed**, **public org page**, and
**Twilio Media Streams** phone calls, using Pipecat. Agent presets select either
**Gemini Realtime** or a modular Deepgram → OpenAI/Cerebras/OpenRouter →
Cartesia/Fish pipeline (direct providers only).

The legacy LiveKit `worker/` package remains in the repo for reference; it is not
started in default dev/prod compose.

## Architecture

```mermaid
sequenceDiagram
  participant Phone as Twilio caller
  participant BE as Backend
  participant WS as voice-ws
  participant G as Gemini Realtime

  Phone->>BE: POST /api/v1/voice/twilio/incoming
  BE-->>Phone: TwiML Connect Stream + JWT
  Phone->>WS: WS /twilio?token=...
  WS->>WS: Verify JWT, parse Twilio start, load agent
  WS->>G: Gemini Live session
  Phone->>WS: μ-law audio (Media Streams)
  WS->>Phone: Agent audio (Media Streams)
```

Browser test calls use `WS /ws` with protobuf frames (see Phase 1 notes).
Pipeline presets use `BrowserWebSocketFrameSerializer` (`src/serialization/`)
because the JS `@pipecat-ai/websocket-transport` client only decodes **audio**
and **message** protobuf kinds — STT/LLM text, transcription, and interruption
frames are dropped (including protobuf field 5, which the JS decoder ignores and
surfaces as `Unknown frame kind`). TTS audio subclasses are normalized before send.
Realtime Gemini is unchanged.

## Local run (Docker)

```bash
# From repo root (starts backend, frontend, voice-ws-dev, …)
./start.sh start dev

# Or just the voice worker
docker compose -f docker-compose.dev.yml up -d voice-ws-dev
curl http://localhost:7860/health
```

## Env

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET_KEY` | Must match backend (session JWT) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Agent/org/prompt loading |
| `GEMINI_API_KEY` | Platform Gemini key fallback |
| `DEEPGRAM_API_KEY` / `OPENAI_API_KEY` / `CARTESIA_API_KEY` / `CEREBRAS_API_KEY` / `OPENROUTER_API_KEY` / `FISH_API_KEY` | Pipeline provider key fallbacks |
| `AGENT_DEFAULT_TIMEZONE` | Prompt datetime section |
| `VOICE_RECORDING_TEE` | `true` to log tee activity (no storage yet) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Optional; enables Media Streams auto hang-up |

Backend (not this container) also needs `VOICE_WS_TWILIO_URL=wss://…` for phone
calls so Twilio can reach `/twilio`.

## Phases

1. **Done:** Web test call + Gemini Realtime (`/ws`)
2. **Done:** Twilio Media Streams (phone) → `/twilio`
3. **Done:** STT→LLM→TTS pipeline + shared tools, MCP, and skills

## Recording (future)

`src/recording.py` defines a pass-through tee in the pipeline so bidirectional
audio capture can be added later without reshaping the graph.
