# voice-ws — Pipecat WebSocket voice worker

Active call path for **browser test calls**, **embed**, **public org page**, and
**Twilio Media Streams** phone calls, using Pipecat. Agent presets select either
**Google Gemini or OpenAI realtime** speech, or a modular Deepgram →
OpenAI/Cerebras/OpenRouter → Cartesia/Fish pipeline (direct providers only).

The legacy LiveKit **`worker/`** package was removed from the repo; git history
retains it for reference only.

The Python voice runtime pins `pipecat-ai` to `1.11.0` for Gemini 3.8 Live
support. The browser packages
(`@pipecat-ai/client-js` and `@pipecat-ai/websocket-transport`) are versioned
independently and are unchanged by this runtime upgrade. Upgrade the Python
runtime only with the voice regression suite, recording checks, and live
staging call gates described in the repository testing and release guides.

At call teardown, this worker rounds connected duration up to whole minutes and
settles the complete charge through the atomic billing RPC. An admitted call is
allowed to finish even if the final settlement creates a temporary negative
balance; the backend then blocks new calls until credits are restored.

When Pipecat reports a provider or pipeline failure, the worker keeps the first
safe failure classification on the related `call_logs` row and finalizes its
status as `failed`. The authenticated Calls UI shows the classification and a
short remediation hint. Provider exceptions themselves stay in the runtime
logging/telemetry boundary. The backend migration
`20260902000001_add_call_failure_details` adds the nullable fields used for this
signal; a late Twilio status callback cannot overwrite a recorded failure with
`completed`.

## Architecture

```mermaid
sequenceDiagram
  participant Phone as Twilio caller
  participant BE as Backend
  participant WS as voice-ws
  participant G as Google/OpenAI Realtime

  Phone->>BE: POST /api/v1/voice/twilio/incoming
  BE-->>Phone: TwiML Connect Stream + JWT
  Phone->>WS: WS /twilio?token=...
  WS->>WS: Verify JWT, parse Twilio start, load agent
  WS->>G: Provider realtime session
  Phone->>WS: μ-law audio (Media Streams)
  WS->>Phone: Agent audio (Media Streams)
```

Browser test calls use `WS /ws` with protobuf frames (see Phase 1 notes).
Pipeline presets use `BrowserWebSocketFrameSerializer` (`src/serialization/`)
because the JS `@pipecat-ai/websocket-transport` client only decodes **audio**
and **message** protobuf kinds — STT/LLM text, transcription, and interruption
frames are dropped (including protobuf field 5, which the JS decoder ignores and
surfaces as `Unknown frame kind`). TTS audio subclasses are normalized before send.
Google realtime remains backward-compatible. OpenAI realtime presets select
either the standard `gpt-realtime-2.1` Pipecat adapter or the custom `gpt-live-1`
WebSocket adapter with Responses delegation and server-side tool execution.

## Local run (Docker)

```bash
# From repo root (starts backend, frontend, voice-ws-dev, …)
./start.sh start dev

# Or just the voice worker
docker compose -f docker-compose.dev.yml up -d voice-ws-dev
curl http://localhost:7860/health
```

## Env

| Variable                                                                                             | Purpose                                                                                                                                                                     |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `JWT_SECRET_KEY`                                                                                     | Must match backend (session JWT)                                                                                                                                            |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`                                                              | Agent/org/prompt loading                                                                                                                                                    |
| `GEMINI_API_KEY`                                                                                     | Platform Gemini realtime key fallback                                                                                                                                       |
| `OPENAI_API_KEY`                                                                                     | Platform OpenAI realtime and pipeline LLM key fallback                                                                                                                      |
| `DEEPGRAM_API_KEY` / `CARTESIA_API_KEY` / `CEREBRAS_API_KEY` / `OPENROUTER_API_KEY` / `FISH_API_KEY` | Pipeline provider key fallbacks                                                                                                                                             |
| `AGENT_DEFAULT_TIMEZONE`                                                                             | Prompt datetime section                                                                                                                                                     |
| `RESEND_API_KEY` / `RESEND_FROM_EMAIL` / `RESEND_FROM_NAME`                                          | Platform-owned notification sender configuration; the native `Resend_email` follow-up tool uses the organization's encrypted Resend key and attachment sender configuration |
| `VOICE_RECORDING_ENABLED`                                                                            | Platform gate for audio persistence (default `false`); the agent must also opt in                                                                                           |
| `RECORDING_STORAGE_BACKEND`                                                                          | `local` for development or `r2` for staging/production                                                                                                                      |
| `RECORDING_ENCRYPTION_MODE`                                                                          | `provider_managed` (customer-managed is reserved)                                                                                                                           |
| `RECORDING_R2_*`                                                                                     | Bucket-scoped R2 endpoint, bucket, credentials, and URL TTL                                                                                                                 |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`                                                           | Optional; enables Media Streams auto hang-up                                                                                                                                |

Backend (not this container) also needs `VOICE_WS_TWILIO_URL=wss://…` for phone
calls so Twilio can reach `/twilio`.

## Phases

1. **Done:** Web test call + Gemini Realtime (`/ws`)
2. **Done:** Twilio Media Streams (phone) → `/twilio`
3. **Done:** STT→LLM→TTS pipeline + shared tools, MCP, and skills
4. **Done:** Provider-aware realtime presets with OpenAI GPT-Live and Realtime adapters

## Recording

`src/recording.py` captures caller and agent PCM with transport-adjacent
pass-through taps, renders caller-left/agent-right stereo at the lowest native
track sample rate, uploads it on teardown, and records status/retention
metadata in `call_artifacts`. It retains genuine timing gaps observed at those
boundaries but does not allow downstream model or pipeline delays to inflate
the caller track. Recording is best-effort and never masks call billing. Org
admins and platform admins can listen from the Call Log UI through the
authenticated backend playback endpoint.

Native tool contracts live in `shared/voice_agents/tools/implementations/` and
are assembled here with a trusted per-call `ToolContext`. See the [Resend
Agent Email Tool](../docs/03_implementation/resend_email_agent_tool.md) for
route configuration, provider acceptance semantics, and error handling.

## Operational observability

See the [observability operator guide](../docs/05_operations/observability.md) for
local dashboards, call correlation, privacy, alert rules and production rollout.
The isolated worktree launcher provisions the monitoring stack. Backend and voice
SDK exports are bounded and asynchronous; browser API correlation needs no public
collector credentials.
