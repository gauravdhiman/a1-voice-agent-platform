# Teams

**See parent [SKILL.md](../SKILL.md) for overview and quickstart.**

## Team Overview

A team is a collection of agents (or sub-teams) that collaborate on complex tasks. The team leader delegates tasks to members based on their roles and capabilities.

## When to Use Teams

Use a team when:
- Task requires multiple specialized agents with different expertise
- Single agent's context window would be exceeded
- You need clear separation of concerns

Use a single agent when:
- Task is simple and focused
- Token efficiency matters
- You're not sure yet (start simple, add agents when needed)

## Building Teams

### Basic Team

```python
from agno.team import Team
from agno.agent import Agent

researcher = Agent(name="Researcher", role="Gather information")
writer = Agent(name="Writer", role="Create content")

team = Team(
    name="Content Team",
    members=[researcher, writer],
    instructions="Research topic and write article",
)
```

### Team with Tools

```python
from agno.tools.yfinance import YFinanceTools
from agno.tools.hackernews import HackerNewsTools

finance_agent = Agent(name="Finance Agent", tools=[YFinanceTools()])
news_agent = Agent(name="News Agent", tools=[HackerNewsTools()])

team = Team(members=[finance_agent, news_agent])
```

### Nested Teams

```python
german_team = Team(
    name="Germanic Team",
    members=[
        Agent(name="German Agent", role="Speak German"),
        Agent(name="Dutch Agent", role="Speak Dutch"),
    ],
)

main_team = Team(
    name="Language Team",
    members=[
        Agent(name="English Agent"),
        Agent(name="Chinese Agent"),
        german_team,  # Sub-team
    ],
)
```

## Team Patterns

### Supervisor Pattern (Default)

Team leader delegates and synthesizes results:

```python
team = Team(
    name="Research Team",
    members=[news_agent, finance_agent],
    instructions=[
        "Delegate to appropriate specialist",
        "Synthesize results into comprehensive report",
    ],
)
```

**Use when:** You need task decomposition and quality control

### Router Pattern

Route to specialists without synthesis:

```python
team = Team(
    name="Language Router",
    members=[english_agent, japanese_agent, spanish_agent],
    respond_directly=True,  # Specialist responds directly
    determine_input_for_members=False,
    instructions="Route to appropriate language agent",
)
```

**Use when:** You need routing/passthrough functionality

### Broadcast Pattern

Parallel research from all members:

```python
team = Team(
    name="Research Team",
    members=[agent1, agent2, agent3],
    delegate_to_all_members=True,  # All members work in parallel
)
```

**Use when:** You need multiple perspectives or parallel research

## Running Teams

### Sync Execution

```python
response = team.run("What are trending AI stories?")
print(response.content)
```

### Async Execution

```python
import asyncio

async def main():
    response = await team.arun("Research AI trends")
    print(response.content)

asyncio.run(main())
```

### Streaming

```python
from agno.run.team import TeamRunEvent

for event in team.run("Tell me about AI", stream=True):
    if event.event == TeamRunEvent.run_content:
        print(event.content, end="", flush=True)
```

### Streaming with Events

```python
for event in team.run("...", stream=True, stream_events=True):
    if event.event == TeamRunEvent.run_content:
        print(f"Content: {event.content}")
    elif event.event == TeamRunEvent.tool_call_started:
        print(f"Tool call started")
    elif event.event == TeamRunEvent.team_reasoning_step:
        print(f"Reasoning: {event.reasoning_content}")
```

### Show Member Responses

```python
team.print_response(
    "Research this topic",
    show_members_responses=True,  # Show what each agent did
)
```

## Team Configuration

### Common Parameters

| Parameter                  | Type   | Description                         |
| ------------------------- | ------ | ----------------------------------- |
| `name`                     | str    | Team name                         |
| `model`                    | Model  | LLM model for team leader        |
| `members`                  | list   | Agents and sub-teams           |
| `role`                     | str    | Team's purpose                    |
| `instructions`              | str/list| Instructions for team leader       |
| `respond_directly`          | bool   | Route without synthesis            |
| `determine_input_for_members`| bool   | Leader determines member inputs    |
| `delegate_to_all_members`    | bool   | Broadcast to all members           |
| `show_members_responses`      | bool   | Show member actions              |
| `stream_member_events`        | bool   | Stream internal member events      |

### Team Model

Team leader uses its own model:

```python
team = Team(
    model=OpenAIResponses(id="gpt-4o"),  # Leader's model
    members=[member1, member2],  # Members use their own models
)
```

## Event Types

**Core events:**
- `TeamRunStarted` - Team execution started
- `TeamRunContent` - Response text chunk
- `TeamRunContentCompleted` - Content streaming complete
- `TeamRunCompleted` - Execution completed
- `TeamRunError` - Error occurred
- `TeamRunCancelled` - Run was cancelled

**Tool events:**
- `TeamToolCallStarted` - Tool call started
- `TeamToolCallCompleted` - Tool call completed

