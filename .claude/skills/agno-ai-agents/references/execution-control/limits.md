# Tool Call Limits

**See parent [../execution-control/overview.md](../execution-control/overview.md) for execution control overview.**

## Overview

Tool call limits prevent agents from making excessive tool calls, which can cause runaway behavior and unexpected costs.

## Limit Number of Tool Calls

```python
agent = Agent(
    name="Limited Agent",
    tool_call_limit=5,  # Max 5 tool calls per run
)
```

## Reset Tool Call Count

```python
# Run with tool calls
response1 = agent.run("Task 1")

# Reset counter
agent.reset_tool_call_count()

# Run with fresh tool call count
response2 = agent.run("Task 2")
```

## Best Practices

1. **Set reasonable limits** - Balance between functionality and safety
2. **Monitor tool usage** - Track which tools are called most frequently
3. **Adjust per agent** - Different agents may need different limits
4. **Reset appropriately** - Reset between independent tasks
5. **Log limit violations** - Track when agents hit limits

## See Also

- [Hooks](hooks.md) - Pre/post execution hooks
- [Guardrails](guardrails.md) - Input/output validation
- [Cancellation](cancellation.md) - Run cancellation
- [Human-in-the-Loop](human-in-the-loop.md) - Pause for confirmation
