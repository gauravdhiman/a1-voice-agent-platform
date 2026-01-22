# Hooks

**See parent [../execution-control/overview.md](../execution-control/overview.md) for execution control overview.**

## Overview

Hooks allow you to inject custom logic before and after agent runs. They're useful for input validation, logging, telemetry, and context enrichment.

## Pre-Hooks

Execute before agent run:

```python
from agno.hooks import hook
from agno.agent import Agent, RunInput

@hook()
def validate_input(run_input: RunInput, agent: Agent):
    """Validate input before agent execution."""
    if not run_input.message:
        raise ValueError("Input message cannot be empty")

    return run_input

agent = Agent(
    name="Validated Agent",
    pre_hooks=[validate_input],
)
```

## Post-Hooks

Execute after agent run:

```python
from agno.hooks import hook
from agno.agent import Agent, RunOutput

@hook()
def log_output(run_output: RunOutput, agent: Agent):
    """Log agent output."""
    print(f"Agent {agent.name} completed: {run_output.content}")

agent = Agent(
    name="Logging Agent",
    post_hooks=[log_output],
)
```

## Hooks with Parameters

```python
from agno.hooks import hook
from agno.run import RunContext

@hook()
def enrich_context(run_context: RunContext, agent: Agent):
    """Enrich run context with data."""
    if not run_context.metadata:
        run_context.metadata = {}

    run_context.metadata["timestamp"] = datetime.now().isoformat()
    run_context.metadata["user_agent"] = run_context.metadata.get("user_agent", "unknown")

agent = Agent(
    name="Enriched Agent",
    pre_hooks=[enrich_context],
)
```

## Hooks in AgentOS

Run hooks as background tasks:

```python
from agno.os import AgentOS

@hook(run_in_background=True)
async def send_notification(run_output, agent):
    """Send notification after run completes."""
    await send_slack_message(run_output.content)

agent = Agent(
    name="Notification Agent",
    post_hooks=[send_notification],
)

agent_os = AgentOS(
    agents=[agent],
    run_hooks_in_background=True,  # All hooks in background
)
```

## Hooks with Memory

```python
from agno.hooks import hook
from agno.run import RunContext
from agno.memory import MemoryManager

@hook()
def track_user_activity(run_context: RunContext, agent: Agent):
    """Track user activity in memory."""
    if not run_context.metadata:
        run_context.metadata = {}

    activity = {
        "timestamp": datetime.now().isoformat(),
        "action": "agent_run",
        "user_id": run_context.user_id,
    }

    # Store in memory
    # (implementation depends on your memory setup)
    pass

memory_manager = MemoryManager(model=..., db=db)

agent = Agent(
    name="Tracking Agent",
    pre_hooks=[track_user_activity],
    memory_manager=memory_manager,
)
```

## Hook Events

**Pre-hook events:**
- `PreHookStarted` - Pre-hook execution started
- `PreHookCompleted` - Pre-hook execution completed

**Post-hook events:**
- `PostHookStarted` - Post-hook execution started
- `PostHookCompleted` - Post-hook execution completed

```python
from agno.hooks import hook

@hook()
def my_hook(run_context, agent):
    """Access hook-specific events."""
    # Log or process events
    print(f"Hook executed for run: {run_context.run_id}")

agent = Agent(pre_hooks=[my_hook])
```

## Best Practices

1. **Keep hooks lightweight** - Don't block execution with slow operations
2. **Use background hooks** - For non-critical tasks (notifications, logging)
3. **Validate early** - Use pre-hooks for input validation
4. **Handle hook errors** - Catch exceptions to prevent agent failure
5. **Monitor hook execution** - Log hook performance and failures

## See Also

- [Guardrails](guardrails.md) - Input/output validation
- [Human-in-the-Loop](human-in-the-loop.md) - Pause for confirmation
- [Cancellation](cancellation.md) - Run cancellation
- [Online Docs](https://docs.agno.com/execution-control/hooks) - Official hooks documentation
