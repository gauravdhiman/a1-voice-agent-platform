# LiveKit Tool Wrapping Architecture

This document explains how the LiveKit agent system wraps tool methods for use with LLMs (like Gemini Realtime).

## Overview

The worker fetches tool implementations from the database and wraps them for use with LiveKit's `function_tool` decorator. Each tool class (e.g., `GoogleCalendarTool`) has multiple methods that can be called by the agent.

## Challenge

**Problem:** Tool methods have a `self` parameter (for accessing instance state) and a `RunContext` parameter (injected by LiveKit). However, LiveKit's `function_tool` decorator cannot directly accept bound methods or functions with `self` parameter.

**Solution:** Create a standalone wrapper function with the same signature as the original method (excluding `self`), which delegates to the bound method.

## How It Works

### Step 1: Tool Class Definition

```python
class GoogleCalendarTool(BaseTool):
    """Tool for managing Google Calendar."""

    async def create_event(
        self,
        context: RunContext,        # Injected by LiveKit
        title: str,
        start_time: str,
        duration_minutes: int = 30,
        attendees: list[str] | None = None,
        description: str | None = None  # Must use | None = None for optional
    ) -> dict[str, Any]:
        """Create a new calendar event."""
        # ... implementation
```

**Key Points:**

- `self`: Accesses instance config (`self.config`, `self.sensitive_config`)
- `context`: LiveKit provides this automatically when calling the tool
- Other parameters: Provided by LLM from user input
- `| None = None`: Makes parameter truly optional (not `str = ""` which is still required)

### Step 2: Wrapper Creation

In the worker's `entrypoint()`, we process each tool method:

```python
for func in functions:
    func_name = func.__name__

    # Get bound method from instance
    bound_method = getattr(tool_instance, func_name)

    # Get original function from class
    original_func = getattr(tool_class, func_name)
    sig = inspect.signature(original_func)

    # Extract parameters (excluding 'self')
    param_names = [name for name in sig.parameters.keys() if name != 'self']

    # Extract type hints (excluding 'self')
    type_hints = {
        k: v for k, v in original_func.__annotations__.items()
        if k != 'self'
    }

    # Create wrapper
    wrapper = _create_tool_wrapper(bound_method, func_name, param_names, type_hints)
```

### Step 3: `_create_tool_wrapper` Function

This helper function creates a wrapper with the **exact same signature** as the original method:

```python
def _create_tool_wrapper(bound_method: Any, func_name: str, param_names: list[str], type_hints: dict) -> Any:
    """
    Create a wrapper function for a tool method.

    The wrapper has the same signature as the original method (excluding 'self').
    It accepts all parameters explicitly (no **kwargs), then delegates to the bound method.
    """
    # Build parameter definitions
    params_def = ["context: RunContext"]
    for param_name in param_names[1:]:
        param_type = type_hints.get(param_name, Any)
        # Convert type to string representation for use in f-string
        if hasattr(param_type, '__name__'):
            type_str = param_type.__name__
        else:
            type_str = 'Any'
        params_def.append(f"{param_name}: {type_str}")

    params_str = ", ".join(params_def)

    # Create wrapper function dynamically using exec()
    # We name it correctly from the start (not {func_name}_wrapper)
    wrapper_code = f"""
async def {func_name}({params_str}) -> Any:
    '''Wrapper for {func_name}.'''
    # Build kwargs dict for all parameters except context
    kwargs = {{}}
    for pname in {param_names[1:]:!r}:
        kwargs[pname] = locals()[pname]
    return await bound_method(context=context, **kwargs)
"""

    # Execute the code
    namespace = {
        'Any': Any,
        'RunContext': RunContext,
        'bound_method': bound_method,
    }
    local_scope = {}
    exec(wrapper_code, namespace, local_scope)
    wrapper = local_scope[func_name]

    # Copy type hints from original function (excluding 'self')
    wrapper.__annotations__ = type_hints

    return wrapper
```

**What This Does:**

1. Creates a function with **exact same signature** as original (excluding `self`)
2. Names it correctly as `{func_name}` (not `{func_name}_wrapper`)
3. Delegates to bound method with all parameters as kwargs
4. Sets `__annotations__` for LiveKit to inspect

### Step 4: Set Metadata

After creating the wrapper, we set its metadata:

```python
wrapper.__name__ = func_name           # ✅ Tool name LiveKit uses
wrapper.__qualname__ = func_name
wrapper.__doc__ = func.__doc__ or ""  # ✅ Tool description
```

### Step 5: Register with LiveKit

```python
tool = function_tool(
    wrapper,                          # Our wrapper function
    name=func_name,                    # Explicitly set (or uses __name__)
    description=func.__doc__ or ""   # Explicitly set (or uses __doc__)
)
livekit_tools.append(tool)
```

### Step 6: LiveKit Processes the Tool

When LiveKit's `function_tool` decorator processes our wrapper:

