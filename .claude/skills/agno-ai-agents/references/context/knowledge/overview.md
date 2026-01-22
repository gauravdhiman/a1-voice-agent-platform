# Knowledge Overview

**See parent [../SKILL.md](../SKILL.md) for overview and quickstart.**

## What is Knowledge?

Knowledge bases provide agents with searchable information through **Agentic RAG** (Retrieval-Augmented Generation). Agents can search, retrieve, and analyze documents at runtime.

**Key benefits:**
- Agents access up-to-date information beyond training data
- Reduces hallucinations by grounding responses in documents
- Enables domain-specific knowledge for specialized tasks
- Supports filtering and structured retrieval

## Basic Setup

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.models.openai import OpenAIEmbedder

knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/knowledge",
        table_name="docs",
        search_type=SearchType.hybrid,  # Semantic + keyword
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)

# Add content
knowledge.add_content(url="https://example.com/doc.pdf")
knowledge.add_content(text="Your content here...")
knowledge.add_content(path="./document.pdf")
```

## Core Components

1. **Vector Database** - Stores embeddings for semantic search
2. **Embedder** - Converts text to vector representations
3. **Chunker** - Splits documents into searchable pieces
4. **Reader** - Parses different file formats (PDF, web, etc.)
5. **Reranker** - Improves retrieval quality (optional)

## When to Use Knowledge

| Scenario | Use Knowledge |
|----------|--------------|
| Static documentation | ✅ Excellent |
| Frequently changing data | ✅ Good (with updates) |
| Real-time data | ❌ Use tools instead |
| Structured database queries | ❌ Use database tools |
| Creative writing | ❌ Not needed |

## Sub-Topics

- [Search Types](search-types.md) - Hybrid, vector, keyword search
- [Adding Content](adding-content.md) - URLs, files, text sources
- [Usage Patterns](usage-patterns.md) - Agentic vs Traditional RAG
- [Filters](filters.md) - Metadata-based filtering
- [Chunking](chunking.md) - Document chunking strategies
- [Readers](readers.md) - PDF, web, and content readers
- [Vector Databases](vector-databases.md) - LanceDB, PgVector, Qdrant, Pinecone
- [Advanced](advanced.md) - Reasoning, reranking, distributed RAG
- [Knowledge Tools](knowledge-tools.md) - KnowledgeTools components

## Quick Example with Agent

```python
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb
from agno.models.openai import OpenAIResponses

# Create knowledge base
knowledge = Knowledge(
    vector_db=LanceDb(uri="tmp/docs", table_name="knowledge"),
)
knowledge.add_content(url="https://example.com/product-docs.pdf")

# Create agent with knowledge
agent = Agent(
    name="Product Support Agent",
    model=OpenAIResponses(id="gpt-4o"),
    knowledge=knowledge,
    instructions="Use your knowledge base to answer questions about our products",
)

# Agent will automatically search when needed
response = agent.run("What are the system requirements?")
```

## Best Practices

1. **Start simple** - Use hybrid search with default settings
2. **Add metadata** - Enables filtering and better retrieval
3. **Choose right chunking** - Match strategy to content type
4. **Test retrieval** - Verify search results are accurate
5. **Update regularly** - Keep knowledge base fresh
6. **Monitor performance** - Track retrieval time and quality

## See Also

- [Search Types](search-types.md) - Hybrid, vector, keyword search
- [Usage Patterns](usage-patterns.md) - Agentic vs Traditional RAG
- [Chunking](chunking.md) - Document chunking strategies
- [Vector Databases](vector-databases.md) - LanceDB, PgVector, Qdrant, Pinecone
- [Integrations](../integrations/online-resources.md) - Model and database providers
