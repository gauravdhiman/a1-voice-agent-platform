# Tool Architecture Refactoring Proposal

## Overview

This document proposes a refactoring of the tool framework to support explicit action definitions, typed parameters, and proper LLM integration. Currently, tools use a generic `execute(**kwargs)` method, which doesn't provide the LLM with sufficient information about what actions are available and what parameters they accept.

## Current Architecture Analysis

### What Exists

#### 1. BaseTool (base_tool.py)

```python
class ToolMetadata(BaseModel):
    name: str
    description: str
    config_schema: Dict[str, Any]  # For UI configuration
    requires_auth: bool = False
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None

class BaseTool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        pass

    @abstractmethod
    async def execute(self, config: Dict[str, Any], sensitive_config: Dict[str, Any], **kwargs) -> Any:
        """
        Execute tool logic.
        :param config: Public configuration for tool.
        :param sensitive_config: Sensitive/encrypted configuration (tokens, etc.).
        :param kwargs: Arguments passed to tool at runtime.
        """
        pass
```

#### 2. Worker Tool Registration (worker.py:70-88)

```python
for agent_tool in agent_tools:
    if not agent_tool.is_enabled or not agent_tool.tool:
        continue

    tool_name = agent_tool.tool.name
    tool_desc = agent_tool.tool.description

    def create_tool_func(name):
        @fnc_ctx.ai_callable(name=name.lower().replace(" ", "_"), description=tool_desc)
        async def call_tool(
            action: Annotated[str, llm.TypeInfo(description="The action to perform (e.g., 'list_events', 'create_event')")],
            details: Annotated[Optional[str], llm.TypeInfo(description="Additional details or parameters for tool")] = None
        ):
            logger.info(f"LLM calling tool {name} with action: {action}")
            return await executor.run_tool(name, action=action, details=details)
        return call_tool

    create_tool_func(tool_name)
```

#### 3. GoogleCalendarTool (google_calendar.py)

```python
class GoogleCalendarTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Google_calendar",
            description="Manage Google Calendar events...",
            # ... auth config, config_schema
        )

    async def execute(self, config: Dict[str, Any], sensitive_config: Dict[str, Any], **kwargs) -> Any:
        action = kwargs.get("action")

        if action == "list_events":
            # list events logic
        elif action == "create_event":
            # create event logic
        elif action == "get_availability":
            # check availability logic
        else:
            raise ValueError(f"Unknown action: {action}")
```

### The Problems

#### Problem 1: No Action Definition

- Tools don't expose what methods/actions they support
- LLM doesn't know that `list_events`, `create_event`, `check_availability` exist
- It only knows "call this tool with an action string"

**Impact:** LLM has to guess what actions are available, leading to incorrect calls or tool failures.

#### Problem 2: Generic Arguments Instead of Typed Parameters

**Current:**
```python
action: str, details: str  # Everything is strings
```

**Missing:**
- Specific parameters like `start_time: datetime`, `duration: int`, `attendees: list[str]`
- Parameter types (string, integer, datetime, etc.)
- Default values
- Allowed values (enums)

**Impact:** LLM can't be guided on valid parameter types, required vs optional, or valid values.

#### Problem 3: No Argument Schemas for LLM

- No JSON Schema describing what each action accepts
- No required/optional flags
- No parameter descriptions for LLM

**Impact:** LLM generates incorrect parameters, leading to API errors and poor user experience.

#### Problem 4: Monolithic execute() Method

- All actions jammed into one method with if/elif logic
- Violates single responsibility principle
- Hard to maintain as tools grow

**Impact:** Code becomes spaghetti-like, difficult to test, and error-prone.

---

## Proposed Solution: Action-Based Tools

### New Data Model

```
PlatformTool (Database)
  ├─ name: "Google_calendar"
  ├─ description: "Google Calendar integration"
  └─ config_schema: {
      calendar_id: string (for UI)
      default_event_duration: integer (for UI)
    }

Tool (Code)
  ├─ name: "Google_calendar"
  ├─ description: "..."
  ├─ actions: [
  │     Action(
  │       name="list_events",
  │       description="List calendar events...",
  │       parameters=[
  │         {name: "time_min", type: "datetime", required: true},
  │         {name: "time_max", type: "datetime", required: false},
  │         {name: "max_results", type: "integer", default: 10}
  │       ]
  │     ),
  │     Action(name="create_event", ...),
  │     Action(name="check_availability", ...)
  │   ]
  └─ execute_action(action_name, **kwargs) -> Any
```

### Component 1: Add Action Models

**File:** `shared/voice_agents/tools/base/action_models.py`

