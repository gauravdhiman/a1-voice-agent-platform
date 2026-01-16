# Tool Architecture Implementation Summary

This document summarizes all changes implemented based on tool system architecture decisions and recent improvements.

## Recent Updates (January 2026)

### Gmail Tool Set Implementation

**File**: `shared/voice_agents/tools/implementations/gmail.py`

**New Tool Functions**:

| Function | Description | Parameters |
|----------|-------------|------------|
| `get_latest_emails` | Get latest emails from inbox | `count: int = 5` (max 10) |
| `get_emails_from_user` | Get emails from specific sender | `user: str`, `count: int = 5` |
| `get_unread_emails` | Get unread emails | `count: int = 5` |
| `get_starred_emails` | Get starred emails | `count: int = 5` |
| `get_emails_by_context` | Get emails matching search query | `query: str`, `count: int = 5` |
| `create_draft_email` | Create new email draft | `to: str`, `subject: str`, `body: str`, `cc: Optional[str]` |
| `get_emails_by_label` | Get emails with specific label | `label_name: str`, `count: int = 5` |
| `get_labels` | List all Gmail labels | None |
| `apply_label` | Apply label to emails matching query | `query: str`, `label_name: str`, `count: int = 5` |
| `remove_label` | Remove label from emails matching query | `query: str`, `label_name: str`, `count: int = 5` |

**Response Size Limits**:
- Default: 5 emails per operation
- Maximum: 10 emails per operation
- Email body truncated to 500 characters to prevent API errors

**Authentication**: OAuth2 (Google)

### Tool Wrapper Fixes (Type Hints)

**File**: `worker/src/worker.py`

**Problem**: `Optional`, `Dict`, `List`, `Union` type hints not available in `exec()` namespace

**Solution**:
```python
# Import typing constructs
from typing import Any, Dict, List, Optional, Union

# Add to namespace
namespace = {
    "Any": Any,
    "Dict": Dict,
    "List": List,
    "Optional": Optional,  # For Optional[str]
    "Union": Union,          # For list[str] | None
    "RunContext": RunContext,
    "bound_method": bound_method,
    "logger": logger,
}
```

**Added logging**:
```python
result = await bound_method(context=context, **kwargs)
import json
try:
    result_str = json.dumps(result, default=str)
    logger.debug(f"Tool {func_name} result size: {len(result_str)} chars")
except Exception as e:
    logger.error(f"Failed to serialize tool {func_name} result: {e}")
```

### Default Value Preservation

**File**: `worker/src/worker.py`

**Problem**: Default parameter values not preserved in wrapper function

**Solution**:
```python
# Accept sig instead of param_names
def _create_tool_wrapper(
    bound_method: Any,
    func_name: str,
    sig: inspect.Signature,  # NEW: Pass signature
    type_hints: dict
) -> Any:
    # Extract Parameter objects with defaults
    for param_name, param in sig.parameters.items():
        if param.default != inspect.Parameter.empty:
            param_def += f" = {repr(param.default)}"  # Include default
```

### Tool Connection States

**File**: `shared/voice_agents/tool_models.py`

**New Enum**: `ConnectionStatus`

```python
class ConnectionStatus(str, Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTED_NO_AUTH = "connected_no_auth"
    CONNECTED_AUTH_VALID = "connected_auth_valid"
    CONNECTED_AUTH_INVALID = "connected_auth_invalid"
```

**Helper Function**: `get_connection_status()`

```python
def get_connection_status(
    requires_auth: bool,
    auth_status: AuthStatus
) -> ConnectionStatus:
    """Derive connection status from tool requirements and auth state."""
    if not requires_auth:
        return ConnectionStatus.CONNECTED_NO_AUTH
    if auth_status == AuthStatus.AUTHENTICATED:
        return ConnectionStatus.CONNECTED_AUTH_VALID
    return ConnectionStatus.CONNECTED_AUTH_INVALID
```

### UI Updates - Tool Cards

**File**: `frontend/src/components/tools/tool-card.tsx`

**Visual States**:

| Connection Status | Card Color | Badge | Badge Text | Icon |
|------------------|-------------|-------|-------------|-------|
| NOT_CONNECTED | White | Gray | "Not connected" | Wrench |
| CONNECTED_NO_AUTH | Light green | Light green | "Connected" | ShieldCheck |
| CONNECTED_AUTH_VALID | Light green | Light green | "Authenticated" | ShieldCheck |
| CONNECTED_AUTH_INVALID | Light red | Light red | "Authentication required" | XCircle |

**Dark mode support**: All colors include dark variants

### UI Updates - Tool Filters

**File**: `frontend/src/components/tools/tool-filters.tsx`

**Filter Labels**:
- Changed from: "All", "Configured", "Not configured"
- Changed to: "All", "Connected", "Not Connected"

**Filter Logic**:
```typescript
if (toolFilterType === "connected") {
  filtered = filtered.filter(
    (tool) => localAgentTools.find((at) => at.tool_id === tool.id) !== undefined,
  );
} else if (toolFilterType === "not_connected") {
  filtered = filtered.filter(
    (tool) => !localAgentTools.find((at) => at.tool_id === tool.id),
  );
}
```

