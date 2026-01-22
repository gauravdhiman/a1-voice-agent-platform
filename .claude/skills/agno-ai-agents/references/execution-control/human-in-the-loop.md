# Human-in-the-Loop (HITL)

**See parent [../execution-control/overview.md](../execution-control/overview.md) for execution control overview.**

## Overview

Human-in-the-loop (HITL) allows agents to pause and request human confirmation for sensitive operations.

## Stop Before Tool Execution

Require confirmation before sensitive tool:

```python
from agno.tools import tool

@tool(stop_before_execution=True)
def delete_user(user_id: str) -> str:
    """Delete user account - requires confirmation."""
    return f"User {user_id} deleted"

agent = Agent(
    name="HITL Agent",
    tools=[delete_user],
)
```

**Execution flow:**
1. Agent decides to call `delete_user`
2. Execution pauses
3. User confirms or denies
4. If confirmed, tool executes
5. Agent continues with result

## Stop Before Execution with Custom Message

```python
from agno.tools import tool

@tool(
    stop_before_execution=True,
    execution_message="This will permanently delete data. Continue?",
)
def delete_data(dataset_id: str) -> str:
    """Delete dataset."""
    return f"Dataset {dataset_id} deleted"
```

## Confirm Before Run

```python
from agno.execution_control import ConfirmBeforeRun

agent = Agent(
    name="Confirmation Agent",
    confirm_before_run=True,  # Confirm before each run
    confirmation_message="Do you want to proceed?",
)
```

## External Tool Execution

Pause and return control to external system:

```python
from agno.tools import tool
from agno.execution_control import ExternalExecution

@tool(external_execution=True)
def get_approval(amount: float) -> dict:
    """Get external approval for amount."""
    return {
        "requires_approval": True,
        "amount": amount,
        "status": "pending_approval",
    }

agent = Agent(
    name="Approval Agent",
    tools=[get_approval],
)
```

**Execution flow:**
1. Agent calls `get_approval`
2. Execution pauses and returns control
3. External system processes approval
4. Resume with approval result

## Best Practices

1. **HITL for sensitive actions** - Require confirmation for destructive operations
2. **Clear messages** - Use descriptive confirmation messages
3. **External execution** - For complex approval workflows
4. **Minimize disruptions** - Don't overuse HITL for routine tasks
5. **Track decisions** - Log approval/rejection decisions

## See Also

- [Hooks](hooks.md) - Pre/post execution hooks
- [Guardrails](guardrails.md) - Input/output validation
- [Cancellation](cancellation.md) - Run cancellation
- [Online Docs](https://docs.agno.com/execution-control/human-in-the-loop) - Official HITL documentation