```python
"""
Models for defining tool actions and their parameters.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ParameterType(str, Enum):
    """Supported parameter types for tool actions."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATETIME = "datetime"


class ActionParameter(BaseModel):
    """Defines a parameter for a tool action."""
    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="What this parameter does")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any = Field(None, description="Default value")
    enum: Optional[List[Any]] = Field(None, description="Allowed values (for enum parameters)")
    min_value: Optional[float] = Field(None, description="Minimum value for number types")
    max_value: Optional[float] = Field(None, description="Maximum value for number types")


class ToolAction(BaseModel):
    """Defines an action that a tool can perform."""
    name: str = Field(..., description="Action name (e.g., 'list_events')")
    description: str = Field(..., description="What this action does")
    parameters: List[ActionParameter] = Field(
        default_factory=list,
        description="Parameters this action accepts"
    )
    returns: str = Field(
        default="any",
        description="Description of what this action returns"
    )
```

### Component 2: Update BaseTool to Support Actions

**File:** `shared/voice_agents/tools/base/base_tool.py`

```python
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from .action_models import ToolAction


class ToolMetadata(BaseModel):
    name: str
    description: str
    config_schema: Dict[str, Any]  # For UI configuration (calendar_id, api_key, etc.)
    requires_auth: bool = False
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        pass

    @property
    @abstractmethod
    def actions(self) -> List[ToolAction]:
        """
        Return list of actions this tool provides.
        Each action should have a corresponding execute_action implementation.
        """
        pass

    @abstractmethod
    async def execute_action(
        self,
        action_name: str,
        config: Dict[str, Any],
        sensitive_config: Dict[str, Any],
        **kwargs
    ) -> Any:
        """
        Execute a specific action.
        :param action_name: The name of the action to execute.
        :param config: Public configuration for the tool.
        :param sensitive_config: Sensitive/encrypted configuration (tokens, etc.).
        :param kwargs: Action-specific parameters passed from LLM.
        """
        pass
```

### Component 3: Refactor GoogleCalendarTool

**File:** `shared/voice_agents/tools/implementations/google_calendar.py`

