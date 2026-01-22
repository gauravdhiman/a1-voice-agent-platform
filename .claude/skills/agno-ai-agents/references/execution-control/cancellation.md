# Run Cancellation

**See parent [../execution-control/overview.md](../execution-control/overview.md) for execution control overview.**

## Overview

Run cancellation allows you to stop agent, team, or workflow executions that are running too long or need to be terminated.

## Cancel Agent Run

```python
from agno.agent import Agent

agent = Agent(name="My Agent")

# Start run
run_response = agent.run("Long running task...")
print(f"Run ID: {run_response.run_id}")

# Cancel later
agent.cancel_run(run_id=run_response.run_id)
```

## Cancel Team Run

```python
from agno.team import Team

team = Team(members=[agent1, agent2])

# Start run
run_response = team.run("Research topic...")
print(f"Run ID: {run_response.run_id}")

# Cancel later
team.cancel_run(run_id=run_response.run_id)
```

## Cancel Workflow Run

```python
from agno.workflow import Workflow

workflow = Workflow(steps=[step1, step2])

# Start run
run_response = workflow.run("Process data...")
print(f"Run ID: {run_response.run_id}")

# Cancel later
workflow.cancel_run(run_id=run_response.run_id)
```

## Async Cancellation

```python
import asyncio

async def main():
    agent = Agent(name="Async Agent")

    # Start run in background
    task = asyncio.create_task(agent.arun("Long task..."))

    # Cancel after delay
    await asyncio.sleep(1)
    task.cancel()

asyncio.run(main())
```

## Best Practices

1. **Set timeouts** - Use cancellation for runaway tasks
2. **Track run IDs** - Save run IDs for cancellation
3. **Handle cleanup** - Ensure resources are released on cancellation
4. **Monitor long runs** - Identify patterns of long-running operations
5. **Graceful shutdown** - Use cancellation for clean shutdown

## See Also

- [Hooks](hooks.md) - Pre/post execution hooks
- [Guardrails](guardrails.md) - Input/output validation
- [Human-in-the-Loop](human-in-the-loop.md) - Pause for confirmation
- [Online Docs](https://docs.agno.com/execution-control/cancellation) - Official cancellation documentation
