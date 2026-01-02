# AI Voice Agent Platform: Architectural Flow & Implementation Guide

This document provides a comprehensive walkthrough of how the platform works, from initial setup to a live AI agent handling a phone call and using tools.

## **1. High-Level Architecture**

The platform is built as a multi-tenant SaaS that bridges traditional telephony (Twilio) with modern AI (Gemini) and real-time communication (LiveKit).

```mermaid
graph TD
    subgraph "Frontend (Next.js)"
        UI[Dashboard UI]
        ToolConfig[Tool Configuration]
    end

    subgraph "Backend (FastAPI)"
        API[API Server]
        Auth[OAuth Handler]
        AgentSvc[Voice Agent Service]
        ToolSvc[Tool Service]
        VoiceRoutes[Voice Webhooks]
    end

    subgraph "Agent Worker (LiveKit Agents)"
        Worker[LiveKit Worker]
        Gemini[Gemini S2S Model]
        Executor[Agent Executor]
    end

    subgraph "External Services"
        Twilio[Twilio SIP]
        LK[LiveKit Cloud]
        Google[Google Calendar API]
        DB[(Supabase DB)]
    end

    UI --> API
    API --> DB
    ToolConfig --> Auth
    Twilio -- Incoming Call --> VoiceRoutes
    VoiceRoutes --> LK
    LK -- Job Dispatch --> Worker
    Worker --> Gemini
    Worker --> Executor
    Executor --> Google
```

---

## **2. The Flow: Step-by-Step**

### **Phase A: Tool Registration & Configuration**
Before an agent can do anything, tools must be defined in the code and configured by a business user.

1.  **Code Definition**: A developer creates a tool class (e.g., `GoogleCalendarTool`) inheriting from `BaseTool`. This class defines its `metadata` (name, description, config schema).
2.  **Registry**: The tool is registered in `registry.py` so the system knows it exists.
3.  **User Configuration**: 
    - The business user logs into the dashboard.
    - They see the available tools fetched via `tool_routes.py`.
    - For the **Google Calendar** tool, they click "Connect", which triggers an OAuth flow handled by `AuthService`.
    - The encrypted tokens are stored in the `agent_tools` table as `sensitive_config`.

### **Phase B: Incoming Call & Session Initialization**
This is where the "Real-time" magic happens.

```mermaid
sequenceDiagram
    participant U as User (Phone)
    participant T as Twilio
    participant B as Backend (FastAPI)
    participant L as LiveKit Cloud
    participant W as Worker (Gemini Agent)

    U->>T: Dials Agent Phone Number
    T->>B: POST /api/v1/voice/twilio/incoming
    Note over B: Look up Agent by phone number
    B->>B: Start Session (Snapshot Tools)
    B->>L: Create Room with Metadata (agent_id, session_id)
    B-->>T: SIP Dial Response (sip:room@lk.domain)
    T->>L: Connect via SIP
    L->>W: Dispatch Job (Room Created)
    W->>L: Connect to Room
```

**Key Classes/Methods:**
- `VoiceAgentService.get_agent_by_phone()`: Identifies which agent belongs to the dialed number.
- `SessionManager.start_session()`: Creates a "snapshot" of the agent's current tools. If you disable a tool *during* a call, the agent keeps using the snapshot until the call ends.
- `handle_twilio_incoming()`: Returns TwiML that tells Twilio to bridge the call into a LiveKit room via SIP.

### **Phase C: Agent Execution & Tool Usage**
The worker is now live and talking to the user.

```mermaid
sequenceDiagram
    participant W as Worker
    participant G as Gemini S2S
    participant E as Agent Executor
    participant API as External API (Google)

    W->>W: entrypoint(ctx)
    W->>W: Fetch Agent & Tools (from Snapshot)
    W->>W: Register FunctionContext (Tools -> LLM Functions)
    W->>G: Initialize RealtimeModel (Instructions + Tools)
    
    Note over G: User: "What's on my calendar?"
    
    G->>W: Call Tool: google_calendar(action='list_events')
    W->>E: run_tool("Google Calendar", action="list_events")
    E->>API: Execute Google API Call
    API-->>E: Return Events
    E-->>W: Tool Result
    W-->>G: Send Result to LLM
    
    Note over G: Gemini: "You have a meeting at 10 AM."
```

**Detailed Logic in `worker.py`:**
- **Dynamic Tool Binding**: We loop through `agent_tools` and use `@fnc_ctx.ai_callable` to turn our Python tools into functions the LLM understands.
- **Closure Capture**: We use a `create_tool_func` helper to ensure that when the LLM calls a tool, it passes the correct `tool_name` to the `AgentExecutor`.
- **Gemini S2S**: The `RealtimeModel` handles audio directly. It doesn't convert speech-to-text; it *understands* the audio and generates a response.

---

## **3. Key Components Reference**

### **The Executor (`agent_executor.py`)**
The `AgentExecutor` is the bridge between the LLM and the tool implementations.
- It verifies if a tool is enabled.
- It injects both public `config` (like `calendar_id`) and `sensitive_config` (like OAuth tokens) into the tool's `execute` method.

### **The Session Manager (`session_service.py`)**
Prevents "mid-call configuration drift."
- **`start_session`**: Captures a list of all `AgentTool` objects.
- **`get_session`**: Used by the worker to retrieve the exact tool state the call started with.

### **The Tool Implementation (`google_calendar.py`)**
- **`metadata`**: Tells the UI how to render the config form and tells the LLM what the tool does.
- **`execute`**: The actual logic that talks to Google. It receives everything it needs (config + tokens) to perform the action.

---

## **Summary for New Developers**
To add a new capability to the agent:
1.  Define a new class in `tools/implementations/`.
2.  Add it to `tools/base/registry.py`.
3.  The UI will automatically show it.
4.  Once a user enables it, the `worker.py` will automatically register it as a "Function" for the Gemini model the next time a call comes in.