```python
import httpx
from typing import Any, Dict
from datetime import datetime, timedelta

from shared.voice_agents.tools.base.base_tool import BaseTool, ToolMetadata
from shared.voice_agents.tools.base.action_models import (
    ToolAction,
    ActionParameter,
    ParameterType
)


class GoogleCalendarTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Google_calendar",
            description="Manage Google Calendar events, check availability, and schedule meetings.",
            requires_auth=True,
            auth_type="oauth2",
            auth_config={
                "provider": "google",
                "scopes": [
                    "https://www.googleapis.com/auth/calendar.events",
                    "https://www.googleapis.com/auth/calendar.readonly"
                ],
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token"
            },
            config_schema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "title": "Calendar ID",
                        "default": "primary",
                        "description": "The ID of the calendar to use."
                    },
                    "default_event_duration": {
                        "type": "integer",
                        "title": "Default Event Duration (minutes)",
                        "default": 30
                    }
                },
                "required": ["calendar_id"]
            }
        )

    @property
    def actions(self) -> List[ToolAction]:
        return [
            ToolAction(
                name="list_events",
                description="List calendar events within a time range",
                parameters=[
                    ActionParameter(
                        name="time_min",
                        type=ParameterType.DATETIME,
                        description="Start of time range in ISO format (e.g., 2025-12-30T09:00:00Z)",
                        required=True
                    ),
                    ActionParameter(
                        name="time_max",
                        type=ParameterType.DATETIME,
                        description="End of time range in ISO format (e.g., 2025-12-30T18:00:00Z)",
                        required=False
                    ),
                    ActionParameter(
                        name="max_results",
                        type=ParameterType.INTEGER,
                        description="Maximum number of events to return",
                        required=False,
                        default=10,
                        min_value=1,
                        max_value=100
                    )
                ],
                returns="List of calendar events"
            ),

            ToolAction(
                name="create_event",
                description="Create a new calendar event",
                parameters=[
                    ActionParameter(
                        name="title",
                        type=ParameterType.STRING,
                        description="Event title",
                        required=True
                    ),
                    ActionParameter(
                        name="start_time",
                        type=ParameterType.DATETIME,
                        description="Event start time in ISO format (e.g., 2025-12-30T14:00:00Z)",
                        required=True
                    ),
                    ActionParameter(
                        name="duration_minutes",
                        type=ParameterType.INTEGER,
                        description="Event duration in minutes",
                        required=False,
                        default=30,
                        min_value=5,
                        max_value=480
                    ),
                    ActionParameter(
                        name="attendees",
                        type=ParameterType.ARRAY,
                        description="List of attendee email addresses",
                        required=False
                    ),
                    ActionParameter(
                        name="description",
                        type=ParameterType.STRING,
                        description="Event description",
                        required=False
                    )
                ],
                returns="Created event details"
            ),

            ToolAction(
                name="check_availability",
                description="Check if time slots are free",
                parameters=[
                    ActionParameter(
                        name="date",
                        type=ParameterType.DATETIME,
                        description="Date and time to check in ISO format",
                        required=True
                    ),
                    ActionParameter(
                        name="duration_minutes",
                        type=ParameterType.INTEGER,
                        description="Duration to check in minutes",
                        required=False,
                        default=30,
                        min_value=15,
                        max_value=240
                    )
                ],
                returns="Availability information and any conflicts"
            )
        ]

    async def execute_action(
        self,
        action_name: str,
        config: Dict[str, Any],
        sensitive_config: Dict[str, Any],
        **kwargs
    ) -> Any:
        access_token = sensitive_config.get("access_token")
        if not access_token:
            raise ValueError("No access token found in sensitive_config")

        calendar_id = config.get("calendar_id", "primary")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            if action_name == "list_events":
                time_min = kwargs.get("time_min")
                time_max = kwargs.get("time_max")
                max_results = kwargs.get("max_results", 10)

                response = await client.get(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                    headers=headers,
                    params={
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "maxResults": max_results,
                        "singleEvents": "true",
                        "orderBy": "startTime"
                    }
                )
                response.raise_for_status()
                data = response.json()
                return {"events": data.get("items", [])}

            elif action_name == "create_event":
                title = kwargs.get("title")
                start_time = kwargs.get("start_time")
                duration = kwargs.get("duration_minutes", config.get("default_event_duration", 30))
                attendees = kwargs.get("attendees", [])
                event_description = kwargs.get("description", "")

                # Calculate end time
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_time = (start_dt + timedelta(minutes=duration)).isoformat()

                event = {
                    "summary": title,
                    "description": event_description,
                    "start": {"dateTime": start_time},
                    "end": {"dateTime": end_time}
                }

                if attendees:
                    event["attendees"] = [{"email": email} for email in attendees]

                response = await client.post(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                    headers=headers,
                    json=event
                )
                response.raise_for_status()
                return response.json()

            elif action_name == "check_availability":
                check_date = kwargs.get("date")
                duration = kwargs.get("duration_minutes", 30)

                # Calculate time range
                start_dt = datetime.fromisoformat(check_date.replace('Z', '+00:00'))
                end_dt = (start_dt + timedelta(minutes=duration)).isoformat()

                response = await client.get(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                    headers=headers,
                    params={
                        "timeMin": check_date,
                        "timeMax": end_dt,
                        "singleEvents": "true",
                        "orderBy": "startTime"
                    }
                )
                response.raise_for_status()
                data = response.json()

                has_conflict = len(data.get("items", [])) > 0
                return {
                    "available": not has_conflict,
                    "conflicts": data.get("items", [])
                }

            else:
                raise ValueError(f"Unknown action: {action_name}")
```

### Component 4: Update Worker to Register Actions Individually

**File:** `worker/src/worker.py`

```python
# Update imports
from typing import Annotated

# In the entrypoint function, replace the tool registration loop:

for agent_tool in agent_tools:
    if not agent_tool.is_enabled or not agent_tool.tool:
        continue

    tool_name = agent_tool.tool.name
    tool_class = tool_registry.get_tool_class(tool_name)
    tool_instance = tool_class()

    # Register each action as a separate function for LLM
    for action in tool_instance.actions:
        action_name = action.name

        # Build parameter annotations dynamically based on action parameters
        param_annotations = {}
        param_defaults = {}
        param_descriptions = {}

        for param in action.parameters:
            # Map ParameterType to Python type hints
            if param.type == ParameterType.STRING:
                param_annotations[param.name] = str
            elif param.type == ParameterType.INTEGER:
                param_annotations[param.name] = int
            elif param.type == ParameterType.NUMBER:
                param_annotations[param.name] = float
            elif param.type == ParameterType.BOOLEAN:
                param_annotations[param.name] = bool
            elif param.type == ParameterType.ARRAY:
                param_annotations[param.name] = list
            elif param.type == ParameterType.DATETIME:
                param_annotations[param.name] = str  # ISO string
            elif param.type == ParameterType.OBJECT:
                param_annotations[param.name] = dict

            # Set default if not required
            if not param.required and param.default is not None:
                param_defaults[param.name] = param.default

            param_descriptions[param.name] = param.description

        def create_action_func(act_name, anns, defaults, descs):
            @fnc_ctx.ai_callable(name=act_name, description=action.description)
            async def call_action(**kwargs):
                logger.info(f"LLM calling action {act_name} with args: {kwargs}")
                return await executor.run_tool_action(tool_name, act_name, **kwargs)
            return call_action

        create_action_func(action_name, param_annotations, param_defaults, param_descriptions)
```

