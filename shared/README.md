# Shared Code - Voice Agents Platform

This directory contains code shared between the backend and `voice-ws` services, specifically for the voice agents system.

The shared billing helpers define the canonical voice meter: connected duration
is rounded up to whole minutes with a one-minute minimum. Admission is prepaid,
but final call settlement is performed atomically by the database RPC so an
admitted call can complete and be charged in full.

## 🏗️ Architecture

### Purpose

The shared module allows both the backend (for API endpoints) and `voice-ws` (for voice agent execution) to use the same:

- **Data models**: Pydantic models for tools, agents, and configurations
- **Business logic**: Service layer for tool and agent management
- **Tool implementations**: Reusable tool classes
- **Type definitions**: Consistent types across services

```mermaid
graph TB
    subgraph Shared["shared/ Module"]
        VA[voice_agents/]
        VA --> VS[service.py]
        VA --> TS[tool_service.py]
        VA --> TM[tool_models.py]
        VA --> VSS[voice_session_service.py]
        VA --> TOOLS[tools/]
        VA --> MD[models.py]

        CFG[config/]
        COM[common/]
    end

    subgraph Backend["backend/ (FastAPI)"]
        BR[API Routes]
        BR[Tool Management Endpoints]
        BR[Agent Management Endpoints]
        BR[Voice session JWT issuance]
    end

    subgraph VoiceWS["voice-ws/ (Pipecat)"]
        WK[WebSocket /ws and /twilio]
        WK[Tool assembly + MCP]
        WK[Speech pipeline / realtime]
    end

    subgraph Database["Supabase"]
        DB[voice_agents]
        DB[agent_tools]
        DB[platform_tools]
        DB[tool_functions]
    end

    BR --> VA
    WK --> VA
    VA --> DB
```

## 📁 Directory Structure

```
shared/
├── voice_agents/
│   ├── service.py           # Voice agent CRUD operations
│   ├── tool_service.py      # Tool CRUD and query operations
│   ├── tool_models.py       # Pydantic models for tools
│   ├── voice_session_service.py  # Short-lived JWT for voice-ws sessions
│   ├── models.py           # Voice agent data models
│   ├── speech_config.py   # Per-agent speech engine config (realtime vs pipeline; discriminated union)
│   ├── preset_models.py   # Platform-admin preset Pydantic models (Phase 3)
│   ├── preset_service.py  # Platform-admin preset catalog CRUD (Phase 3; mirrors tool_service)
│   ├── key_resolver.py    # Per-org provider key resolver: SpeechConfig + encrypted provider_credentials -> api_keys (Phase 3)
│   ├── tools/             # Tool implementation framework
│   │   ├── base/
│   │   │   ├── base_tool.py            # Base class for tools
│   │   │   ├── action_models.py        # Action function models
│   │   │   ├── platform_tool_registry.py    # Tool registry for voice-ws
│   │   │   └── __init__.py
│   │   └── implementations/            # Concrete tool implementations
│   │       ├── google_calendar_appointment.py # Google Calendar appointment tool
│   │       ├── gmail.py                # Gmail tool
│   │       └── resend_email.py         # Route-based Resend follow-up tool
│   └── __init__.py
├── notifications/
│   ├── email_providers.py              # Shared async provider adapter contract
│   └── __init__.py
├── config/
│   ├── opentelemetry.py   # OpenTelemetry setup
│   ├── settings.py        # Environment-based settings
│   ├── supabase.py       # Supabase client initialization
│   └── __init__.py
├── common/
│   ├── errors.py          # Common error classes
│   ├── security.py        # Security utilities
│   └── __init__.py
└── __init__.py
```

## 🔑 Key Components

### 1. Voice Agent Service (`voice_agents/service.py`)

**Purpose**: CRUD operations for voice agents

**Key Methods**:

- `create_voice_agent()`: Create new voice agent
- `get_voice_agent()`: Get voice agent by ID
- `update_voice_agent()`: Update agent configuration
- `delete_voice_agent()`: Delete agent
- `list_voice_agents()`: List agents (with filters)

**Usage**:

```python
from shared.voice_agents.service import voice_agent_service

# Create agent
agent = await voice_agent_service.create_voice_agent(
    VoiceAgentCreate(
        name="Support Agent",
        organization_id=org_id,
        system_prompt="You are a helpful support agent...",
        is_active=True
    )
)

# Get agent with tools
agent_with_tools = await voice_agent_service.get_voice_agent(agent_id, include_tools=True)
```

### 2. Tool Service (`voice_agents/tool_service.py`)

**Purpose**: Two-tier service for tool management

#### For Backend (API Layer)

Returns **safe responses** without sensitive data:

