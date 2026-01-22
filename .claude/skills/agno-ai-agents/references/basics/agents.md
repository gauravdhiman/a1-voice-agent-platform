# Agents

**See parent [SKILL.md](../SKILL.md) for overview and quickstart.**

## Agent Overview

An agent is an LLM-driven program that uses tools in a loop, guided by instructions. Think of it as an autonomous assistant that can take actions.

## Building Agents

### Basic Agent

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

### Agent with Tools

```python
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    name="Finance Agent",
    model=OpenAIResponses(id="gpt-4o"),
    tools=[YFinanceTools()],
    instructions="Help with financial data",
)
```

### Agent with Instructions

Multiple instruction formats supported:

```python
agent = Agent(
    # String
    instructions="You are a helpful assistant",

    # List (recommended for complex instructions)
    instructions=[
        "You are a helpful assistant",
        "Always be concise",
        "Use markdown formatting",
    ],

    # Function (dynamic instructions)
    instructions=lambda run_context: f"Current time: {datetime.now()}",
)
```

## Running Agents

### Sync Execution

```python
response = agent.run("What is the weather?")
print(response.content)
```

### Async Execution

```python
import asyncio

async def main():
    response = await agent.arun("What is the weather?")
    print(response.content)

asyncio.run(main())
```

### Streaming

```python
from agno.agent import RunEvent

for event in agent.run("Tell me a story", stream=True):
    if event.event == RunEvent.run_content:
        print(event.content, end="", flush=True)
```

### Streaming with Events

```python
for event in agent.run("...", stream=True, stream_events=True):
    if event.event == RunEvent.run_content:
        print(f"Content: {event.content}")
    elif event.event == RunEvent.tool_call_started:
        print(f"Tool: {event.tool.tool_name}")
    elif event.event == RunEvent.reasoning_step:
        print(f"Reasoning: {event.reasoning_content}")
```

## Agent Capabilities

### Knowledge (RAG)

**Agentic RAG** - Agent searches knowledge base when needed:

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType

knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="docs",
        search_type=SearchType.hybrid,
    )
)
knowledge.add_content(url="https://example.com/doc.pdf")

agent = Agent(knowledge=knowledge)
```

**Traditional RAG** - Always retrieve before response:

```python
from agno.tools.knowledge import KnowledgeTools

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    search=True,  # Always search
    think=False,  # Don't think first
)

agent = Agent(tools=[knowledge_tools])
```

**Knowledge with filters:**

```python
agent.run("What's in my department?", knowledge_filters={"department": "engineering"})
```

### Memory

**Store user preferences:**

```python
from agno.memory import MemoryManager

memory_manager = MemoryManager(model=OpenAIResponses(id="gpt-4o"), db=db)

agent = Agent(
    memory_manager=memory_manager,
    enable_agentic_memory=True,
)

# Agent learns and remembers preferences
response = agent.run("I prefer short answers", user_id="user@example.com")
```

**Agentic memory** - Agent decides what to remember:

```python
agent = Agent(
    memory_manager=memory_manager,
    enable_agentic_memory=True,  # Agent decides what to store
)
```

**Manual memory operations:**

```python
from agno.tools.memory import MemoryTools

agent = Agent(
    tools=[MemoryTools(memory_manager=memory_manager)],
    enable_agentic_memory=False,  # Manual control
)
```

### Session State

**Persistent data within session:**

```python
agent = Agent(
    session_state={"counter": 0, "shopping_list": []},
    db=db,
    instructions="Current state: {session_state}",
)

# Access state in tools
def add_item(run_context: RunContext, item: str):
    run_context.session_state["shopping_list"].append(item)
    return f"Added {item}"

agent = Agent(session_state={"shopping_list": []}, tools=[add_item])
```

### History

**Add conversation history to context:**

```python
agent = Agent(
    add_history_to_context=True,  # Include previous messages
    db=db,  # Required for history persistence
)
```

**Limit history:**

```python
agent = Agent(
    add_history_to_context=True,
    history_messages=10,  # Last 10 messages
)
```

**Filter tool calls from history:**

```python
agent = Agent(
    add_history_to_context=True,
    include_tool_calls_in_history=False,  # Hide tool calls
)
```

### Structured Output

**Pydantic model for output:**

```python
from pydantic import BaseModel

class TVShow(BaseModel):
    title: str
    episodes: int

agent = Agent(model=OpenAIResponses(id="gpt-5.2"))
response = agent.run("Create a TV show", output_schema=TVShow)

print(response.content.title)
print(response.content.episodes)
```

### Multimodal

**Image input:**

```python
from agno.media import Image