### Tool Connect/Disconnect Flow

**Files**:
- `frontend/src/components/tools/tool-disconnect-dialog.tsx` (new)
- `frontend/src/components/tools/tool-config-drawer.tsx` (updated)
- `frontend/src/components/ui/delete-button.tsx` (new)
- `frontend/src/components/ui/delete-confirmation-dialog.tsx` (new)

**Flow**:
1. User clicks "Connect" on tool card → Creates `agent_tools` record
2. Tool card updates to `CONNECTED_NO_AUTH` or `CONNECTED_AUTH_INVALID`
3. User clicks "Tools" → Opens drawer
4. Drawer has "Disconnect" button → Shows confirmation dialog
5. On confirm → Deletes `agent_tools` record → Tool returns to `NOT_CONNECTED`

**Removal**: No enable/disable switch for toolsets, only function-level control

### Google Calendar Enhancements

**File**: `shared/voice_agents/tools/implementations/google_calendar.py`

**New Functions**:
- `update_event`: Update existing calendar event
- `delete_event`: Delete calendar event

---

## Changes Implemented

## Changes Implemented

### 1. Database Migration

**File**: `backend/alembic/versions/20251230000002_add_tool_functions_schema_and_unselected_functions.py`

**Changes**:

- Added `tool_functions_schema` JSONB column to `platform_tools` table
- Added `unselected_functions` TEXT[] column to `agent_tools` table
- Supports downgrade for rollback

**Status**: ✅ Created (not yet applied)

### 2. Tool Models

**File**: `shared/voice_agents/tool_models.py`

**Changes**:

- Added `tool_functions_schema: Optional[Dict[str, Any]]` field to `PlatformToolCreate` and `PlatformTool`
- Changed `selected_functions` → `unselected_functions: Optional[List[str]]` in `AgentToolBase`
- Added `List` to imports

**Status**: ✅ Implemented

### 3. Tool Registry

**File**: `shared/voice_agents/tools/base/registry.py`

**Changes**:

- Added `_get_json_type()` helper function to map Python types to JSON schema types
- Added `_extract_function_schema()` to generate LiveKit-compatible function schemas from `@function_tool` decorators
- Updated `sync_with_db()` to:
  - Extract function schemas from `@function_tool` methods
  - Store them in `tool_functions_schema` JSONB field
  - Update existing tools with new schema when code changes

**Status**: ✅ Implemented

### 4. Worker

**File**: `worker/src/worker.py`

**Changes**:

- Updated to filter functions by `unselected_functions` instead of `selected_functions`
- Added safety checks for stale function names:
  - Detects functions in `unselected_functions` that no longer exist in code
  - Logs warnings instead of crashing
  - Only filters if function exists in both places
- Updated logic to skip unselected functions while exposing all others by default

**Status**: ✅ Implemented

### 5. Backend Routes

**File**: `backend/src/voice_agents/tool_routes.py`

**Changes**:

- Removed test endpoint `POST /agent/{agent_id}/test/{tool_name}` that used `AgentExecutor`
- No other changes needed (routes already support new fields via models)

**Status**: ✅ Cleaned up

### 6. Removed AgentExecutor

**Files**:

- Deleted: `shared/voice_agents/agent_executor.py`
- Updated: `shared/voice_agents/__init__.py` (removed `AgentExecutor` from exports)
- Updated: `backend/scripts/test_tool_execution.py` (added deprecation comment)

**Status**: ✅ Cleaned up

### 7. Frontend Types

**File**: `frontend/src/types/agent.ts`

**Changes**:

- Added `PlatformToolFunction` interface for function schema representation
- Updated `PlatformTool` to include `tool_functions_schema: { functions: PlatformToolFunction[] } | null`
- Updated `AgentTool` to include `unselected_functions: string[] | null`
- Updated `AgentToolCreate` to include `unselected_functions?: string[] | null`
- Updated `AgentToolUpdate` to include `unselected_functions?: string[] | null`

**Status**: ✅ Implemented

### 8. Frontend UI

**File**: `frontend/src/app/(dashboard)/organization/page.tsx`

**Changes**:

- Added `unselectedFunctions` state to track unselected functions per tool
- Added `handleToggleFunction()` to toggle individual functions on/off
- Updated `handleToggleTool()` to preserve `unselected_functions` when enabling/disabling tool
- Updated `renderToolConfig()` to:
  - Display functions from `tool_functions_schema`
  - Show checkboxes for each function
  - Indicate which functions are unselected
  - Show function descriptions and parameters
  - Only show function list when tool is enabled

**Status**: ✅ Implemented

### 6. Removed AgentExecutor

**Files**:

- Deleted: `shared/voice_agents/agent_executor.py`
- Updated: `shared/voice_agents/__init__.py` (removed `AgentExecutor` from exports)
- Updated: `backend/scripts/test_tool_execution.py` (added deprecation comment)

