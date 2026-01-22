# Usage Patterns

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Two main patterns for using knowledge with agents: **Agentic RAG** (agent decides when to search) and **Traditional RAG** (always retrieve before response).

## Agentic RAG (Recommended)

Agent autonomously decides when and how to search the knowledge base.

```python
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge

agent = Agent(
    name="RAG Agent",
    model=OpenAIResponses(id="gpt-4o"),
    knowledge=knowledge,
    instructions="Use your knowledge base when needed to answer questions",
)
```

**Execution flow:**
1. User asks question
2. Agent analyzes question and determines if search is needed
3. If search needed, queries knowledge base
4. Agent analyzes results and decides if more searches needed
5. Continues searching until satisfied
6. Generates response based on retrieved information

**When to use:**
- Complex queries requiring multiple searches
- Unknown if search is needed upfront
- Want efficient use of knowledge base
- Agent should be autonomous

**Pros:**
- Efficient (only searches when needed)
- Adaptive to query complexity
- Can plan multiple searches
- Better for open-ended questions

**Cons:**
- May miss relevant information
- Requires good agent instructions
- Less predictable behavior

### Agentic RAG with KnowledgeTools

More control over agentic behavior:

```python
from agno.tools.knowledge import KnowledgeTools

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,  # Plan search queries
    search=True,  # Execute searches
    analyze=True,  # Evaluate if results are sufficient
    add_few_shot=True,  # Add examples to context
)

agent = Agent(
    name="Smart RAG Agent",
    model=OpenAIResponses(id="gpt-4o"),
    tools=[knowledge_tools],
    instructions="Plan your searches carefully and analyze results thoroughly",
)
```

## Traditional RAG

Always retrieve documents before generating response.

```python
from agno.tools.knowledge import KnowledgeTools

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    search=True,  # Always search
    think=False,  # Don't plan
    analyze=False,  # Don't analyze
)

agent = Agent(
    name="Traditional RAG Agent",
    model=OpenAIResponses(id="gpt-4o"),
    tools=[knowledge_tools],
)
```

**Execution flow:**
1. User asks question
2. Always searches knowledge base
3. Generates response based on search results

**When to use:**
- Every question needs knowledge base
- Predictable search behavior required
- Simple question-answer pattern
- Want to guarantee retrieval

**Pros:**
- Predictable behavior
- Guaranteed retrieval
- Simpler to debug
- Consistent responses

**Cons:**
- Always searches (inefficient)
- May retrieve irrelevant info
- Cannot skip unnecessary searches
- Less flexible

## Choosing the Right Pattern

| Need | Recommended Pattern |
|------|-------------------|
| General questions | Agentic RAG |
| Document-specific queries | Traditional RAG |
| Complex multi-step research | Agentic RAG |
| Simple fact retrieval | Traditional RAG |
| Unknown query patterns | Agentic RAG |
| Predictable behavior needed | Traditional RAG |

## Knowledge Filtering in Queries

Filter knowledge base during queries:

```python
response = agent.run(
    "What are the engineering guidelines?",
    knowledge_filters={
        "department": "engineering",
        "access_level": "internal",
    },
)
```

See [Filters](filters.md) for detailed filtering patterns.

## Per-Query Knowledge Selection

Use different knowledge bases for different queries:

```python
kb_tech = Knowledge(vector_db=LanceDb(uri="db_tech", table_name="tech_docs"))
kb_product = Knowledge(vector_db=LanceDb(uri="db_product", table_name="product_docs"))

agent = Agent(
    name="Multi-Knowledge Agent",
    knowledge=[kb_tech, kb_product],  # Multiple knowledge bases
    instructions="Search both technical and product documentation",
)
```

## Dynamic Knowledge Updates

Update knowledge base during runtime:

```python
# User uploads new document
user_doc_url = "https://example.com/user-upload.pdf"

# Add to knowledge base
knowledge.add_content(url=user_doc_url)

# Agent can now search the new document
response = agent.run("Summarize the document I just uploaded")
```

## Knowledge in Teams

Distribute knowledge across team members:

```python
kb_engineering = Knowledge(...)
kb_product = Knowledge(...)
kb_sales = Knowledge(...)

engineering_agent = Agent(name="Engineer", knowledge=kb_engineering)
product_agent = Agent(name="Product Manager", knowledge=kb_product)
sales_agent = Agent(name="Sales", knowledge=kb_sales)

team = Team(
    name="Company Knowledge Team",
    members=[engineering_agent, product_agent, sales_agent],
    instructions="Collaborate using your specialized knowledge bases",
)
```

## Best Practices

1. **Default to Agentic RAG** - More efficient and flexible for most cases
2. **Provide clear instructions** - Guide agent on when/how to search
3. **Use filters** - Reduce noise in search results
4. **Monitor search patterns** - Track agent search behavior
5. **Test with real queries** - Validate retrieval and response quality
6. **Consider multiple knowledge bases** - For different domains
7. **Update knowledge regularly** - Keep information current

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Filters](filters.md) - Metadata-based filtering
- [Advanced](advanced.md) - Reasoning, reranking, distributed RAG
- [Teams](../basics/teams.md) - Team coordination patterns
