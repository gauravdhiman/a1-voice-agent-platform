# Readers

**See parent [overview.md](overview.md) for knowledge overview.**

## Overview

Readers parse different file formats and content sources, enabling knowledge bases to ingest documents from various sources.

## PDF Reader

Extract text from PDF documents.

```python
from agno.knowledge.reader import PDFReader

knowledge = Knowledge(
    reader=PDFReader(),
)

knowledge.add_content(path="./document.pdf")
```

**Advanced PDF options:**

```python
PDFReader(
    extract_images=True,  # Extract text from images
    extract_tables=True,  # Extract table data
    page_range=(1, 10),  # Specific pages
    ocr_enabled=False,  # OCR for scanned PDFs
)
```

**When to use:**
- Documentation manuals
- Research papers
- Technical specifications
- Contracts and legal documents

## Website Reader

Extract content from web pages.

```python
from agno.knowledge.reader import WebsiteReader

knowledge = Knowledge(
    reader=WebsiteReader(),
)

knowledge.add_content(url="https://example.com/page")
```

**Advanced web options:**

```python
WebsiteReader(
    extract_links=True,  # Include links in content
    extract_images=False,  # Skip image alt text
    exclude_selector=".sidebar, .footer",  # CSS selectors to exclude
    include_selector=".main-content, article",  # CSS selectors to include
)
```

**When to use:**
- Documentation sites
- Blog posts
- Articles
- Public knowledge bases

## Text Reader

Default reader for plain text files.

```python
from agno.knowledge.reader import TextReader

knowledge = Knowledge(
    reader=TextReader(),
)

knowledge.add_content(path="./document.txt")
```

**Supported formats:**
- Text (.txt)
- Markdown (.md)
- ReStructuredText (.rst)
- HTML (.html)

**When to use:**
- Configuration files
- Code documentation
- README files
- Plain text notes

## JSON Reader

Parse JSON files for structured data.

```python
from agno.knowledge.reader import JSONReader

knowledge = Knowledge(
    reader=JSONReader(
        text_field="content",  # Field containing text
        metadata_fields=["title", "category"],  # Fields to add as metadata
    ),
)

knowledge.add_content(path="./data.json")
```

**When to use:**
- Structured data
- Database exports
- API responses
- Configuration data

## CSV Reader

Process CSV files row by row.

```python
from agno.knowledge.reader import CSVReader

knowledge = Knowledge(
    reader=CSVReader(
        text_field="description",  # Field containing text
        metadata_fields=["id", "category", "status"],
    ),
)

knowledge.add_content(path="./products.csv")
```

**When to use:**
- Product catalogs
- User data
- Transaction records
- Structured datasets

## Multiple Content Types

Handle multiple formats in one knowledge base:

```python
from agno.knowledge.reader import PDFReader, WebsiteReader, TextReader

knowledge = Knowledge()  # Default reader (auto-detect)

# Add different content types
knowledge.add_content(
    paths=["./doc.pdf", "./notes.md", "./data.json"],
    urls=["https://example.com"],
    text="Raw text content",
)
```

## Custom Reader

Create custom reader for specific formats:

```python
from agno.knowledge.reader import Reader

class CustomReader(Reader):
    """Custom reader for proprietary format."""

    def read(self, content):
        # Parse your custom format
        text = self._parse_content(content)
        metadata = self._extract_metadata(content)

        return [
            {
                "text": text,
                "metadata": metadata,
            }
        ]

    def _parse_content(self, content):
        # Your parsing logic
        pass

    def _extract_metadata(self, content):
        # Your metadata extraction logic
        pass

knowledge = Knowledge(reader=CustomReader())
```

## Reader Options

### Encoding

```python
TextReader(encoding="utf-8")
```

### Error Handling

```python
PDFReader(
    skip_corrupted_pages=True,
    on_error="skip"  # or "raise" or "warn"
)
```

### Content Cleaning

```python
WebsiteReader(
    remove_headers=True,
    remove_footers=True,
    normalize_whitespace=True,
)
```

## Best Practices

1. **Use appropriate reader** - Match reader to file format
2. **Handle errors gracefully** - Set `on_error="skip"` for bulk operations
3. **Extract metadata** - Use metadata fields for filtering
4. **Clean content** - Remove headers, footers, navigation
5. **Test with sample files** - Validate extraction before bulk processing
6. **Combine readers** - Use multiple readers for diverse content
7. **Create custom readers** - For proprietary formats

## See Also

- [Overview](overview.md) - Knowledge base overview
- [Adding Content](adding-content.md) - Adding documents to knowledge base
- [Chunking](chunking.md) - Document chunking strategies