```python
# Get tools for API response (no OAuth tokens)
tools = await tool_service.get_tools_by_organization(org_id, safe=True)
# Each tool has: id, name, description, config_schema, metadata
# Does NOT have: sensitive_config, OAuth tokens
```

#### For voice-ws (Agent Execution)

Returns **full tool objects** with all configuration:

```python
# Get tool for voice-ws (includes OAuth tokens)
tool_instance = await tool_service.get_tool_instance(tool_id, org_id)
# Returns: Tool class instance with:
# - config (public config)
# - sensitive_config (OAuth tokens, secrets)
# - All methods callable by LLM
```

**Key Methods**:

- `create_tool()`: Register new platform tool
- `get_tool()`: Get tool metadata
- `get_tool_instance()`: Instantiate tool with full config (for voice-ws)
- `get_tools_by_organization()`: List tools (safe mode for API)
- `associate_tool_with_agent()`: Link tool to agent
- `get_tools_for_agent()`: Get all tools for an agent

### 3. Tool Models (`voice_agents/tool_models.py`)

**Purpose**: Pydantic models for tools

**Key Models**:

- `ToolMetadata`: Tool name, description, config schema, auth info
- `ToolConfig`: Public configuration for tool (calendar ID, etc.)
- `ToolSensitiveConfig`: Sensitive data (OAuth tokens, API keys)
- `ToolFunctionMetadata`: Metadata about tool methods
- `ToolCreate/Update`: Request models for tool CRUD
- `ToolInstanceResponse`: Safe response for API (no secrets)

**Usage**:

```python
from shared.voice_agents.tool_models import ToolMetadata, ToolConfig

# Tool metadata
metadata = ToolMetadata(
    name="Google_calendar",
    description="Manage Google Calendar events...",
    requires_auth=True,
    auth_type="oauth2",
    config_schema={"type": "object", "properties": {...}}
)

# Tool config
config = ToolConfig(
    calendar_id="primary",
    default_event_duration=30
)
```

### 4. Base Tool Class (`voice_agents/tools/base/base_tool.py`)

**Purpose**: Abstract base class for all tool implementations

