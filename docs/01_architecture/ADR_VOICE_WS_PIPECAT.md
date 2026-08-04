# ADR: Replace LiveKit with Pipecat WebSocket voice transport

**Status:** Accepted — LiveKit removed; Pipecat WebSocket is the only transport  
**Date:** 2026-08-02 (updated 2026-08-03)  
**Branch:** `feature/dump-livekit-use-websockets-or-pipecat`

## Context

LiveKit (WebRTC rooms + SIP) is heavier than needed for 1:1 agent audio calls.
We want a lighter stack so a small always-on VM can host the voice process without
LiveKit Cloud / SIP trunk complexity.

## Decision

1. **`voice-ws/`** (Pipecat + FastAPI WebSocket) is the sole voice runtime.
   The legacy LiveKit **`worker/`** package was deleted from the repo (git history
   retains it).
2. All call surfaces (dashboard test call, embed, public org page, Twilio phone)
   use Pipecat WebSocket sessions. Backend returns `{ token, wsUrl, sessionId }`.
3. Deliver in three phases (all complete on voice-ws):
   - **Phase 1:** Web test call + Gemini Realtime over WebSocket
   - **Phase 2:** Twilio Media Streams → same worker (phone)
   - **Phase 3:** STT→LLM→TTS pipeline + tools/MCP/skills
4. Design sessions so bidirectional audio can later be tee’d for **call
   recording** without rewriting the transport.

## Consequences

- Browser uses `@pipecat-ai/client-js` + `@pipecat-ai/websocket-transport`.
- Backend issues short-lived `voice_ws_session` JWTs with `{ token, wsUrl, sessionId }`.
- LiveKit Inference presets were removed; pipeline presets use direct providers only.
- No LiveKit build/deploy path remains in compose or Render blueprint.

## Related

- Implementation notes: `docs/03_implementation/voice_ws_phase1.md`,
  `docs/03_implementation/voice_ws_phase2.md`,
  `docs/03_implementation/voice_ws_phase3.md`
- Parked LiveKit cloud deploy: `docs/05_operations/DEPLOY_BRANCH_PARKED.md` (on
  deploy branch only)