**Status**: ✅ Cleaned up

## Key Design Decisions

### Why `unselected_functions` vs `selected_functions`?

**Decision**: Use `unselected_functions` to track functions to DISABLE, with all others ENABLED by default.

**Benefits**:

1. **Default behavior**: All functions enabled when tool set is added to agent
2. **Data integrity during refactors**:
   - If function is renamed: Agent automatically gets new function
   - Stale `unselected_functions` entries are ignored gracefully
   - Worst case: Agent gets extra functionality (not loses existing functionality)
3. **Safer**: Providing an agent with extra tools is less harmful than removing previously configured tools

### Configuration Storage

**Platform Tool Level** (`platform_tools.config_schema`):

- Schema for UI configuration (e.g., calendar_id, default_event_duration)

**Agent Tool Level** (`agent_tools.config`):

- Tool set configuration for specific agent (e.g., calendar_id = "primary")

**Function Level** (not implemented - future):

- Could be added to JSONB in future if needed (e.g., list_events.max_results = 20)

**Sensitive Configuration** (`agent_tools.sensitive_config`):

- Encrypted storage for OAuth tokens, API keys
- Stored at tool set level (shared by all functions)

### Schema Storage

**`tool_functions_schema` in `platform_tools`**:

- Stores all function schemas from `@function_tool` decorated methods
- Used for debugging and inspection
- Format: `{"functions": [{"type": "function", "name": "...", ...}]}`

### Function Filtering in Worker

**Logic**:

```python
# 1. Get actual function names from code
actual_func_names = {func.__name__ for func in all_functions}

# 2. Detect stale entries in unselected_functions
stale_functions = set(unselected_func_names) - actual_func_names
if stale_functions:
    logger.warning(f"Found stale unselected functions: {stale_functions}")

# 3. Only skip if function both in unselected AND exists
if func_name in unselected_func_names and func_name in actual_func_names:
    continue
```

## Migration Path

### Steps to Apply Changes:

1. **Apply Database Migration**:

   ```bash
   cd backend
   source .venv/bin/activate  # Activate virtual environment
   alembic upgrade head
   ```

2. **Restart Backend**:

   - The `main.py` startup event will call `tool_registry.sync_with_db()`
   - This will populate `tool_functions_schema` for all registered tools

3. **Update Frontend** (if needed):

   - Display `tool_functions_schema` to show available functions per tool set
   - Allow users to unselect functions (not select)
   - Update API calls to use `unselected_functions` field

4. **Testing**:
   - Test tool registration and schema extraction
   - Test function filtering with `unselected_functions`
   - Test stale function name handling
   - Test OAuth flow with new schema

## Files Modified

| File                                                           | Changes              |
| -------------------------------------------------------------- | -------------------- |
| `backend/alembic/versions/20251230000002_*.py`                 | ✅ Created (new)     |
| `shared/voice_agents/tool_models.py`                           | ✅ Updated           |
| `shared/voice_agents/tools/base/registry.py`                   | ✅ Updated           |
| `worker/src/worker.py`                                         | ✅ Updated           |
| `backend/src/voice_agents/tool_routes.py`                      | ✅ Cleaned up        |
| `shared/voice_agents/__init__.py`                              | ✅ Updated           |
| `shared/voice_agents/agent_executor.py`                        | ✅ Deleted           |
| `backend/scripts/test_tool_execution.py`                       | ✅ Marked deprecated |
| `shared/voice_agents/tools/base/action_models.py`              | ✅ Deleted           |
| `shared/voice_agents/tools/base/__init__.py`                   | ✅ Updated           |
| `shared/voice_agents/tools/implementations/google_calendar.py` | ✅ Already correct   |

## Next Steps (Optional Enhancements)

1. **Frontend Implementation**:

   - Show tool functions for each platform tool
   - Allow users to unselect functions
   - Display function schemas for debugging

2. **Function-Level Configuration** (if needed):

   - Add to `tool_functions_schema` in `platform_tools`
   - Support per-function config in UI
   - Add config merging logic in worker

3. **Analytics**:

   - Track which functions are most used
   - Track OAuth success/failure rates
   - Monitor stale function detection

4. **Testing Infrastructure**:
   - Write proper tests for tool registration
   - Write tests for function filtering
   - Write tests for stale function handling

### User Interface Features

The updated UI provides:

1. **Tool Set Level Configuration**:

   - Enable/disable entire tool set for agent
   - Configure tool set parameters (e.g., calendar_id)

2. **Function Level Control**:

   - View all available functions from `tool_functions_schema`
   - Enable/disable individual functions per agent
   - Default: All functions enabled when tool set is added
   - Track which functions are unselected

3. **OAuth Integration**:

   - "Connect" button for tools requiring OAuth
   - Saves tokens to `sensitive_config`

4. **Visual Indicators**:
   - Function count: "X total, Y enabled"
   - Status badges for enabled/disabled functions
   - Authentication requirement indicators
