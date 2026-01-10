# Tool Architecture Implementation Summary

This document summarizes all changes implemented based on `TOOL_ARCHITECTURE_DECISION.md`.

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