agent.run("Describe this", images=[Image(url="https://example.com/image.jpg")])
```

**Audio input:**

```python
from agno.media import Audio

agent.run("Transcribe this", audio=[Audio(url="https://example.com/audio.mp3")])
```

**File input:**

```python
from agno.media import File

agent.run("Analyze this", files=[File(path="document.pdf")])
```

### Reasoning

**Use reasoning model for complex tasks:**

```python
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="o3-mini", reasoning_effort="medium")
)
```

**Capture reasoning content:**

```python
response = agent.run("Solve this problem")
print(response.reasoning_content)  # See the reasoning steps
```

## Agent Configuration

### Common Parameters

| Parameter          | Type    | Description                     |
| ----------------- | ------- | ------------------------------- |
| `name`            | str      | Agent name                     |
| `model`           | Model    | LLM model to use              |
| `role`            | str      | Agent's role/purpose           |
| `instructions`     | str/list | System instructions             |
| `tools`           | list     | Tools available to agent        |
| `knowledge`        | Knowledge| Knowledge base for RAG          |
| `memory_manager`  | Memory   | Memory for user preferences      |
| `session_state`   | dict     | Initial session state           |
| `db`              | Db       | Database for persistence       |
| `markdown`        | bool     | Format output as markdown      |
| `add_history_to_context` | bool | Include conversation history |
| `enable_agentic_memory` | bool | Agent decides what to remember |
| `output_model`    | BaseModel| Structured output schema      |

### Model Selection

**OpenAI:**

```python
from agno.models.openai import OpenAIChat, OpenAIResponses

agent = Agent(model=OpenAIChat(id="gpt-4o"))
agent = Agent(model=OpenAIResponses(id="gpt-5.2"))
```

**Anthropic:**

```python
from agno.models.anthropic import Claude

agent = Agent(model=Claude(id="claude-sonnet-4-5"))
```

**Google:**

```python
from agno.models.google import Gemini

agent = Agent(model=Gemini(id="gemini-2.5-flash-exp"))
```

**Local models (Ollama):**

```python
from agno.models.ollama import OllamaChat

agent = Agent(model=OllamaChat(id="llama3"))
```

## Event Types

**Core events:**
- `RunStarted` - Execution started
- `RunContent` - Response text chunk
- `RunContentCompleted` - Content streaming complete
- `RunCompleted` - Execution completed
- `RunError` - Error occurred
- `RunCancelled` - Run was cancelled

**Tool events:**
- `ToolCallStarted` - Tool execution started
- `ToolCallCompleted` - Tool execution completed

**Reasoning events:**
- `ReasoningStarted` - Reasoning process started
- `ReasoningStep` - Single reasoning step
- `ReasoningCompleted` - Reasoning completed

**Memory events:**
- `MemoryUpdateStarted` - Memory update started
- `MemoryUpdateCompleted` - Memory update completed

**Hook events:**
- `PreHookStarted` - Pre-run hook started
- `PreHookCompleted` - Pre-run hook completed
- `PostHookStarted` - Post-run hook started
- `PostHookCompleted` - Post-run hook completed

## Agent Patterns

### Research Agent

```python
from agno.tools.knowledge import KnowledgeTools
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    name="Researcher",
    model=OpenAIResponses(id="gpt-5.2"),
    tools=[YFinanceTools()],
    knowledge=knowledge,
    instructions=[
        "Research topic thoroughly",
        "Use knowledge base for background info",
        "Use financial tools for stock data",
        "Provide comprehensive report",
    ],
)
```

### Customer Support Agent

```python
agent = Agent(
    name="Support Agent",
    model=OpenAIResponses(id="gpt-4o"),
    tools=[TicketTools(), KnowledgeTools()],
    memory_manager=memory_manager,
    instructions=[
        "Help customers with their issues",
        "Be empathetic and patient",
        "Remember customer preferences",
        "Use knowledge base for product info",
    ],
)
```

### Content Creator Agent

```python
from agno.tools.media import ImageTools

agent = Agent(
    name="Content Creator",
    model=OpenAIResponses(id="gpt-5.2"),
    tools=[ImageTools()],
    instructions=[
        "Create engaging content",
        "Generate images when appropriate",
        "Use markdown formatting",
        "Be creative and original",
    ],
)
```

## See Also

- [Teams](teams.md) - Multi-agent coordination
- [Workflows](workflows.md) - Pipeline orchestration
- [Tools Overview](../tools/overview.md) - Tool creation
- [Knowledge](../context/knowledge.md) - RAG implementation
- [Memory](../context/memory.md) - Memory systems