**Structure**:

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Tool metadata for LLM and UI."""
        pass

    async def test_tool(self, context: RunContext) -> dict[str, Any]:
        """Test tool configuration."""
        pass

    # Implementations add their own methods
    async def check_availability(self, context: RunContext, ...) -> dict:
        pass

    async def create_event(self, context: RunContext, ...) -> dict:
        pass
```

**Implementing a Tool**:

```python
from shared.voice_agents.tools.base.base_tool import BaseTool

class MyTool(BaseTool):
    class Config(BaseConfig):
        my_param: str = "default"

    class SensitiveConfig(BaseSensitiveConfig):
        api_key: str = ""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="MyTool",
            description="My tool description",
            # ...
        )

    async def my_action(
        self,
        context: RunContext,
        param1: str,
        optional_param: str | None = None
    ) -> dict[str, Any]:
        """Action description for LLM."""
        # Implementation
        return {"result": "..."}
```

### 5. Tool Registry (`voice_agents/tools/base/platform_tool_registry.py`)

**Purpose**: Auto-discover and register platform tool implementations for `voice-ws`

**Process**:

1. Scan `shared.voice_agents.tools.implementations` package
2. Import all tool classes
3. Register each tool class in the registry dictionary
4. Provide methods to instantiate tools

**Usage**:

```python
from shared.voice_agents.tools.base.platform_tool_registry import platform_tool_registry

platform_tool_registry.register_tools_from_package(
    "shared.voice_agents.tools.implementations"
)
tool_class = platform_tool_registry.get_tool_class("Google_calendar")
tool_instance = tool_class(config, sensitive_config)
```

### 6. Voice Session Service (`voice_agents/voice_session_service.py`)

**Purpose**: Issue and validate short-lived JWTs for browser and Twilio voice sessions

**Integration flow**:

1. Backend validates agent and creates a `voice_ws_session` JWT (`JWT_SECRET_KEY`)
2. Browser or Twilio connects to `voice-ws` at `/ws` or `/twilio?token=…`
3. `voice-ws` verifies the JWT, loads agent config, and starts the Pipecat session
4. For phone calls, backend sets `VOICE_WS_TWILIO_URL` so Twilio Media Streams reach `/twilio`

### 7. Configuration (`config/`)

**opentelemetry.py**: OpenTelemetry initialization

- Sets up tracing, metrics, logging
- Configures OTLP exporter
- Registers instrumentation

**settings.py**: Environment-based configuration

- Database URL
- OAuth settings
- Voice WebSocket URLs (`VOICE_WS_PUBLIC_URL`, `VOICE_WS_TWILIO_URL`)
- Feature flags

**supabase.py**: Supabase client initialization

- Creates async Supabase client
- Provides table access methods

### 8. Common Utilities (`common/`)

**errors.py**: Custom error classes

- `ToolNotFoundError`
- `AgentNotFoundError`
- `ConfigurationError`
- etc.

**security.py**: Security utilities

- Token validation
- Secret handling
- Sanitization

## 🔑 Key Design Patterns

### 1. Two-Tier Service

**Rationale**: Different security requirements for API vs. voice-ws

**Backend (API Layer)**:

```python
# Get tools for display in UI - NO secrets
tools = await tool_service.get_tools_by_organization(org_id, safe=True)
# Returns: Tool name, description, config schema (for form inputs)
# Does NOT return: OAuth tokens, API keys, etc.
```

**voice-ws (Agent Execution)**:

```python
# Get tool for LLM execution - WITH secrets
tool_instance = await tool_service.get_tool_instance(tool_id, org_id)
# Returns: Fully instantiated tool with:
# - config (calendar_id, etc.)
# - sensitive_config (access_token, refresh_token, etc.)
# - All methods callable by LLM
```

### 2. No Session Manager

**Rationale**: Statelessness and simplicity

**Implementation**:

- `voice-ws` fetches tools directly from database each session
- No in-memory session manager
- Each call gets fresh configuration and OAuth tokens

**Benefits**:

- Simplified architecture
- No stale configuration
- Easy to scale (multiple voice-ws instances)
- Configuration changes take effect immediately

### 3. Base Class Pattern

**Rationale**: Consistent tool interface

**Benefits**:

- All tools have same structure
- Auto-discovery via registry
- Type safety with Pydantic models
- Clear metadata for LLM and UI

### 4. Tool Registration

**Process**:

1. Tool classes defined in `shared.voice_agents.tools.implementations`
2. `voice-ws` imports package via platform tool registry
3. Registry auto-discovers all tool classes
4. `voice-ws` queries database for enabled tools
5. `voice-ws` instantiates tools with config
6. Tools expose JSON schemas for Pipecat / LLM function calling

## 🔧 Using the Shared Module

### In Backend

```python
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.tool_service import tool_service

# API endpoint: List tools
@app.get("/api/tools")
async def list_tools(org_id: str):
    tools = await tool_service.get_tools_by_organization(org_id, safe=True)
    return {"tools": tools}
```

### In voice-ws

```python
from shared.voice_agents.service import voice_agent_service
from shared.voice_agents.tool_service import tool_service

agent = await voice_agent_service.get_voice_agent(agent_id, include_tools=True)
tool_instance = await tool_service.get_tool_instance(tool_id, org_id)
```

### Adding a New Tool

1. Create tool class in `shared.voice_agents/tools/implementations/`:

   ```python
   class MyTool(BaseTool):
       # Implementation
   ```

2. Tool is auto-registered by `platform_tool_registry.py`

3. `voice-ws` automatically discovers and uses it

4. Backend can query tool metadata for UI

## 📊 Database Schema

### Tables Used

**voice_agents**: Agent definitions

- id, name, organization_id, system_prompt, is_active, created_at, etc.

**agent_tools**: Agent-tool associations

- id, agent_id, tool_id, config, is_enabled, function_enables

**platform_tools**: Tool definitions

- id, name, description, requires_auth, auth_type, etc.

**tool_functions**: Tool function/method metadata

- id, tool_id, function_name, description, parameters, etc.

**tool_sensitive_configs**: Encrypted tool secrets

- id, tool_id, organization_id, config (encrypted)

## 🔐 Security Considerations

1. **OAuth Tokens**: Stored encrypted in database
2. **Two-Tier Service**: API never returns sensitive data
3. **Safe Mode**: Default mode for tool queries (no secrets)
4. **voice-ws Security**: Only voice-ws has access to full tool instances
5. **Environment Variables**: All secrets in environment (not in code)

## 📚 Related Documentation

- [voice-ws Documentation](../voice-ws/README.md)
- [Voice Agents Overview](../docs/02_features/voice_agents/overview.md)
- [Tool Connection States](../docs/02_features/voice_agents/tool_connection_states.md)
- [Outbound phone calls](../docs/03_implementation/outbound_phone_calls.md)
- [OAuth Setup](../docs/02_core_systems/oauth_setup.md)

## 🚧 Future Enhancements

- [ ] Tool versioning
- [ ] Tool dependencies
- [ ] Tool composition (multiple tools combined)
- [ ] Tool sandboxing
- [ ] Rate limiting per tool
- [ ] Tool health monitoring

---

For questions about the shared module:

- Check individual module files for docstrings
- Review examples in tool implementations
- Refer to service layer for usage patterns