**Note:** The above is a simplified version. In production, you'd need to properly handle Annotated types for each parameter to give LLM full schema information.

### Component 5: Update AgentExecutor

**File:** `shared/voice_agents/agent_executor.py`

```python
# Add new method to AgentExecutor class

async def run_tool_action(self, tool_name: str, action_name: str, **kwargs) -> Any:
    """
    Execute a specific tool action.
    """
    # 1. Check if tool is enabled for this agent
    agent_tools = await self.get_tools()

    agent_tool = next(
        (at for at in agent_tools if at.tool and at.tool.name == tool_name),
        None
    )

    if not agent_tool:
        raise Exception(f"Tool {tool_name} is not configured for this agent")

    if not agent_tool.is_enabled:
        raise Exception(f"Tool {tool_name} is currently disabled for this agent")

    # 2. Get tool implementation from registry
    tool_class = tool_registry.get_tool_class(tool_name)
    if not tool_class:
        raise Exception(f"Tool implementation {tool_name} not found in registry")

    tool_instance = tool_class()

    # 3. Execute the specific action
    # Note: tool_service already decrypts sensitive_config during get_agent_tools
    return await tool_instance.execute_action(
        action_name=action_name,
        config=agent_tool.config or {},
        sensitive_config=agent_tool.sensitive_config or {},
        **kwargs
    )
```

---

## Summary of Changes

| Component | Current | Proposed |
|-----------|----------|-----------|
| **BaseTool** | Single `execute(**kwargs)` method | `actions` property + `execute_action(action_name, **kwargs)` |
| **Worker Registration** | One generic function/tool with `action` and `details` strings | One function per action with properly typed parameters |
| **LLM Sees** | `google_calendar(action="list_events", details="...")` | `list_events(time_min="...", time_max="...", max_results=10)`, `create_event(title="...", start_time="...", ...)` |
| **Action Metadata** | None (actions hidden in code) | Full schema: name, description, parameters (type, required, default, min/max, enum) |
| **Google Calendar** | Monolithic `execute()` with if/elif chain | Clean `execute_action()` with explicit action handlers |

## Benefits

✅ **Explicit Action Definitions**
- Tools declare what actions they support
- LLM knows exactly which functions are available
- No guessing or hidden functionality

✅ **Typed Parameters**
- Each action has specific parameter types (string, integer, datetime, etc.)
- LLM knows what data types to provide
- Reduces API errors from malformed parameters

✅ **Parameter Validation**
- Required vs optional parameters clearly defined
- Default values specified
- Min/max constraints for numbers
- Enum options for constrained choices

✅ **Better LLM Integration**
- Each action becomes its own LLM function
- LLM sees `list_events(time_min, time_max, max_results)` instead of `google_calendar(action, details)`
- Higher accuracy in function calling

✅ **Cleaner Code**
- Single responsibility per action
- Easier to test individual actions
- Easier to add new actions to existing tools

✅ **Scalable Framework**
- Easy to add new tools with multiple actions
- Example: Email tool could have `send_email`, `check_inbox`, `schedule_draft`
- Each action independently configured

## Migration Path

1. **Create `action_models.py`** - Define new action parameter models
2. **Update `BaseTool`** - Add `actions` property, deprecate `execute()`
3. **Refactor existing tools** - Convert `execute()` to `execute_action()` with explicit action handling
4. **Update `AgentExecutor`** - Add `run_tool_action()` method
5. **Update `worker.py`** - Register actions individually instead of generic tool functions
6. **Test thoroughly** - Ensure LLM can call actions correctly

## Example: Adding a New Tool

```python
# shared/voice_agents/tools/implementations/email_tool.py

class EmailTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="Email",
            description="Send emails via SMTP or API",
            requires_auth=True,
            auth_type="api_key",
            auth_config={...},
            config_schema={
                "smtp_server": {"type": "string"},
                "smtp_port": {"type": "integer", "default": 587},
                "from_email": {"type": "string"}
            }
        )

    @property
    def actions(self) -> List[ToolAction]:
        return [
            ToolAction(
                name="send_email",
                description="Send an email to a recipient",
                parameters=[
                    ActionParameter(
                        name="to",
                        type=ParameterType.STRING,
                        description="Recipient email address",
                        required=True
                    ),
                    ActionParameter(
                        name="subject",
                        type=ParameterType.STRING,
                        description="Email subject",
                        required=True
                    ),
                    ActionParameter(
                        name="body",
                        type=ParameterType.STRING,
                        description="Email body content",
                        required=True
                    )
                ]
            )
        ]

    async def execute_action(self, action_name, config, sensitive_config, **kwargs):
        if action_name == "send_email":
            # Implementation
            pass
```

This makes it trivial to add new tools and actions with full LLM awareness.
