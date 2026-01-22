# Tools

**See parent [SKILL.md](../SKILL.md) for overview and quickstart.**

## Tools Overview

Tools are functions that Agents call to interact with external systems. They give agents real-world action capabilities.

## Creating Tools

### Basic Tool

```python
from agno.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get weather for city.

    Args:
        city (str): The city to get weather for.
    """
    return f"Weather in {city} is sunny."
```

### Tool with Multiple Parameters

```python
@tool
def calculate_metrics(revenue: float, expenses: float) -> dict:
    """Calculate financial metrics.

    Args:
        revenue (float): Total revenue
        expenses (float): Total expenses
    """
    profit = revenue - expenses
    margin = (profit / revenue * 100) if revenue > 0 else 0
    return {"profit": profit, "margin": margin}
```

### Tool with Pydantic

```python
from pydantic import BaseModel, Field

class WeatherRequest(BaseModel):
    city: str = Field(description="City name")

@tool
def get_weather(request: WeatherRequest) -> str:
    """Get weather."""
    return f"Weather in {request.city} is sunny."
```

### Async Tool

```python
import asyncio

@tool
async def fetch_data(url: str) -> str:
    """Fetch data from URL asynchronously."""
    await asyncio.sleep(1)
    return f"Data from {url}"
```

## Using Toolkits

### Built-in Toolkits

```python
from agno.tools.yfinance import YFinanceTools
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    tools=[YFinanceTools(), HackerNewsTools()],
)
```

### Common Toolkits

| Toolkit                 | Purpose                             |
| ------------------------ | ------------------------------------ |
| `YFinanceTools`          | Stock prices and financial data          |
| `HackerNewsTools`         | Fetch HackerNews stories               |
| `WikipediaTools`          | Wikipedia search and retrieval         |
| `WebTools`                | Web scraping and search               |
| `DatabaseTools`            | SQL database queries                 |
| `EmailTools`               | Send emails                         |
| `SlackTools`              | Slack messages                      |
| `GoogleCalendarTools`       | Calendar operations                  |
| `NotionTools`              | Notion CRUD operations             |
| `AirbnbTools`              | Airbnb data access                  |