```python
# From: /usr/local/lib/python3.11/site-packages/livekit/agents/llm/utils.py
model = function_arguments_to_pydantic_model(wrapper)
```

**What LiveKit Does:**

1. **Inspects signature**: `inspect.signature(wrapper)` → `(context, title, start_time, ...)`
2. **Gets type hints**: `wrapper.__annotations__` → `{context: RunContext, title: str, ...}`
3. **Filters out RunContext**: Excludes from input schema (LLM doesn't see this)
4. **Creates Pydantic model**: Dynamic class with fields for each parameter

**Example Pydantic Model Created:**

```python
class CreateEventArgs(BaseModel):
    title: str
    start_time: str
    duration_minutes: int = 30
    attendees: list[str] | None = None
    description: str | None = None
```

### Step 7: LLM Sees the Tool

LiveKit converts the Pydantic model to a JSON schema for the LLM:

```json
{
    "type": "function",
    "function": {
        "name": "create_event",           # From wrapper.__name__
        "description": "Create a new calendar event.\n    ...",  # From wrapper.__doc__
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Event title"
                },
                "duration_minutes": {
                    "type": "integer",
                    "default": 30
                },
                "description": {
                    "type": "string",
                    "default": null           # Optional field
                }
            },
            "required": ["title", "start_time"]  # Only required fields
        }
    }
}
```

**Note:** `description` has `"default": null` making it truly optional.

### Step 8: When LLM Calls the Tool

When the LLM decides to call the tool, it generates JSON:

```json
{
    "title": "Team Meeting",
    "start_time": "2026-01-06T17:00:00Z",
    "duration_minutes": 30,
    "attendees": [],
    "description": null  # Optional, can be omitted
}
```

LiveKit validates this against the Pydantic model, then calls our wrapper:

```python
wrapper(
    context=<RunContext instance>,  # LiveKit injects this
    title="Team Meeting",
    start_time="2026-01-06T17:00:00Z",
    duration_minutes=30,
    attendees=[],
    description=None
)
```

Our wrapper then builds kwargs and delegates:

```python
kwargs = {
    'title': "Team Meeting",
    'start_time': "2026-01-06T17:00:00Z",
    'duration_minutes': 30,
    'attendees': [],
    'description': None
}
await bound_method(context=context, **kwargs)
```

Which calls the actual tool method with `self` already bound.

## Important Implementation Details

### Why `exec()` Is Necessary

We use `exec()` to create functions with **dynamic signatures** because:

1. Python doesn't have a built-in way to create functions with dynamic signatures
2. Each tool method can have different parameters
3. We need to match signatures **exactly** for LiveKit's Pydantic validation

**Alternative approaches that DON'T work:**

- ❌ Using `**kwargs`: Pydantic creates wrong model with `kwargs` field
- ❌ Bound methods directly: Can't set `__livekit_tool_info` on bound methods
- ❌ Original methods: Has `self` parameter that LiveKit rejects

### Optional Parameters Pattern

**Correct:** `description: str | None = None`

```python
async def create_event(..., description: str | None = None) -> ...:
    pass
```

**Incorrect:** `description: str = ""`

```python
async def create_event(..., description: str = "") -> ...:
    pass
```

**Why:** In Pydantic 2.x:

- `str = ""` creates a **required** field with empty string default
- `str | None = None` creates a truly **optional** field
- LLMs often omit optional fields entirely (don't send them at all)

## Why This Is Generic and Maintainable

1. **Generic**: Works for any tool method with any signature

   - No hardcoded parameter names
   - No hardcoded parameter types
   - Handles any number of parameters

2. **Maintainable**: Single `_create_tool_wrapper` function

   - Easy to debug (add logging here)
   - Easy to modify (change behavior here)
   - All tools use same wrapping logic

3. **Clean**: Wrapper is isolated from business logic
   - Tool implementations don't need to know about LiveKit
   - Worker can change wrapping logic without touching tools

## Debugging

To add debug logging, modify `_create_tool_wrapper`:

```python
async def {func_name}({params_str}) -> Any:
    '''Wrapper for {func_name}.'''
    # Debug logging
    logger.info(f"[TOOL CALL] {func_name} started")
    for pname in {param_names[1:]:!r}:
        value = locals()[pname]
        logger.debug(f"[TOOL ARG] {pname} = {value}")

    # Build kwargs
    kwargs = {{}}
    for pname in {param_names[1:]:!r}:
        kwargs[pname] = locals()[pname]

    result = await bound_method(context=context, **kwargs)
    logger.info(f"[TOOL CALL] {func_name} completed")
    return result
```

## Summary

The wrapper pattern enables:

- ✅ Tool classes to use `self` for state management
- ✅ LiveKit to injects `RunContext` automatically
- ✅ LLMs to see clean tool schemas (no `self`, no `context`)
- ✅ Generic for any tool method
- ✅ Maintainable and debuggable
- ✅ Supports optional parameters correctly
