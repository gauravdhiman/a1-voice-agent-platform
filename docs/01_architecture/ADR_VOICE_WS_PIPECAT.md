# ADR: Replace LiveKit with Pipecat WebSocket voice transport

**Status:** Accepted (Phase 2 complete; Phase 3 pending)  
**Date:** 2026-08-02  
**Branch:** `feature/dump-livekit-use-websockets-or-pipecat`

## Context

LiveKit (WebRTC rooms + SIP) is heavier than needed for 1:1 agent audio calls.
We want a lighter stack so a small always-on VM can host the voice process without
LiveKit Cloud / SIP trunk complexity.

## Decision

1. Add a new container **`voice-ws/`** (Pipecat + FastAPI WebSocket). Do **not**
   modify or delete the existing LiveKit `worker/`.
2. Route calls via `VOICE_TRANSPORT=pipecat|livekit` (default `pipecat` on this
   feature branch).
3. Deliver in three phases:
   - **Phase 1:** Web test call + Gemini Realtime over WebSocket
   - **Phase 2:** Twilio Media Streams → same worker (phone)
   - **Phase 3:** STT→LLM→TTS pipeline + tools/MCP/skills
4. Design sessions so bidirectional audio can later be tee’d for **call
   recording** without rewriting the transport.

## Consequences

- Browser uses `@pipecat-ai/client-js` + `@pipecat-ai/websocket-transport`.
- Backend issues short-lived `voice_ws_session` JWTs instead of LiveKit room
  tokens when transport is `pipecat`.
- LiveKit worker remains available for rollback (`VOICE_TRANSPORT=livekit`).

## Related

- Implementation notes: `docs/03_implementation/voice_ws_phase1.md`,
  `docs/03_implementation/voice_ws_phase2.md`
- Parked LiveKit cloud deploy: `docs/05_operations/DEPLOY_BRANCH_PARKED.md` (on
  deploy branch only)
