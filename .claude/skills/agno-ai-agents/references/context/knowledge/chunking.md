# Chunking

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Chunking strategies determine how documents are split into searchable pieces. The right strategy depends on content type and use case.

## Fixed-Size Chunking

Split documents into chunks of fixed size with overlap.

```python
from agno.knowledge.chunker import FixedSizeChunker

knowledge = Knowledge(
    chunker=FixedSizeChunker(chunk_size=500, chunk_overlap=50)
)
```

**When to use:**
- Simple documents
- Uniform content structure
- Quick to implement
- Predictable chunk sizes

**Parameters:**
- `chunk_size` - Number of tokens/characters per chunk
- `chunk_overlap` - Overlap between adjacent chunks (maintains context)

**Pros:**
- Simple and predictable
- Easy to control size
- Works well for most documents

**Cons:**
- May split at awkward positions
- Doesn't consider semantic boundaries
- Can break related information

## Recursive Chunking

Split documents using natural boundaries (paragraphs, sentences, etc.).

```python
from agno.knowledge.chunker import RecursiveChunker

knowledge = Knowledge(
    chunker=RecursiveChunker(
        separators=["\n\n", "\n", ". ", " "],
        chunk_size=500
    )
)
```

**When to use:**
- Documents with natural structure
- Want to preserve paragraphs
- Better semantic coherence
- Most common choice

**Parameters:**
- `separators` - List of separators in priority order (tried in order)
- `chunk_size` - Maximum chunk size

**Pros:**
- Preserves natural boundaries
- Better semantic coherence
- Maintains paragraph structure

**Cons:**
- More complex configuration
- May create variable chunk sizes
- Requires tuning separators

## Semantic Chunking

Split documents based on semantic meaning using embeddings.

```python
from agno.knowledge.chunker import SemanticChunker

knowledge = Knowledge(
    chunker=SemanticChunker(
        embedder=embedder,
        breakpoint_threshold_type="percentile"
    )
)
```

**When to use:**
- Complex documents
- Want topic-based chunks
- Need high semantic coherence
- Can afford processing time

**Parameters:**
- `embedder` - Embedding model for semantic analysis
- `breakpoint_threshold_type` - "percentile", "standard_deviation", or "interquartile"
- `breakpoint_threshold` - Sensitivity for chunk boundaries

**Pros:**
- Best semantic coherence
- Topic-based chunks
- Maintains related content together

**Cons:**
- Slower processing
- Requires embeddings
- More complex setup
- May create irregular chunks

## Agentic Chunking (Recommended)

Let agent decide optimal chunking based on content analysis.

```python
from agno.knowledge.chunker import AgenticChunker

knowledge = Knowledge(
    chunker=AgenticChunker(embedder=embedder)
)
```

**When to use:**
- Best quality required
- Mixed content types
- Want adaptive chunking
- Can afford processing time

**How it works:**
1. Agent analyzes document structure
2. Identifies optimal chunk boundaries
3. Creates chunks that maintain semantic coherence
4. Adapts strategy per document type

**Pros:**
- Best quality chunks
- Adapts to content
- Handles complex structures
- Highest semantic coherence

**Cons:**
- Slowest option
- Most complex
- Requires agent capabilities
- Higher cost

## Choosing the Right Chunker

| Content Type | Recommended | Alternative |
|--------------|-------------|-------------|
| Simple articles | Recursive | Fixed-Size |
| Technical docs | Recursive | Semantic |
| Legal contracts | Semantic | Agentic |
| Code/docs mixed | Agentic | Recursive |
| FAQ pages | Fixed-Size | Recursive |
| Research papers | Agentic | Semantic |

## Chunking Parameters

### Chunk Size

```python
# Small chunks for precise retrieval
FixedSizeChunker(chunk_size=200)

# Large chunks for broader context
FixedSizeChunker(chunk_size=1000)
```

**Guidelines:**
- Small (200-400): Precise retrieval, more chunks
- Medium (400-600): Balanced (most common)
- Large (600-1000): Broader context, fewer chunks

### Overlap

```python
# Small overlap
FixedSizeChunker(chunk_size=500, chunk_overlap=20)

# Large overlap for better context
FixedSizeChunker(chunk_size=500, chunk_overlap=100)
```

**Guidelines:**
- Small (0-20): Less duplication
- Medium (20-50): Balanced
- Large (50-100): Better context continuity

## Combining Chunkers

Use different chunkers for different content types:

```python
from agno.knowledge.chunker import (
    RecursiveChunker,
    FixedSizeChunker,
)

# Add docs with different chunkers
knowledge.add_content(
    path="./docs/faq.pdf",
    chunker=FixedSizeChunker(chunk_size=300)  # Small for FAQ
)

knowledge.add_content(
    path="./docs/guide.pdf",
    chunker=RecursiveChunker(chunk_size=500)  # Recursive for guide
)
```

## Best Practices

1. **Start with Recursive** - Good default for most documents
2. **Test retrieval quality** - Verify chunks produce good search results
3. **Use overlap** - Maintain context between chunks
4. **Match chunking to content** - Different strategies for different types
5. **Monitor performance** - Track chunking time and retrieval quality
6. **Consider agent needs** - Chunk size should match context window
7. **Iterate and tune** - Adjust based on actual query performance

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Adding Content](adding-content.md) - Adding documents
- [Search Types](search-types.md) - Search strategies
- [Vector Databases](vector-databases.md) - Vector database configuration