**Reasoning events:**
- `TeamReasoningStarted` - Reasoning started
- `TeamReasoningStep` - Single reasoning step
- `TeamReasoningCompleted` - Reasoning completed

## Team Patterns

### Research Team

```python
news_agent = Agent(
    name="News Researcher",
    role="Get tech news and trends",
    tools=[HackerNewsTools()],
)

finance_agent = Agent(
    name="Finance Researcher",
    role="Get stock prices and financial data",
    tools=[YFinanceTools()],
)

research_team = Team(
    name="Research Team",
    members=[news_agent, finance_agent],
    instructions=[
        "Delegate to News Researcher for tech news",
        "Delegate to Finance Researcher for stock data",
        "Synthesize findings into comprehensive report",
    ],
    show_members_responses=True,
)
```

### Content Creation Team

```python
researcher = Agent(
    name="Researcher",
    role="Gather information on topic",
    tools=[HackerNewsTools()],
)

writer = Agent(
    name="Writer",
    role="Write engaging articles",
)

editor = Agent(
    name="Editor",
    role="Review and improve content",
)

content_team = Team(
    name="Content Team",
    members=[researcher, writer, editor],
    instructions=[
        "Delegate to Researcher for information gathering",
        "Delegate to Writer for drafting content",
        "Delegate to Editor for review and improvement",
        "Synthesize final content",
    ],
)
```

### Multi-Language Team

```python
english_agent = Agent(name="English", role="Speak English")
japanese_agent = Agent(name="Japanese", role="Speak Japanese")
spanish_agent = Agent(name="Spanish", role="Speak Spanish")

language_router = Team(
    name="Language Router",
    members=[english_agent, japanese_agent, spanish_agent],
    respond_directly=True,
    determine_input_for_members=False,
    instructions="Route questions to appropriate language agent",
)
```

### Customer Support Team

```python
billing_agent = Agent(
    name="Billing Agent",
    role="Handle billing inquiries",
    tools=[BillingTools()],
)

technical_agent = Agent(
    name="Technical Agent",
    role="Handle technical issues",
    tools=[TechTools()],
)

general_agent = Agent(
    name="General Agent",
    role="Handle general inquiries",
    memory_manager=memory_manager,
)

support_team = Team(
    name="Support Team",
    members=[billing_agent, technical_agent, general_agent],
    instructions=[
        "Route billing questions to Billing Agent",
        "Route technical issues to Technical Agent",
        "Handle general inquiries with General Agent",
        "Synthesize when multiple agents involved",
    ],
)
```

### Analysis Team

```python
analyst1 = Agent(
    name="Data Analyst",
    role="Analyze data patterns",
    tools=[AnalyticsTools()],
)

analyst2 = Agent(
    name="Trend Analyst",
    role="Identify trends and predictions",
    tools=[TrendTools()],
)

summarizer = Agent(
    name="Summarizer",
    role="Combine analysis into insights",
)

analysis_team = Team(
    name="Analysis Team",
    members=[analyst1, analyst2, summarizer],
    instructions=[
        "Delegate to both analysts in parallel",
        "Synthesize findings with Summarizer",
    ],
)
```

## Delegation Control

### Manual Member Input

```python
def get_member_input(step_input: StepInput) -> dict:
    """Custom logic for member input."""
    return {
        "task": step_input.run_input,
        "context": "Additional context",
    }

team = Team(
    members=[member1, member2],
    determine_member_input=get_member_input,
)
```

### Member Selection

Control which members receive tasks:

```python
team = Team(
    members=[member1, member2, member3],
    instructions=[
        "Only use member1 for financial topics",
        "Only use member2 for technical topics",
        "Use member3 for general topics",
    ],
)
```

## Team with Knowledge

```python
knowledge_base = Knowledge(
    vector_db=LanceDb(uri="tmp/knowledge", table_name="docs")
)

team = Team(
    members=[researcher, writer],
    knowledge=knowledge_base,  # All members can search
    instructions="Use knowledge base for accurate information",
)
```

## Team with Memory

```python
memory_manager = MemoryManager(model=OpenAIResponses(id="gpt-4o"), db=db)

team = Team(
    members=[agent1, agent2],
    memory_manager=memory_manager,
    instructions="Remember user preferences across team interactions",
)
```

## Debugging Teams

### Show Member Responses

```python
team.print_response(
    "Test query",
    show_members_responses=True,  # See delegation and responses
)
```

### Stream Events

```python
for event in team.run("...", stream=True, stream_events=True):
    # See all internal events
    print(f"Event: {event.event}")
```

### Check Member Roles

```python
for member in team.members:
    print(f"Member: {member.name}, Role: {member.role}")
```

## See Also

- [Agents](agents.md) - Single agent patterns
- [Workflows](workflows.md) - Pipeline orchestration
- [Team Examples](../cookbook/teams.md) - Example teams
