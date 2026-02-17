# Agent Direct Test Feature - Implementation Plan

## Overview

This document outlines the implementation plan for adding a "Test Agent" feature that allows users to directly test voice agents from the Agent configuration page via a browser-based WebRTC call, bypassing the Twilio phone number flow.

## Current Architecture

### Existing Phone Call Flow
```
Caller → Twilio → Webhook → TwiML → LiveKit (SIP) → Worker → Agent
```

1. Caller dials Twilio phone number
2. Twilio hits webhook at `/api/v1/voice/twilio/incoming`
3. Backend returns TwiML with SIP URI to bridge to LiveKit
4. Twilio connects to LiveKit via SIP
5. LiveKit dispatches job to Worker
6. Worker joins room, loads agent/tools, starts conversation

### Web-Based Test Flow
```
User clicks "Test Agent" → Backend generates LiveKit token → Browser connects to LiveKit → Worker joins → Agent responds
```

## Implementation

### Backend Changes

#### 1.1 API Endpoint for Test Session Token
**File:** `backend/src/voice_agents/routes.py`

```python
@router.post("/agents/{agent_id}/test-token")
async def get_test_token(agent_id: UUID) -> TestTokenResponse:
```

**Request:** `agent_id` (UUID)  
**Response:**
```json
{
  "token": "eyJhbGc...",
  "serverUrl": "wss://livekit.example.com",
  "roomName": "test_agent_123_abc"
}
```

#### 1.2 LiveKit Service
**File:** `shared/voice_agents/livekit_service.py`

- Updated to use settings from config
- Added `generate_test_token()` method that creates a room named `test_{agent_id}_{random}`

#### 1.3 Settings
**File:** `shared/config/settings.py`

- Added LiveKit settings (`livekit_url`, `livekit_api_key`, `livekit_api_secret`)

### Frontend Changes

#### 2.1 Dependencies
- Added `livekit-client` package

#### 2.2 Environment Variables
- Added `NEXT_PUBLIC_LIVEKIT_URL` to `.env.local.example`

#### 2.3 Test Call Hook
**File:** `frontend/src/hooks/use-test-call.ts`

Custom hook managing the test call lifecycle:
- Connect to LiveKit room using token
- Handle audio (microphone input, speaker output)
- Connection state management
- Cleanup on unmount

#### 2.4 Test Call Modal Component
**File:** `frontend/src/components/agents/test-call-modal.tsx`

Modal component with:
- Test Agent button on detail page
- Connection status UI
- Mute/Unmute controls
- End call button

### Worker Changes

#### 3.1 Room Name Detection
**File:** `worker/src/worker.py`

Updated to handle test room name format:
- Test room: `test_{agent_id}_{random}`
- Phone room: `call_{phone_number}_{random}`

Worker fetches agent by ID for test rooms instead of phone number.

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/src/voice_agents/routes.py` | Modify | Add `POST /agents/{agent_id}/test-token` endpoint |
| `shared/voice_agents/livekit_service.py` | Modify | Add `generate_test_token()` method |
| `shared/config/settings.py` | Modify | Add LiveKit settings |
| `worker/src/worker.py` | Modify | Handle test room name format |
| `frontend/package.json` | Modify | Add `livekit-client` dependency |
| `frontend/.env.local.example` | Modify | Add `NEXT_PUBLIC_LIVEKIT_URL` |
| `frontend/src/services/agent-service.ts` | Modify | Add `getTestToken()` API method |
| `frontend/src/hooks/use-test-call.ts` | New | Custom hook for test call |
| `frontend/src/components/agents/test-call-modal.tsx` | New | Modal component for test UI |
| `frontend/src/app/(dashboard)/agents/[agentId]/page.tsx` | Modify | Add Test Agent button |

## Tests

### Backend Tests
**File:** `backend/tests/voice_agents/test_test_token.py`

- `test_get_test_token_success` - Test successful token generation
- `test_get_test_token_agent_not_found` - Test when agent doesn't exist
- `test_get_test_token_permission_denied` - Test permission checks
- `test_get_test_token_inactive_agent` - Test inactive agent rejection
- `test_get_test_token_livekit_not_configured` - Test when LiveKit is not configured
- `test_generate_test_token` - Test LiveKit service token generation
- `test_generate_test_token_not_configured` - Test service when not configured

### Frontend Tests
**File:** `frontend/tests/services/test-agent-service.test.ts`

- `getTestToken returns test token data` - Test token retrieval

## Security Considerations

1. **Token Expiration:** Test tokens expire after 10 minutes
2. **Room Cleanup:** Test rooms auto-delete after inactivity (empty_timeout=300)
3. **Access Control:** Only users with org access can test agents
4. **Active Agent Check:** Cannot test inactive agents
