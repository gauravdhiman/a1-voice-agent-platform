# Filters

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Knowledge filters allow you to retrieve documents based on metadata attributes, enabling fine-grained control over search results.

## Filter by Metadata

Filter search results using document metadata:

```python
# Add content with metadata
knowledge.add_content(
    text="Engineering documentation",
    metadata={"department": "engineering", "access_level": "internal"},
)

# Filter during search
response = agent.run(
    "What are the engineering guidelines?",
    knowledge_filters={"department": "engineering"},
)
```

## Multiple Filters

Combine multiple metadata conditions:

```python
response = agent.run(
    "Get product info",
    knowledge_filters={
        "department": "product",
        "access_level": "public",
    },
)
```

## Filter Operators

### Exact Match

```python
knowledge_filters={"status": "published"}
```

### Multiple Values (OR)

```python
knowledge_filters={"department": ["engineering", "product"]}
```

### Range Queries

```python
knowledge_filters={"version": {"$gte": "2.0"}}
```

### Negation

```python
knowledge_filters={"access_level": {"$ne": "internal"}}
```

## Common Metadata Patterns

### Access Control

```python
knowledge.add_content(
    url="https://example.com/internal-doc.pdf",
    metadata={
        "access_level": "internal",
        "user_group": "employees",
    },
)

knowledge.add_content(
    url="https://example.com/public-doc.pdf",
    metadata={
        "access_level": "public",
    },
)

# Only search public documents
response = agent.run(
    "What is your public API?",
    knowledge_filters={"access_level": "public"},
)
```

### Department/Domain

```python
knowledge.add_content(
    path="./engineering/api.pdf",
    metadata={
        "department": "engineering",
        "doc_type": "api_reference",
        "product": "core",
    },
)

knowledge.add_content(
    path="./sales/faq.pdf",
    metadata={
        "department": "sales",
        "doc_type": "faq",
        "product": "all",
    },
)

# Filter by department and doc type
response = agent.run(
    "What's the API endpoint?",
    knowledge_filters={
        "department": "engineering",
        "doc_type": "api_reference",
    },
)
```

### Version Control

```python
knowledge.add_content(
    text="API v1 documentation",
    metadata={"version": "1.0", "status": "deprecated"},
)

knowledge.add_content(
    text="API v2 documentation",
    metadata={"version": "2.0", "status": "current"},
)

# Only search current version
response = agent.run(
    "How do I authenticate?",
    knowledge_filters={
        "version": "2.0",
        "status": "current",
    },
)
```

### Time-Based

```python
from datetime import datetime

knowledge.add_content(
    text="Quarterly report Q4",
    metadata={
        "year": "2025",
        "quarter": "Q4",
        "date": "2025-01-15",
    },
)

# Filter by year and quarter
response = agent.run(
    "What were the Q4 results?",
    knowledge_filters={
        "year": "2025",
        "quarter": "Q4",
    },
)
```

## Dynamic Filters

Generate filters based on user context:

```python
def get_user_filters(user_role):
    if user_role == "engineer":
        return {"department": "engineering", "access_level": "internal"}
    elif user_role == "customer":
        return {"access_level": "public"}
    else:
        return {}

# Apply user-specific filters
user_role = "engineer"  # From auth/session
response = agent.run(
    "How do I deploy?",
    knowledge_filters=get_user_filters(user_role),
)
```

## Filters in Teams

Apply different filters per agent:

```python
kb_internal = Knowledge(...)
kb_public = Knowledge(...)

internal_agent = Agent(
    name="Internal Support",
    knowledge=kb_internal,
    instructions="Search internal documentation",
)

public_agent = Agent(
    name="Public Support",
    knowledge=kb_public,
    instructions="Search public documentation",
)

team = Team(
    name="Support Team",
    members=[internal_agent, public_agent],
    instructions="Internal agent handles internal queries, public agent handles others",
)
```

## Combining Filters with Search Types

Filters work with all search types:

```python
# Hybrid search with filters
knowledge = Knowledge(
    vector_db=LanceDb(..., search_type=SearchType.hybrid)
)

response = agent.run(
    "Find API documentation",
    knowledge_filters={"doc_type": "api_reference"},
)

# Vector search with filters
response = agent.run(
    "Find API documentation",
    search_type=SearchType.vector,
    knowledge_filters={"doc_type": "api_reference"},
)
```

## Best Practices

1. **Design metadata schema** - Plan metadata structure before adding content
2. **Use consistent naming** - Standardize metadata keys and values
3. **Add access control** - Use filters for permission-based access
4. **Index filter fields** - Ensure metadata fields are indexed
5. **Test filter combinations** - Validate complex filter queries
6. **Document metadata schema** - Keep team informed of structure
7. **Use hierarchical metadata** - Group related filters (department, team, project)

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Adding Content](adding-content.md) - Adding metadata to documents
- [Usage Patterns](usage-patterns.md) - Using filters in queries
- [Vector Databases](vector-databases.md) - Vector database configuration
