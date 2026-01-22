# Adding Content

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Knowledge bases accept content from multiple sources: URLs, local files, raw text, and programmatic inputs.

## From URL

Add documents from web URLs:

```python
knowledge.add_content(url="https://example.com/document.pdf")
```

**Supported formats:**
- PDF (.pdf)
- Text (.txt, .md)
- HTML (automatically extracted)
- JSON (.json)

## From Local File

Add documents from local filesystem:

```python
knowledge.add_content(path="./documents/guide.pdf")
```

**Supported formats:**
- PDF (.pdf)
- Text (.txt, .md, .rst)
- JSON (.json)
- CSV (.csv)
- Markdown (.md)

## From Text

Add raw text directly:

```python
knowledge.add_content(text="Your content here...")
```

**Use cases:**
- Dynamic content generation
- Database query results
- API responses
- User-provided content

## From Multiple Sources

Add multiple documents in one call:

```python
knowledge.add_content(
    urls=[
        "https://example.com/doc1.pdf",
        "https://example.com/doc2.pdf",
    ],
    paths=["./local/doc.pdf", "./data.json"],
    text="Additional content...",
)
```

## Adding Content with Metadata

Attach metadata to documents for filtering:

```python
knowledge.add_content(
    url="https://example.com/engineering-guide.pdf",
    metadata={
        "department": "engineering",
        "access_level": "internal",
        "version": "1.2",
        "last_updated": "2025-01-15",
    },
)

knowledge.add_content(
    path="./public/docs/api.pdf",
    metadata={
        "department": "product",
        "access_level": "public",
        "doc_type": "api_reference",
    },
)
```

See [Filters](filters.md) for using metadata in searches.

## Adding Content by Directory

Add all documents from a directory:

```python
knowledge.add_directory(
    path="./documents",
    pattern="*.pdf",  # Only PDF files
    recursive=True,  # Include subdirectories
)
```

**Patterns:**
- `*.pdf` - All PDFs
- `*.md` - All Markdown files
- `*` - All files
- `docs/*.txt` - Specific directory

## Batch Processing

Process large document sets:

```python
# Add from CSV with document URLs
import pandas as pd

df = pd.read_csv("document_list.csv")

for _, row in df.iterrows():
    knowledge.add_content(
        url=row["url"],
        metadata={
            "category": row["category"],
            "author": row["author"],
        },
    )
```

## Content Updates

### Update Existing Content

```python
knowledge.add_content(
    url="https://example.com/doc.pdf",
    metadata={"version": "2.0"},  # New version
)
```

### Delete Content

```python
knowledge.delete_content(
    url="https://example.com/old-doc.pdf"
)
```

### Rebuild Index

After bulk updates, rebuild the search index:

```python
knowledge.rebuild_index()
```

## Reader Customization

Specify reader for specific content types:

```python
from agno.knowledge.reader import PDFReader, WebsiteReader

knowledge.add_content(
    url="https://example.com/doc.pdf",
    reader=PDFReader(extract_images=True)
)

knowledge.add_content(
    url="https://example.com/page",
    reader=WebsiteReader(extract_links=True)
)
```

## Content Validation

Validate content before adding:

```python
try:
    knowledge.add_content(
        url="https://example.com/doc.pdf",
        validate=True  # Validate before processing
    )
except ValueError as e:
    print(f"Validation failed: {e}")
```

## Best Practices

1. **Add metadata** - Enables filtering and better organization
2. **Batch when possible** - Multiple documents in one call is more efficient
3. **Validate content** - Check for errors before adding
4. **Rebuild index periodically** - After bulk updates
5. **Organize with directories** - Use directory structure for categorization
6. **Track versions** - Add version metadata for updates
7. **Set appropriate permissions** - Access level metadata for security

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Filters](filters.md) - Metadata-based filtering
- [Readers](readers.md) - PDF, web, and content readers
- [Chunking](chunking.md) - Document chunking strategies
