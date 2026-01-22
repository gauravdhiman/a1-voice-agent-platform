# Execution Control

**See parent [../../SKILL.md](../../SKILL.md) for overview and quickstart.**

## Overview

Execution control provides mechanisms to customize agent behavior including hooks (pre/post processing), guardrails (input/output validation), human-in-the-loop (pause for confirmation), and run cancellation.

## Key Concepts

- **Hooks**: Inject custom logic before/after agent runs
- **Guardrails**: Validate and filter inputs/outputs
- **Human-in-the-Loop**: Pause for human confirmation
- **Cancellation**: Stop running agents/teams/workflows
- **Tool Call Limits**: Prevent excessive tool calls

## Sub-Topics

- [Hooks](hooks.md) - Pre/post execution hooks for validation, logging, telemetry
- [Guardrails](guardrails.md) - Input/output validation and security
- [Human-in-the-Loop](human-in-the-loop.md) - Pause for confirmation on sensitive operations
- [Cancellation](cancellation.md) - Cancel running agent/team/workflow executions
- [Tool Call Limits](limits.md) - Prevent excessive tool calls

## Execution Order

When an agent runs with multiple execution control mechanisms:

```
1. Pre-hooks execute (input validation, enrichment)
2. Guardrails check input (moderation, PII detection)
3. Agent processes and decides to call tools
4. HITL pauses for confirmation (if configured)
5. Tool executes or user denies
6. Agent continues with result
7. Post-hooks execute (logging, notifications)
8. Output returned
```

## Combined Patterns

```python
from agno.hooks import hook
from agno.tools import tool
from agno.guardrails import OpenAIModeration

# Hook for input validation
@hook()
def validate_input(run_input, agent):
    if not run_input.message:
        raise ValueError("Empty input")
    return run_input

# Tool with confirmation
@tool(stop_before_execution=True)
def sensitive_operation(data: str) -> str:
    """Perform sensitive operation."""
    return f"Processed: {data}"

agent = Agent(
    name="Controlled Agent",
    pre_hooks=[validate_input],
    guardrails=[OpenAIModeration()],
    tools=[sensitive_operation],
)
```

## Best Practices

1. **Validate early** - Use pre-hooks for input validation
2. **Use guardrails** - For security and compliance
3. **HITL for sensitive actions** - Require confirmation for destructive operations
4. **Keep hooks lightweight** - Don't block execution with slow operations
5. **Handle errors** - Catch exceptions to prevent agent failure
6. **Combine mechanisms** - Use multiple controls for layered protection
7. **Monitor performance** - Track execution control impact on latency
8. **Set timeouts** - Use cancellation for runaway tasks

## Online Resources

- [Hooks Documentation](https://docs.agno.com/execution-control/hooks)
- [Guardrails Documentation](https://docs.agno.com/execution-control/guardrails)
- [Human-in-the-Loop Documentation](https://docs.agno.com/execution-control/human-in-the-loop)
- [Cancellation Documentation](https://docs.agno.com/execution-control/cancellation)
