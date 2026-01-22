# Features - Online Resources

**See parent [../../SKILL.md](../../SKILL.md) for overview and quickstart.**

## Overview

This directory references Agno's advanced features documentation online. These features extend the core agent/team/workflow functionality with production-ready capabilities.

## Key Features

### Evals (Evaluation)
- **What**: Measure agent quality across multiple dimensions
- **URL**: [Evals Overview](https://docs.agno.com/features/evals/overview)
- **Sub-topics**:
  - [Accuracy](https://docs.agno.com/features/evals/accuracy/overview) - LLM-as-a-judge correctness checks
  - [Agent as Judge](https://docs.agno.com/features/evals/agent-as-judge/overview) - Custom quality criteria with scoring
  - [Performance](https://docs.agno.com/features/evals/performance/overview) - Latency and memory measurements
  - [Reliability](https://docs.agno.com/features/evals/reliability/overview) - Tool call and error handling tests

### Reasoning
- **What**: Advanced reasoning capabilities for complex problem solving
- **URL**: [Reasoning Documentation](https://docs.agno.com/features/reasoning)

### Multimodal
- **What**: Process and generate text, images, audio, and video
- **URL**: [Multimodal Documentation](https://docs.agno.com/features/multimodal)

### Tracing
- **What**: Visualize and analyze agent execution flows
- **URL**: [Tracing Documentation](https://docs.agno.com/features/tracing)

### Custom Logging
- **What**: Custom logging for debugging and monitoring
- **URL**: [Custom Logging](https://docs.agno.com/features/custom-logging)

### Telemetry
- **What**: Collect and analyze agent performance metrics
- **URL**: [Telemetry](https://docs.agno.com/features/telemetry)

### Skills (Experimental)
- **What**: Reusable agent skills and capabilities
- **URL**: [Skills Documentation](https://docs.agno.com/features/skills)

## When to Use Each Feature

| Feature | Use Case |
|---------|----------|
| **Evals** | Testing agent quality before deployment |
| **Reasoning** | Complex multi-step problem solving |
| **Multimodal** | Processing images, audio, or video |
| **Tracing** | Debugging agent execution flows |
| **Custom Logging** | Application-specific logging needs |
| **Telemetry** | Production monitoring and analytics |
| **Skills** | Sharing reusable agent capabilities |

## Quick Examples

### Basic Eval

```python
from agno.eval.accuracy import AccuracyEval

evaluation = AccuracyEval(
    model=OpenAIResponses(id="gpt-4"),
    agent=Agent(model=OpenAIResponses(id="gpt-4")),
    input="What is 10*5?",
    expected_output="50",
)

result = evaluation.run()
```

### Multimodal Agent

```python
agent = Agent(
    name="Multimodal Agent",
    model=OpenAIResponses(id="gpt-4-vision"),
    instructions=[AgentInstructions(multimodal=True)],
)
```

## Best Practices

1. **Evals**: Start with accuracy tests, then add performance/reliability
2. **Reasoning**: Use for complex tasks requiring step-by-step logic
3. **Multimodal**: Combine text with images/audio when appropriate
4. **Tracing**: Enable during development and debugging
5. **Custom Logging**: Keep it lightweight for production
6. **Telemetry**: Monitor key metrics in production

## See Also

- [Execution Control](../execution-control/overview.md) - Hooks, guardrails, HITL, cancellation
- [Integrations](../integrations/online-resources.md) - Model providers, databases, vector DBs
- [Cookbook](../cookbook/online-resources.md) - Ready-to-use examples
