---
name: agno-ai-agents
description: Build, run, and manage multi-agent AI systems using the Agno framework. Use when creating AI agents, teams, workflows with memory, knowledge, tools, execution control (hooks, guardrails, human-in-the-loop), evaluations, multimodal capabilities, reasoning agents, or deploying via AgentOS. Triggered by requests for - "create an AI agent", "build multi-agent system", "add tools to agent", "implement RAG/knowledge base", "add memory to agent", "create workflow", "deploy agent with FastAPI", "agent evaluation", "voice/image/multimodal agent"
---

# Agno AI Agents Framework

## Overview

Agno is a framework for building multi-agent AI systems with memory, knowledge, tools, and production deployment.

**Core components:**
- **Agents** - LLM-driven programs that use tools in a loop
- **Teams** - Groups of agents that collaborate on complex tasks
- **Workflows** - Orchestration pipelines with sequential, parallel, conditional steps
- **AgentOS** - Production service layer with FastAPI, authentication, interfaces

## Quick Start

Create your first agent (~20 lines):

```python
from agno.agent import Agent
from agno.models.openai import OpenAIResponses

agent = Agent(
    name="My Agent",
    model=OpenAIResponses(id="gpt-4o"),
    instructions="You are a helpful assistant",
    markdown=True,
)

response = agent.run("Hello!")
print(response.content)
```

**Run agent with state persistence:**

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS

agent = Agent(
    name="My Agent",
    model=OpenAIResponses(id="gpt-4o"),
    db=SqliteDb(db_file="agent.db"),
    add_history_to_context=True,
    markdown=True,
)

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()
# fastapi dev agent.py
```

## Core Concepts

### When to Use Each Component

| Need                    | Use          |
| ------------------------ | ------------- |
| Simple autonomous task   | Agent         |
| Multiple specialists     | Team          |
| Repeatable pipeline     | Workflow       |
| Production deployment   | AgentOS        |

### Agent Architecture

Agent execution loop:
1. Build context (system, user, history, memories, session state)
2. Send to model
3. Model responds with message or tool call
4. If tool call, execute and return result to model
5. Repeat until final message
6. Return response

## Core Workflows

### Building Agents

```python
from agno.agent import Agent
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    name="News Agent",
    model=OpenAIResponses(id="gpt-4o"),
    role="Get trending tech news",
    tools=[HackerNewsTools()],
    instructions="Be concise and helpful",
)
```

**Key agent capabilities:**
- **Tools** - External actions (120+ pre-built toolkits available)
- **Knowledge** - Agentic RAG with searchable documents
- **Memory** - User preferences across conversations
- **State** - Session-scoped data storage

See [references/basics/agents.md](references/basics/agents.md) for detailed agent patterns.

### Building Teams

```python
from agno.team import Team

team = Team(
    name="Research Team",
    members=[researcher, writer],
    instructions="Synthesize research into articles",
)
```

**Team patterns:**
- **Supervisor** (default) - Delegation with synthesis
- **Router** - Route to specialists without synthesis
- **Broadcast** - Parallel research

See [references/basics/teams.md](references/basics/teams.md) for team coordination patterns.

### Building Workflows

```python
from agno.workflow import Workflow, Step

workflow = Workflow(
    name="Content Pipeline",
    steps=[Step(name="research", agent=researcher), Step(name="write", agent=writer)],
)
```

**Workflow capabilities:**
- Sequential steps
- Parallel execution
- Conditional branching
- Loops
- Conversational interactions

See [references/basics/workflows.md](references/basics/workflows.md) for workflow patterns.

## Common Capabilities

### Adding Tools

**Pre-built toolkits:**

```python
from agno.tools.yfinance import YFinanceTools