See [AgentOS UI](https://os.agno.com) or documentation for complete toolkit list.

## Tool Parameters

### Run Context Access

Access agent's run context:

```python
from agno.run import RunContext

@tool
def add_item(run_context: RunContext, item: str) -> str:
    """Add item to shopping list in session state."""
    if not run_context.session_state:
        run_context.session_state = {}

    items = run_context.session_state.get("shopping_list", [])
    items.append(item)
    run_context.session_state["shopping_list"] = items

    return f"Added {item}. List: {items}"
```

### Agent Access

Access agent instance:

```python
from agno.agent import Agent

@tool
def get_agent_info(agent: Agent) -> str:
    """Get agent configuration."""
    return f"Agent name: {agent.name}, Instructions: {agent.instructions}"
```

### Team Access

Access team instance:

```python
from agno.team import Team

@tool
def get_team_info(team: Team) -> str:
    """Get team configuration."""
    return f"Team: {team.name}, Members: {len(team.members)}"
```

### Media Parameters

Access input media:

```python
from agno.media import Image

@tool
def process_image(images: list) -> str:
    """Process input images."""
    return f"Received {len(images)} images"
```

## Tool Results

### Simple Return Types

```python
@tool
def get_number() -> int:
    """Return a number."""
    return 42

@tool
def get_list() -> list:
    """Return a list."""
    return ["item1", "item2", "item3"]

@tool
def get_dict() -> dict:
    """Return a dictionary."""
    return {"key": "value"}
```

### ToolResult for Media

```python
from agno.tools.function import ToolResult
from agno.media import Image

@tool
def generate_image(prompt: str) -> ToolResult:
    """Generate an image from prompt."""
    # Create image (example)
    image = Image(
        id="img_123",
        url="https://example.com/generated.jpg",
        original_prompt=prompt,
    )

    return ToolResult(
        content=f"Generated image for: {prompt}",
        images=[image],
    )
```

## Tool Hooks

### Pre-Execution Hook

```python
from agno.tools import hook

@hook(event="pre_tool_execution")
def log_tool_call(tool_name: str, tool_args: dict, agent: Agent):
    """Log before tool execution."""
    print(f"Calling tool: {tool_name} with args: {tool_args}")
```

### Post-Execution Hook

```python
@hook(event="post_tool_execution")
def log_tool_result(tool_name: str, tool_result, agent: Agent):
    """Log after tool execution."""
    print(f"Tool {tool_name} returned: {tool_result}")
```

## Tool Patterns

### API Tool

```python
import requests

@tool
def fetch_api_data(endpoint: str) -> dict:
    """Fetch data from API endpoint.

    Args:
        endpoint (str): API endpoint URL
    """
    response = requests.get(endpoint)
    return response.json()
```

### Database Tool

```python
@tool
def query_database(query: str) -> list:
    """Query database with SQL.

    Args:
        query (str): SQL query string
    """
    # Execute query
    results = execute_sql(query)
    return results
```

### File Operation Tool

```python
@tool
def read_file(path: str) -> str:
    """Read file contents.

    Args:
        path (str): File path to read
    """
    with open(path, 'r') as f:
        return f.read()
```

### Tool with Exception Handling

```python
@tool
def risky_operation(value: int) -> str:
    """Perform risky operation with error handling."""
    try:
        result = 10 / value
        return f"Result: {result}"
    except ZeroDivisionError:
        return "Error: Cannot divide by zero"
    except Exception as e:
        return f"Error: {str(e)}"
```

## Tool Configuration

### Tool Metadata

```python
@tool(
    name="custom_name",
    description="Custom description",
    sanitize_arguments=True,
)
def my_tool(value: str) -> str:
    """Tool docstring."""
    return value
```

### Tool Filtering

Filter which tools agent can use:

```python
@tool
def sensitive_operation(data: str) -> str:
    """Sensitive operation tool."""
    return data

# Agent can't use sensitive tool
agent = Agent(
    tools=[get_weather],
    # sensitive_operation not included
)
```

## MCP Tools

### Connect to MCP Server

```python
from agno.tools.mcp import MCPTools

mcp_tools = MCPTools(url="http://localhost:8000")
agent = Agent(tools=[mcp_tools])
```

### Multiple MCP Servers

```python
from agno.tools.mcp import MCPTools

github_tools = MCPTools(url="http://github-mcp:8000")
notion_tools = MCPTools(url="http://notion-mcp:8000")

agent = Agent(tools=[github_tools, notion_tools])
```

See [MCP Integration](../integrations/mcp.md) for MCP setup and usage.

## Knowledge Tools

### Agentic RAG Tools

```python
from agno.tools.knowledge import KnowledgeTools

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,  # Plan search
    search=True,  # Execute search
    analyze=True,  # Evaluate results
    add_few_shot=True,
)

agent = Agent(tools=[knowledge_tools])
```

**Knowledge tools provide:**
- `think` - Plan search queries
- `search` - Execute knowledge base queries
- `analyze` - Evaluate if results are sufficient

See [Knowledge](../context/knowledge.md) for RAG patterns.

## Memory Tools

### Manual Memory Operations

```python
from agno.tools.memory import MemoryTools

memory_tools = MemoryTools(
    memory_manager=memory_manager,
    create=True,
    read=True,
    update=True,
    delete=True,
)

agent = Agent(
    tools=[memory_tools],
    enable_agentic_memory=False,  # Manual control
)
```

See [Memory](../context/memory.md) for memory patterns.

## Reasoning Tools

### Knowledge Tools with Reasoning

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    capture_reasoning=True,  # Capture reasoning steps
)

agent = Agent(
    tools=[knowledge_tools],
    model=OpenAIChat(id="o3-mini"),  # Reasoning model
)
```

### Memory Tools with Reasoning

```python
from agno.tools.memory import MemoryTools

memory_tools = MemoryTools(
    memory_manager=memory_manager,
    capture_reasoning=True,
)

agent = Agent(
    tools=[memory_tools],
    model=OpenAIChat(id="o3-mini"),
)
```

See [Reasoning](../features/reasoning.md) for reasoning patterns.

## Tool Testing

### Test Tool Independently

```python
result = get_weather("San Francisco")
print(result)
# Output: Weather in San Francisco is sunny.
```

### Test with Agent

```python
test_agent = Agent(tools=[get_weather])
response = test_agent.run("What's the weather in NYC?")
print(response.content)
```

## Best Practices

1. **Clear docstrings** - Explain what tool does and each parameter
2. **Type hints** - Always include parameter and return type hints
3. **Error handling** - Handle exceptions gracefully
4. **Simple returns** - Return simple types (str, int, dict, list)
5. **Use ToolResult** - For media artifacts (images, audio, video)
6. **Async when needed** - Use async for I/O operations
7. **Tool hooks** - Use for logging and monitoring
8. **Test tools** - Always test independently before using with agents
9. **Sanitize inputs** - Use sanitize_arguments=True for user inputs
10. **Tool naming** - Use descriptive names that model can understand

## See Also

- [Knowledge Tools](../context/knowledge.md) - RAG toolkits
- [Memory Tools](../context/memory.md) - Memory toolkits
- [Reasoning Tools](../features/reasoning.md) - Reasoning toolkits
- [Tool Examples](../cookbook/tools.md) - Example tools
