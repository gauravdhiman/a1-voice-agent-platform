# Vector Databases

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Vector databases store and search document embeddings for semantic retrieval. Choose based on scale, infrastructure, and cost requirements.

## LanceDB

Embedded vector database, ideal for local development and small-scale deployments.

```python
from agno.vectordb.lancedb import LanceDb

knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="docs",
        search_type=SearchType.hybrid,
    ),
)
```

**When to use:**
- Local development
- Small to medium datasets (< 1M documents)
- Want zero infrastructure
- Embedded applications

**Pros:**
- Zero setup, embedded
- Fast for small datasets
- No external dependencies
- Open source

**Cons:**
- Limited scalability
- No built-in replication
- Single server only

**Advanced options:**

```python
LanceDb(
    uri="s3://bucket/lancedb",  # Cloud storage
    table_name="docs",
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    top_k=10,
)
```

## PgVector

PostgreSQL extension for vector search, ideal if you already use PostgreSQL.

```python
from agno.vectordb.pgvector import PgVector

knowledge = Knowledge(
    vector_db=PgVector(
        connection_string="postgresql://user:pass@localhost:5432/db",
        table_name="docs",
        search_type=SearchType.hybrid,
    ),
)
```

**When to use:**
- Already using PostgreSQL
- Need ACID transactions
- Want RDBMS capabilities
- Medium to large datasets

**Pros:**
- Postgres integration
- ACID compliance
- SQL queries possible
- Scalable
- Open source

**Cons:**
- Requires Postgres setup
- Performance tuning needed
- Slower than specialized vector DBs

## Qdrant

High-performance vector database with advanced filtering capabilities.

```python
from agno.vectordb.qdrant import Qdrant

knowledge = Knowledge(
    vector_db=Qdrant(
        location="http://localhost:6333",
        collection_name="docs",
        search_type=SearchType.hybrid,
    ),
)
```

**When to use:**
- Need advanced filtering
- High performance required
- Large-scale deployments
- Production workloads

**Pros:**
- Excellent performance
- Advanced filtering
- Cloud or self-hosted
- Good scalability
- Open source

**Cons:**
- Separate infrastructure
- Setup complexity
- Learning curve

**Advanced options:**

```python
Qdrant(
    location="https://your-cluster.qdrant.io:6333",
    api_key="your-api-key",
    collection_name="docs",
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    top_k=10,
)
```

## Pinecone

Managed vector database service with minimal setup.

```python
from agno.vectordb.pinecone import Pinecone

knowledge = Knowledge(
    vector_db=Pinecone(
        index_name="docs",
        api_key="your-api-key",
        search_type=SearchType.hybrid,
    ),
)
```

**When to use:**
- Want managed service
- Minimal infrastructure
- Enterprise requirements
- Need SLA guarantees

**Pros:**
- Fully managed
- No infrastructure
- Auto-scaling
- Excellent performance
- Easy setup

**Cons:**
- Cost at scale
- Vendor lock-in
- Limited control

**Advanced options:**

```python
Pinecone(
    index_name="docs",
    api_key="your-api-key",
    environment="us-east-1-aws",
    dimension=1536,  # Match embedder
    metric="cosine",
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

## Choosing the Right Vector Database

| Need | Recommended |
|------|-------------|
| Local development | LanceDB |
| Small production (< 1M docs) | LanceDB or PgVector |
| Medium production (1-10M docs) | PgVector or Qdrant |
| Large production (10M+ docs) | Qdrant or Pinecone |
| Already use Postgres | PgVector |
| Want managed service | Pinecone |
| Open source requirement | LanceDB, PgVector, Qdrant |

## Performance Considerations

### Indexing

```python
# Build index for faster search
vector_db.create_index(
    index_type="HNSW",
    M=16,  # Number of connections per node
    ef_construction=100,  # Index build speed vs quality
)
```

### Batch Insertions

```python
# Insert multiple documents efficiently
documents = [
    {"text": "Doc 1", "metadata": {"id": 1}},
    {"text": "Doc 2", "metadata": {"id": 2}},
]

knowledge.add_documents(documents)
```

## Best Practices

1. **Start with LanceDB** - Easy setup for development
2. **Match embedder dimension** - Vector DB must match embedder
3. **Use appropriate metric** - Cosine for most cases
4. **Test with real data** - Validate performance before production
5. **Monitor query latency** - Track search performance
6. **Consider total cost** - Including infrastructure and maintenance
7. **Plan for growth** - Scalability requirements

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Search Types](search-types.md) - Hybrid, vector, keyword search
- [Integrations](../integrations/online-resources.md) - Model and database providers
- Online: [Vector Databases](https://docs.agno.com/integrations/vectordbs/overview) - Official vector database documentation
