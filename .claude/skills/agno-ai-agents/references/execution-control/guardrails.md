# Guardrails

**See parent [../execution-control/overview.md](../execution-control/overview.md) for execution control overview.**

## Overview

Guardrails validate and filter agent inputs and outputs to ensure security, compliance, and quality.

## OpenAI Moderation

```python
from agno.guardrails import OpenAIModeration

agent = Agent(
    name="Moderated Agent",
    guardrails=[OpenAIModeration()],
)
```

**Detects:** Hate speech, violence, self-harm, sexual content

## PII Detection

```python
from agno.guardrails import PIIDetection

agent = Agent(
    name="PII Protected Agent",
    guardrails=[PIIDetection()],
)
```

**Detects:** Email addresses, phone numbers, SSN, credit card numbers

## Prompt Injection Detection

```python
from agno.guardrails import PromptInjectionDetection

agent = Agent(
    name="Secure Agent",
    guardrails=[PromptInjectionDetection()],
)
```

**Detects:** Jailbreak attempts, system prompt overrides, malicious prompts

## Custom Guardrails

```python
from agno.guardrails import Guardrail
from agno.agent import Agent, RunInput

class CustomGuardrail(Guardrail):
    """Custom guardrail implementation."""

    def run(self, run_input: RunInput, agent: Agent) -> RunInput:
        """Validate and potentially modify input."""
        # Your validation logic here
        if "forbidden_word" in run_input.message:
            raise ValueError("Forbidden content detected")

        # Optionally modify input
        run_input.message = run_input.message.strip()
        return run_input

agent = Agent(
    name="Guarded Agent",
    guardrails=[CustomGuardrail()],
)
```

## Guardrails on Teams

```python
from agno.team import Team

team = Team(
    name="Secure Team",
    members=[agent1, agent2],
    guardrails=[OpenAIModeration(), PIIDetection()],
)
```

## Best Practices

1. **Layer guardrails** - Use multiple guardrails for comprehensive protection
2. **Validate early** - Check inputs before agent processing
3. **Combine guardrails** - Different guardrails for different concerns
4. **Monitor violations** - Log when guardrails trigger
5. **Customize for domain** - Create guardrails specific to your use case

## See Also

- [Hooks](hooks.md) - Pre/post execution hooks
- [Human-in-the-Loop](human-in-the-loop.md) - Pause for confirmation
- [Cancellation](cancellation.md) - Run cancellation
- [Online Docs](https://docs.agno.com/execution-control/guardrails) - Official guardrails documentation
