# Advanced Features

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Advanced knowledge features for complex use cases: reasoning, reranking, distributed RAG, and more.

## Agentic RAG with Reasoning

Use reasoning models for better planning and analysis.

```python
from agno.tools.knowledge import KnowledgeTools
from agno.models.openai import OpenAIChat

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,  # Plan search queries
    search=True,  # Execute searches
    analyze=True,  # Evaluate if results are sufficient
    capture_reasoning=True,  # Capture reasoning steps
)

agent = Agent(
    name="Reasoning RAG Agent",
    model=OpenAIChat(id="o3-mini"),
    tools=[knowledge_tools],
    instructions="Plan your searches carefully and analyze results thoroughly",
)
```

**Benefits:**
- Better query planning
- Deeper result analysis
- Captures reasoning trace
- Fewer irrelevant searches

**When to use:**
- Complex queries requiring planning
- Need transparency in decision-making
- Want to optimize search efficiency
- Multi-step research tasks

## RAG with Reranking

Improve retrieval quality by reranking search results.

```python
from agno.knowledge.reranker import CohereReranker

knowledge = Knowledge(
    vector_db=LanceDb(...),
    reranker=CohereReranker(api_key="cohere-api-key"),
)
```

**How it works:**
1. Initial search retrieves top N results
2. Reranker re-scores results using more sophisticated model
3. Top K reranked results returned to agent

**Supported rerankers:**
- Cohere Reranker
- OpenAI Reranker
- Custom rerankers

**When to use:**
- Large knowledge bases (> 100K documents)
- Need higher precision
- Can afford extra latency
- Production deployments

**Benefits:**
- Better relevance
- Higher precision
- More accurate retrieval

**Cost:**
- Additional API calls
- Increased latency
- Higher compute requirements

## Distributed RAG (Teams)

Distribute knowledge across multiple agents in a team.

```python
from agno.team import Team

kb_tech = Knowledge(vector_db=LanceDb(uri="db_tech", table_name="tech_docs"))
kb_product = Knowledge(vector_db=LanceDb(uri="db_product", table_name="product_docs"))
kb_sales = Knowledge(vector_db=LanceDb(uri="db_sales", table_name="sales_docs"))

agent1 = Agent(name="Tech Specialist", knowledge=kb_tech)
agent2 = Agent(name="Product Specialist", knowledge=kb_product)
agent3 = Agent(name="Sales Specialist", knowledge=kb_sales)

team = Team(
    name="Distributed Knowledge Team",
    members=[agent1, agent2, agent3],
    instructions="Coordinate to search across all knowledge bases",
)
```

**Patterns:**
- **Domain specialists** - Each agent has domain-specific knowledge
- **Geographic distribution** - Different knowledge per region
- **Time-based separation** - Historical vs current knowledge
- **Access control** - Public vs private knowledge bases

**Benefits:**
- Scalable across large knowledge bases
- Parallel searches
- Domain expertise
- Flexible routing

**When to use:**
- Multiple knowledge domains
- Large knowledge bases
- Different access levels
- Geographic distribution

## Hierarchical Knowledge

Organize knowledge in hierarchical structure for complex queries.

```python
kb_high_level = Knowledge(vector_db=LanceDb(uri="db_high", table_name="high_level"))
kb_detailed = Knowledge(vector_db=LanceDb(uri="db_detailed", table_name="detailed"))

agent = Agent(
    name="Hierarchical Agent",
    knowledge=[kb_high_level, kb_detailed],
    instructions="Search high-level first, then detailed if needed",
)
```

## Real-time Knowledge Updates

Update knowledge base in real-time from external sources.

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def update_knowledge():
    # Fetch new documents
    new_docs = await fetch_new_documents()

    # Add to knowledge base
    for doc in new_docs:
        knowledge.add_content(
            url=doc["url"],
            metadata=doc["metadata"],
        )

    # Rebuild index
    await knowledge.rebuild_index_async()

# Schedule updates every hour
scheduler.add_job(update_knowledge, 'interval', hours=1)
scheduler.start()
```

## Multi-Modal Knowledge

Search across text, images, and other modalities.

```python
from agno.vectordb.pinecone import Pinecone

knowledge = Knowledge(
    vector_db=Pinecone(
        index_name="multimodal_kb",
        dimension=1536,  # Text embeddings
    ),
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)

# Add multimodal content
knowledge.add_content(
    path="./document.pdf",  # Text + images
    multimodal=True,  # Extract and index images
)
```

## Knowledge Versioning

Track and query different versions of knowledge.

```python
# Add content with version
knowledge.add_content(
    text="API v1 documentation",
    metadata={"version": "1.0", "status": "deprecated"},
)

knowledge.add_content(
    text="API v2 documentation",
    metadata={"version": "2.0", "status": "current"},
)

# Query specific version
response = agent.run(
    "What's the API endpoint?",
    knowledge_filters={"version": "2.0", "status": "current"},
)
```

## Knowledge Analytics

Track search patterns and query effectiveness.

```python
from agno.knowledge.analytics import KnowledgeAnalytics

analytics = KnowledgeAnalytics(knowledge=knowledge)

# Track search performance
analytics.log_search(
    query="How do I deploy?",
    results_count=5,
    avg_relevance_score=0.85,
    user_satisfaction="good",
)

# Generate insights
insights = analytics.generate_insights(
    time_range="7d",
    metrics=["avg_latency", "avg_relevance", "top_queries"],
)
```

## Best Practices

1. **Use reranking for large KBs** - Improves retrieval quality significantly
2. **Distribute with teams** - Scale across multiple knowledge bases
3. **Version your knowledge** - Track updates and changes
4. **Monitor search analytics** - Understand query patterns
5. **Update regularly** - Keep knowledge fresh and accurate
6. **Plan for scale** - Choose architecture that grows with needs
7. **Test thoroughly** - Validate advanced features with real queries

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Usage Patterns](usage-patterns.md) - Agentic vs Traditional RAG
- [Filters](filters.md) - Metadata-based filtering
- [Vector Databases](vector-databases.md) - Vector database configuration
- [Teams](../basics/teams.md) - Team coordination patterns
- Online: [Reasoning Documentation](https://docs.agno.com/features/reasoning) - Reasoning capabilities
