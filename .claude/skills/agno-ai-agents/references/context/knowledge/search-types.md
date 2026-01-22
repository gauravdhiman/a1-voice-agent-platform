# Search Types

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Knowledge bases support three search types for retrieving documents. Choose based on your use case and content characteristics.

## Hybrid Search (Recommended)

Combines semantic and keyword search for best results.

```python
from agno.vectordb.lancedb import LanceDb, SearchType

knowledge = Knowledge(
    vector_db=LanceDb(..., search_type=SearchType.hybrid)
)
```

**When to use:**
- General-purpose knowledge bases
- Documents with both natural language and specific keywords
- Unknown query patterns
- Want best retrieval quality

**Pros:**
- Combines semantic understanding with keyword matching
- Handles synonyms and related concepts
- Good for varied query styles
- Most reliable overall approach

**Cons:**
- Slightly slower than vector-only search
- May return more results to review

## Vector Search

Pure semantic search using embeddings.

```python
from agno.vectordb.lancedb import LanceDb, SearchType

knowledge = Knowledge(
    vector_db=LanceDb(..., search_type=SearchType.vector)
)
```

**When to use:**
- Natural language queries
- Concept-based retrieval
- Synonym-rich content
- Queries using varied vocabulary

**Pros:**
- Understands semantic meaning
- Handles synonyms and paraphrases
- Good for conceptual queries
- Fast retrieval with vector indexes

**Cons:**
- Misses exact keyword matches
- Struggles with specific technical terms
- May retrieve irrelevant but semantically similar content

## Keyword Search

Pure keyword-based search.

```python
from agno.vectordb.lancedb import LanceDb, SearchType

knowledge = Knowledge(
    vector_db=LanceDb(..., search_type=SearchType.keyword)
)
```

**When to use:**
- Technical documentation with specific terms
- Product names, IDs, codes
- Structured data fields
- Queries requiring exact matches

**Pros:**
- Precise keyword matching
- Fast for exact term searches
- Good for technical content
- Deterministic results

**Cons:**
- No semantic understanding
- Misses synonyms and related concepts
- Requires exact keyword matches
- Poor for natural language queries

## Choosing the Right Search Type

| Query Type | Recommended | Alternative |
|------------|-------------|-------------|
| "What's the API for..." | Hybrid | Vector |
| "Find error code 500" | Keyword | Hybrid |
| "How do I reset password?" | Hybrid | Vector |
| "Product ID: XYZ-123" | Keyword | - |
| "Similar features to X" | Vector | Hybrid |
| "Troubleshooting steps" | Hybrid | Vector |

## Search Parameters

### Top K Results

Control number of results returned:

```python
from agno.vectordb.lancedb import LanceDb

knowledge = Knowledge(
    vector_db=LanceDb(..., top_k=10)  # Return 10 results
)
```

### Search Score Threshold

Filter results by relevance:

```python
knowledge = Knowledge(
    vector_db=LanceDb(..., search_score_threshold=0.7)
)
```

### Hybrid Search Weights

Adjust semantic vs keyword weighting:

```python
knowledge = Knowledge(
    vector_db=LanceDb(
        ...,
        hybrid_search_weights={"semantic": 0.6, "keyword": 0.4}
    )
)
```

## Best Practices

1. **Start with hybrid** - Default to hybrid search for best results
2. **Test with real queries** - Validate retrieval with actual user questions
3. **Monitor relevance** - Track search quality and adjust parameters
4. **Use metadata filters** - Combine search types with filtering
5. **Consider query type** - Adjust search type based on query patterns

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Filters](filters.md) - Metadata-based filtering
- [Chunking](chunking.md) - Document chunking strategies
- [Vector Databases](vector-databases.md) - LanceDB, PgVector, Qdrant, Pinecone