agent = Agent(tools=[YFinanceTools()])
```

**Custom tools:**

```python
from agno.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get weather for city."""
    return f"Weather in {city} is sunny."

agent = Agent(tools=[get_weather])
```

See [references/tools/overview.md](references/tools/overview.md) for tool creation and usage patterns.

### Adding Knowledge (RAG)

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType

knowledge = Knowledge(
    vector_db=LanceDb(uri="tmp/lancedb", table_name="docs", search_type=SearchType.hybrid)
)
knowledge.add_content(url="https://example.com/doc.pdf")

agent = Agent(knowledge=knowledge)
```

See [references/context/knowledge.md](references/context/knowledge.md) for RAG patterns, chunking strategies, and retrieval methods.

### Adding Memory

```python
from agno.memory import MemoryManager

memory_manager = MemoryManager(model=OpenAIResponses(id="gpt-4o"), db=db)

agent = Agent(
    memory_manager=memory_manager,
    enable_agentic_memory=True,
)
```

See [references/context/memory.md](references/context/memory.md) for memory patterns.

### Execution Control

**Hooks** - Pre/post processing:

```python
from agno.hooks import hook

@hook()
def validate_input(run_input, agent):
    if not run_input:
        raise ValueError("Empty input")

agent = Agent(pre_hooks=[validate_input])
```

**Guardrails** - Input/output validation:

```python
from agno.guardrails import OpenAIModeration

agent = Agent(guardrails=[OpenAIModeration()])
```

**Human-in-the-loop** - Pause for confirmation:

```python
from agno.tools import tool

@tool(stop_before_execution=True)
def delete_user(user_id: str):
    """Delete user account."""
    return f"Deleted {user_id}"
```

See [references/execution-control/overview.md](references/execution-control/overview.md) for complete execution control patterns.

### Streaming

**Agent streaming:**

```python
for event in agent.run("Tell me a story", stream=True):
    if event.event == RunEvent.run_content:
        print(event.content, end="", flush=True)
```

**Stream all events (tool calls, reasoning, memory):**

```python
for event in agent.run("...", stream=True, stream_events=True):
    print(f"Event: {event.event}")
```

## Advanced Features

### Evaluations

Test agent quality with accuracy, performance, and reliability metrics.

```python
from agno.evals import RunEvaluator

evaluator = RunEvaluator(
    agent=agent,
    model=OpenAIResponses(id="gpt-4o")
)
result = evaluator.run(
    messages=["What is Python?"],
    expected_answers=["Python is a programming language"]
)
```

See [references/features/online-resources.md](references/features/online-resources.md) for evaluation documentation and patterns.

### Multimodal

Agents can handle images, audio, video, and files.

```python
from agno.media import Image

agent.run("Describe this image", images=[Image(url="https://example.com/image.jpg")])
```

See [references/features/online-resources.md](references/features/online-resources.md) for multimodal documentation and patterns.

### Reasoning

Use reasoning models (o1, o3, DeepSeek-R1, Groq) for complex tasks.

```python
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="o3-mini", reasoning_effort="medium")
)
```

See [references/features/online-resources.md](references/features/online-resources.md) for reasoning documentation and patterns.

### AgentOS - Production Deployment

Deploy agents with FastAPI, authentication, and interfaces.

```python
from agno.os import AgentOS

agent_os = AgentOS(agents=[agent, team, workflow])
app = agent_os.get_app()

# fastapi dev agent.py
```

**AgentOS provides:**
- REST API endpoints (compatible with SSE streaming)
- Session management
- Knowledge base management
- Memory operations
- Tracing and observability
- Multi-interface support (AG-UI, Slack, WhatsApp, A2A)
- RBAC and authentication

See [references/agent-os/overview.md](references/agent-os/overview.md) for AgentOS deployment patterns.

## Reference Guides

### Core Concepts

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| Agent patterns and capabilities       | [references/basics/agents.md](references/basics/agents.md) |
| Team coordination patterns       | [references/basics/teams.md](references/basics/teams.md) |
| Workflow orchestration patterns | [references/basics/workflows.md](references/basics/workflows.md) |
| Tool creation and usage       | [references/tools/overview.md](references/tools/overview.md) |

### Context Management

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| Knowledge overview and setup | [references/context/knowledge/overview.md](references/context/knowledge/overview.md) |
| Knowledge search types | [references/context/knowledge/search-types.md](references/context/knowledge/search-types.md) |
| Adding content to knowledge | [references/context/knowledge/adding-content.md](references/context/knowledge/adding-content.md) |
| Knowledge usage patterns (Agentic vs Traditional RAG) | [references/context/knowledge/usage-patterns.md](references/context/knowledge/usage-patterns.md) |
| Knowledge filters | [references/context/knowledge/filters.md](references/context/knowledge/filters.md) |
| Knowledge chunking strategies | [references/context/knowledge/chunking.md](references/context/knowledge/chunking.md) |
| Knowledge readers (PDF, web, etc.) | [references/context/knowledge/readers.md](references/context/knowledge/readers.md) |
| Knowledge vector databases (LanceDB, PgVector, Qdrant, Pinecone) | [references/context/knowledge/vector-databases.md](references/context/knowledge/vector-databases.md) |
| Advanced knowledge features (reasoning, reranking, distributed RAG) | [references/context/knowledge/advanced.md](references/context/knowledge/advanced.md) |
| Knowledge tools components | [references/context/knowledge/knowledge-tools.md](references/context/knowledge/knowledge-tools.md) |
| Memory systems and patterns       | [references/context/memory.md](references/context/memory.md) |
| Session state management      | [references/context/state.md](references/context/state.md) |
| History management            | [references/context/history.md](references/context/history.md) |

### Execution Control

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| Execution control overview | [references/execution-control/overview.md](references/execution-control/overview.md) |
| Hooks (pre/post processing) | [references/execution-control/hooks.md](references/execution-control/hooks.md) |
| Guardrails and validation  | [references/execution-control/guardrails.md](references/execution-control/guardrails.md) |
| Human-in-the-loop          | [references/execution-control/human-in-the-loop.md](references/execution-control/human-in-the-loop.md) |
| Run cancellation             | [references/execution-control/cancellation.md](references/execution-control/cancellation.md) |
| Tool call limits             | [references/execution-control/limits.md](references/execution-control/limits.md) |

### Advanced Features

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| Features overview (evals, reasoning, multimodal, tracing, skills) | [references/features/online-resources.md](references/features/online-resources.md) |
| Evals (accuracy, agent-as-judge, performance, reliability) | Online: [Evals Overview](https://docs.agno.com/features/evals/overview) |
| Reasoning models and tools   | Online: [Reasoning Documentation](https://docs.agno.com/features/reasoning) |
| Multimodal (images, audio, video) | Online: [Multimodal Documentation](https://docs.agno.com/features/multimodal) |
| Tracing and observability  | Online: [Tracing Documentation](https://docs.agno.com/features/tracing) |
| Custom logging  | Online: [Custom Logging](https://docs.agno.com/features/custom-logging) |
| Telemetry  | Online: [Telemetry](https://docs.agno.com/features/telemetry) |
| Skills (experimental) | Online: [Skills Documentation](https://docs.agno.com/features/skills) |

### AgentOS

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| AgentOS overview and setup | [references/agent-os/overview.md](references/agent-os/overview.md) |
| Configuration (chat, memory, knowledge, evals) | [references/agent-os/config.md](references/agent-os/config.md) |
| Interfaces (A2A, AG-UI, Slack, WhatsApp) | [references/agent-os/interfaces.md](references/agent-os/interfaces.md) |
| Clients (AgentOSClient, A2AClient) | [references/agent-os/clients.md](references/agent-os/clients.md) |
| Security and RBAC          | [references/agent-os/security.md](references/agent-os/security.md) |

### Integrations

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| Integrations overview (40+ models, 12 DBs, 18 vector DBs, 100+ tools) | [references/integrations/online-resources.md](references/integrations/online-resources.md) |
| Model providers (OpenAI, Anthropic, Google, etc.) | Online: [Model Index](https://docs.agno.com/integrations/models/model-index) |
| Database providers (Postgres, SQLite, MongoDB, Redis, etc.) | Online: [Database Providers](https://docs.agno.com/integrations/databases/overview) |
| Vector databases (PgVector, Pinecone, Qdrant, Weaviate, etc.) | Online: [Vector Databases](https://docs.agno.com/integrations/vectordbs/overview) |
| Toolkits (100+ pre-built tools) | Online: [Toolkit Index](https://docs.agno.com/integrations/toolkits/overview) |
| Memory integrations | Online: [Memory](https://docs.agno.com/integrations/memory/overview) |
| Observability (OpenTelemetry, AgentOps, Langfuse, etc.) | Online: [OpenTelemetry](https://docs.agno.com/integrations/observability/overview) |

### Cookbook

| Topic                                | Reference File                                      |
| ------------------------------------- | -------------------------------------------------- |
| Cookbook overview (2000+ production examples) | [references/cookbook/online-resources.md](references/cookbook/online-resources.md) |
| Models (40+ model providers) | Online: [Models Overview](https://docs.agno.com/cookbook/models/overview) |
| Tools (MCP, custom tools, built-in) | Online: [Tools Overview](https://docs.agno.com/cookbook/tools/overview) |
| Knowledge & RAG (vector DBs, embedders, readers, chunking) | Online: [Knowledge Overview](https://docs.agno.com/cookbook/knowledge/overview) |
| Storage (Postgres, SQLite, MongoDB, Redis, etc.) | Online: [Storage Overview](https://docs.agno.com/cookbook/storage/overview) |
| Agents (RAG, research, multimodal, integrations) | Online: [Agents Overview](https://docs.agno.com/cookbook/agents/overview) |
| Teams (content & research, support & routing) | Online: [Teams Overview](https://docs.agno.com/cookbook/teams/overview) |
| Workflows (blog generator, company description, recruiter, etc.) | Online: [Workflows Overview](https://docs.agno.com/cookbook/workflows/overview) |
| Learning (personal assistant, support agent) | Online: [Learning Overview](https://docs.agno.com/cookbook/learning/overview) |
| Streamlit Apps (agentic RAG, SQL agent, answer engine) | Online: [Streamlit Overview](https://docs.agno.com/cookbook/streamlit/overview) |

## Best Practices

1. **Start simple** - Single agent first, add complexity as needed
2. **Use streaming** - Provides better UX and visibility
3. **Add tools selectively** - Only include tools agent actually needs
4. **Leverage knowledge** - Use RAG for domain-specific information
5. **Enable memory** - Store user preferences for personalization
6. **Test with tools** - Always test tools independently
7. **Use AgentOS for production** - Don't build custom deployment layer
8. **Structure teams wisely** - Each agent should have clear, narrow scope
9. **Use workflows for pipelines** - Repeatable processes benefit from structured steps
10. **Monitor with tracing** - Enable observability in production

## When to Load Reference Files

Load reference files when:
- Implementing specific features (knowledge, memory, guardrails, hooks)
- Debugging complex issues
- Looking for patterns and examples
- Needing detailed API documentation
- Learning best practices for a specific topic

Keep SKILL.md in context for quick reference and decision-making guidance. Use the reference files for deep dives into specific topics, and refer to online documentation for the latest updates on features, integrations, and cookbook examples.
