# Knowledge Tools

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

KnowledgeTools provides fine-grained control over how agents interact with knowledge bases.

## KnowledgeTools Components

```python
from agno.tools.knowledge import KnowledgeTools

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,  # Plan search queries
    search=True,  # Execute searches
    analyze=True,  # Evaluate if results are sufficient
    add_few_shot=True,  # Add examples to context
)
```

## Tool Functions

### think

Plan and brainstorm search queries before execution.

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,
)
```

**What it does:**
- Analyzes user query
- Brainstorms search terms
- Plans search strategy
- Identifies relevant filters

**When to enable:**
- Complex queries
- Unknown optimal search terms
- Want better retrieval quality
- Multi-step research

### search

Execute knowledge base queries.

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    search=True,
)
```

**What it does:**
- Executes semantic/vector searches
- Applies metadata filters
- Retrieves top K results
- Returns document excerpts

**When to enable:**
- Always required for knowledge access
- Core knowledge functionality

### analyze

Evaluate if search results are sufficient or more searches needed.

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    analyze=True,
)
```

**What it does:**
- Evaluates result relevance
- Determines if more information needed
- Recommends additional searches
- Synthesizes findings

**When to enable:**
- Agentic RAG
- Complex queries
- Want iterative refinement
- Multi-step research

### add_few_shot

Add few-shot examples to context for better understanding.

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    add_few_shot=True,
)
```

**What it does:**
- Adds query-result pairs to context
- Helps model understand expected behavior
- Improves response quality

**When to enable:**
- Want consistent responses
- Complex knowledge retrieval patterns
- Training agent behavior

## Configuration Examples

### Minimal Configuration

```python
# Simple search without planning/analysis
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    search=True,  # Just search
    think=False,
    analyze=False,
)

agent = Agent(tools=[knowledge_tools])
```

### Full Configuration

```python
# All features enabled
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,
    search=True,
    analyze=True,
    add_few_shot=True,
)

agent = Agent(tools=[knowledge_tools])
```

### Agentic RAG with Reasoning

```python
# Use reasoning model for better planning
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,
    search=True,
    analyze=True,
    add_few_shot=True,
)

agent = Agent(
    model=OpenAIChat(id="o3-mini"),  # Reasoning model
    tools=[knowledge_tools],
)
```

### Traditional RAG

```python
# Always search, no planning/analysis
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    search=True,
    think=False,  # Don't plan
    analyze=False,  # Don't analyze
)

agent = Agent(tools=[knowledge_tools])
```

## Custom Tool Behavior

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,
    search=True,
    analyze=True,
    # Custom instructions
    instructions="""
    When searching:
    1. Start with broad queries
    2. Narrow down with filters
    3. Analyze results thoroughly
    4. Search again if results are insufficient
    """,
)
```

## Tool Descriptions

KnowledgeTools provides these tools to the agent:

| Tool | Description | Dependencies |
|------|-------------|---------------|
| `think_knowledge` | Plan search queries and strategy | `think=True` |
| `search_knowledge` | Execute knowledge base search | `search=True` |
| `analyze_knowledge` | Evaluate search results | `analyze=True` |

## Tool Parameters

### Search Parameters

```python
# Agent can pass parameters to search
agent.run(
    "Find API documentation",
    knowledge_kwargs={
        "top_k": 10,  # Number of results
        "filters": {"doc_type": "api"},  # Metadata filters
        "search_type": "hybrid",  # Search type
    },
)
```

### Analysis Threshold

```python
knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    analyze=True,
    analyze_threshold=0.7,  # Relevance threshold for "good enough"
)
```

## Best Practices

1. **Start with think=False** - Simpler for basic use cases
2. **Enable analyze for complex queries** - Improves search quality
3. **Use add_few_shot for consistency** - Helps agent learn patterns
4. **Monitor tool usage** - Track which tools agent uses
5. **Adjust based on performance** - Tune configuration per use case
6. **Combine with reasoning models** - For better planning and analysis

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Usage Patterns](usage-patterns.md) - Agentic vs Traditional RAG
- [Advanced](advanced.md) - Reasoning, reranking, distributed RAG
- [Tools](../tools/overview.md) - Tool creation and usage
