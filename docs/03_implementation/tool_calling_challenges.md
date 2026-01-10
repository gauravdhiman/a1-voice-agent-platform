# Tool Calling Challenges & Solutions

This document describes the challenges we faced with LiveKit tool calling and the solutions we implemented.

## Background

When integrating AI voice agents with LiveKit and LLMs (like Gemini Realtime), we encountered several challenges with tool calling. This document explains what went wrong, how we debugged it, and the solutions we implemented.

## Challenge 1: Tool Methods with `self` Parameter

### Problem

Tool methods in our architecture have a `self` parameter (for accessing instance state like configuration and OAuth tokens):

```python
class GoogleCalendarTool(BaseTool):
    async def check_availability(
        self,                    # ❌ Problem: bound method
        context: RunContext,     # LiveKit injects this
        start_time: str,
        duration_minutes: int = 30
    ) -> dict[str, Any]:
        """Check calendar availability."""
        # Uses self.config and self.sensitive_config
        pass
```

LiveKit's `@function_tool` decorator cannot accept bound methods because:

1. It uses `inspect.signature()` to extract parameters
2. Bound methods have `self` as first parameter
3. LiveKit tries to call the function, but `self` is not available

### Error Encountered

```
Error: Cannot wrap bound method with @function_tool decorator
```

### Attempted Solutions

**Attempt 1: Pass bound method directly**

```python
bound_method = getattr(tool_instance, 'check_availability')
tool = function_tool(bound_method)  # ❌ Failed
```

**Result**: Error - cannot wrap bound method

**Attempt 2: Use `inspect.unwrap()` to get original function**

```python
import inspect
original_func = inspect.unwrap(bound_method)
tool = function_tool(original_func)  # ❌ Failed
```

**Result**: Original function still has `self` parameter

### Solution: Dynamic Wrapper Creation

We create a standalone wrapper function with the same signature (excluding `self`), which delegates to the bound method:

```python
def _create_tool_wrapper(bound_method: Any, func_name: str, param_names: list[str], type_hints: dict) -> Any:
    """Create wrapper function for a tool method."""

    # Build parameter definitions
    params_def = ["context: RunContext"]
    for param_name in param_names[1:]:  # Skip 'self'
        param_type = type_hints.get(param_name, Any)
        params_def.append(f"{param_name}: {param_type}")

    params_str = ", ".join(params_def)

    # Create wrapper dynamically using exec()
    wrapper_code = f"""
async def {func_name}({params_str}) -> Any:
    '''Wrapper for {func_name}.'''
    kwargs = {{}}
    for pname in {param_names[1:]:!r}:
        kwargs[pname] = locals()[pname]
    return await bound_method(context=context, **kwargs)
"""

    # Execute code to create function
    namespace = {'Any': Any, 'RunContext': RunContext, 'bound_method': bound_method}
    local_scope = {}
    exec(wrapper_code, namespace, local_scope)
    wrapper = local_scope[func_name]

    # Set metadata
    wrapper.__annotations__ = type_hints
    wrapper.__name__ = func_name
    wrapper.__qualname__ = func_name
    wrapper.__doc__ = original_func.__doc__

    return wrapper
```

**Benefits**:

- ✅ Exact signature matches (excluding `self`)
- ✅ Type hints preserved
- ✅ Delegates to bound method with all parameters
- ✅ Works with any tool method

## Challenge 2: Pydantic Validation Errors

### Problem

When LLM tried to call tools, we got Pydantic validation errors:

```
pydantic_core._pydantic_core.ValidationError: kwargs Field required
```

Root cause: Date string `"2026-01-06T17:00:00Z"` being treated as dictionary key instead of value.

### Investigation

We created a test file `worker/test_livekit_wrapping.py` with 6 different wrapper approaches:

| Test   | Approach                           | Result         | Why                                                         |
| ------ | ---------------------------------- | -------------- | ----------------------------------------------------------- |
| TEST 1 | `**kwargs` + annotations           | ❌ Failed      | Pydantic creates `['kwargs']` instead of actual field names |
| TEST 2 | Only context param                 | ❌ Failed      | Missing other parameters                                    |
| TEST 3 | Explicit params matching           | ✅ **SUCCESS** | Creates correct Pydantic model with actual field names      |
| TEST 4 | Dynamic wrapper using exec         | ✅ **SUCCESS** | Creates correct Pydantic model                              |
| TEST 5 | `inspect.unwrap()` on bound method | ❌ Failed      | Can't set `__livekit_tool_info` on bound methods            |
| TEST 6 | Original method directly           | ❌ Failed      | Has `self` parameter that LiveKit rejects                   |

### Key Discovery

**Must use explicit parameters, not `**kwargs`\*\*:

**INCORRECT** (creates wrong Pydantic model):

```python
async def check_availability(context: RunContext, **kwargs) -> Any:
    """Wrapper for check_availability."""
    pass
```

Pydantic creates:

```python
class CheckAvailabilityArgs(BaseModel):
    context: RunContext
    kwargs: dict[str, Any]  # ❌ Wrong - LLM can't use individual params
```

**CORRECT** (creates correct Pydantic model):

```python
async def check_availability(
    context: RunContext,
    start_time: str,
    duration_minutes: int = 30
) -> Any:
    """Wrapper for check_availability."""
    pass
```

Pydantic creates:

```python
class CheckAvailabilityArgs(BaseModel):
    context: RunContext
    start_time: str
    duration_minutes: int = 30  # ✅ Correct - LLM can use individual params
```

## Challenge 3: Optional Parameters in Pydantic 2.x

### Problem

LLM often omits optional parameters entirely. We got validation errors when agent called `create_event` without description:

```
Error: description Field required
```

### Investigation

We defined the parameter as:

```python
async def create_event(
    self,
    context: RunContext,
    title: str,
    description: str = ""  # ❌ WRONG
):
    pass
```

In Pydantic 2.x:

- `str = ""` creates a **required** field with empty string default
- LLM omits optional fields (doesn't send them at all)
- Pydantic validation fails because field is required but not provided

### Solution

Use `type | None = None` for truly optional fields:

```python
async def create_event(
    self,
    context: RunContext,
    title: str,
    description: str | None = None  # ✅ CORRECT
):
    pass
```

In Pydantic 2.x:

- `str | None = None` creates a truly **optional** field
- LLM can omit the field entirely
- Pydantic validates successfully when field is missing

**Pydantic Models Created**:

**INCORRECT** (`str = ""`):

```python
class CreateEventArgs(BaseModel):
    title: str
    description: str  # ❌ Required field
```

**CORRECT** (`str | None = None`):

```python
class CreateEventArgs(BaseModel):
    title: str
    description: Optional[str] = None  # ✅ Optional field
```

## Challenge 4: Wrapper Naming and Metadata

### Problem

Initially we named wrapper incorrectly and didn't set proper metadata:

```python
# INCORRECT
wrapper.__name__ = f"{func_name}_wrapper"  # ❌ Wrong name
```

LiveKit uses `__name__` as the tool name, so the LLM saw `check_availability_wrapper` instead of `check_availability`.

### Solution

Name the wrapper correctly and set all metadata:

```python
wrapper.__name__ = func_name                    # Tool name
wrapper.__qualname__ = func_name                # Qualified name
wrapper.__doc__ = original_func.__doc__ or ""  # Tool description
wrapper.__annotations__ = type_hints              # Type hints
```

## Challenge 5: Dynamic Function Signatures

### Problem

Each tool method has different parameters. We couldn't use a fixed template:

```python
# Tool 1: check_availability
async def check_availability(context, start_time: str, duration_minutes: int)

# Tool 2: create_event
async def create_event(context, title: str, start_time: str, description: str | None)

# Tool 3: list_events
async def list_events(context, time_min: str, time_max: str, max_results: int = 10)
```

### Solution

Use `exec()` to create functions with dynamic signatures:

```python
# Build signature dynamically
params_def = ["context: RunContext"]
for param_name in param_names[1:]:
    param_type = type_hints.get(param_name, Any)
    params_def.append(f"{param_name}: {param_type}")

params_str = ", ".join(params_def)

# Create function using exec()
wrapper_code = f"""
async def {func_name}({params_str}) -> Any:
    '''Wrapper for {func_name}.'''
    kwargs = {{}}
    for pname in {param_names[1:]:!r}:
        kwargs[pname] = locals()[pname]
    return await bound_method(context=context, **kwargs)
"""

# Execute code
namespace = {'Any': Any, 'RunContext': RunContext, 'bound_method': bound_method}
local_scope = {}
exec(wrapper_code, namespace, local_scope)
wrapper = local_scope[func_name]
```

This is the only reliable way to create functions with dynamic signatures in Python.

## Lessons Learned

### 1. Pydantic Model Creation Matters

LiveKit converts wrapper functions to Pydantic models. The model structure depends on wrapper signature:

- **Explicit parameters**: Individual fields for each parameter
- **`**kwargs`**: Single `kwargs` field (type: dict)
- **Wrong optional definition**: Required field instead of optional

### 2. Type Hints Are Critical

LiveKit reads `__annotations__` to create Pydantic model. Must preserve type hints from original function.

### 3. Naming Matters

LLM sees the wrapper's `__name__` as tool name. Must match original method name.

### 4. `exec()` Is Sometimes Necessary

Python doesn't have a built-in way to create functions with dynamic signatures. `exec()` is the only reliable solution.

## Testing Strategy

We used a comprehensive test file to validate approaches:

```python
# worker/test_livekit_wrapping.py

# 6 different wrapper approaches tested
# Each approach documented with result and explanation
```

**Key insights from testing**:

- TEST 3 and TEST 4 work (explicit parameters)
- TEST 4 (dynamic wrapper using exec) is our production implementation
- Other approaches fail for various reasons

## Implementation in Production

The final implementation in `worker/src/worker.py` uses:

1. **Tool registry** to discover tool implementations
2. **Dynamic wrapper creation** for each tool method
3. **Explicit parameters** in wrapper signature
4. **Optional parameter pattern** (`type | None = None`)
5. **Proper metadata** set on wrapper

**Code flow**:

```python
# 1. Get tool class from registry
tool_class = livekit_tool_registry.get_tool_class(tool_name)

# 2. Instantiate tool with config
tool_instance = tool_class(config, sensitive_config)

# 3. Get functions from tool
functions = [getattr(tool_instance, name) for name in dir(tool_instance) if callable(...)]

# 4. Wrap each function
for func in functions:
    func_name = func.__name__
    bound_method = getattr(tool_instance, func_name)

    # Extract parameters and type hints
    sig = inspect.signature(func)
    param_names = [name for name in sig.parameters.keys() if name != 'self']
    type_hints = {k: v for k, v in func.__annotations__.items() if k != 'self'}

    # Create wrapper
    wrapper = _create_tool_wrapper(bound_method, func_name, param_names, type_hints)

    # Register with LiveKit
    tool = function_tool(wrapper, name=func_name, description=func.__doc__)
    livekit_tools.append(tool)
```

## Related Documentation

- [LiveKit Tool Wrapping Architecture](livekit_tool_wrapping.md) - Detailed wrapper implementation
- [Worker README](../../worker/README.md) - Worker service documentation
- [Shared Module README](../../shared/README.md) - Shared code architecture
- [Worker Test File](../../worker/test_livekit_wrapping.py) - Test approaches and results

## Summary

We successfully solved all tool calling challenges by:

1. ✅ Creating dynamic wrappers with exact parameter signatures
2. ✅ Using explicit parameters (not `**kwargs`) for correct Pydantic models
3. ✅ Using `type | None = None` for truly optional fields
4. ✅ Setting proper metadata on wrappers
5. ✅ Using `exec()` for dynamic function creation

The tool calling system now works correctly with:

- Any tool method signature
- Proper Pydantic validation
- Optional parameters that LLMs can omit
- Clean tool names for LLM understanding
