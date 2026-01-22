# Integrations - Online Resources

**See parent [../../SKILL.md](../../SKILL.md) for overview and quickstart.**

## Overview

This directory references Agno's extensive integration ecosystem online. Agno supports 40+ model providers, 12 databases, 18 vector databases, and 100+ tools.

## Model Providers

### Overview
- **URL**: [Model Index](https://docs.agno.com/integrations/models/model-index)
- **Description**: Index of all supported model providers

### Native Model Providers
- **Anthropic**: [Documentation](https://docs.agno.com/integrations/models/anthropic)
- **Cohere**: [Documentation](https://docs.agno.com/integrations/models/cohere)
- **DeepSeek**: [Documentation](https://docs.agno.com/integrations/models/deepseek)
- **Google Gemini**: [Documentation](https://docs.agno.com/integrations/models/google-gemini)
- **Meta AI**: [Documentation](https://docs.agno.com/integrations/models/meta)
- **Mistral**: [Documentation](https://docs.agno.com/integrations/models/mistral)
- **OpenAI**: [Documentation](https://docs.agno.com/integrations/models/openai)

### Local Model Providers
- **Ollama**: [Documentation](https://docs.agno.com/integrations/models/ollama)
- **vLLM**: [Documentation](https://docs.agno.com/integrations/models/vllm)
- **Llama.cpp**: [Documentation](https://docs.agno.com/integrations/models/llamacpp)

### Cloud Model Providers
- **Azure OpenAI**: [Documentation](https://docs.agno.com/integrations/models/azure-openai)
- **AWS Bedrock**: [Documentation](https://docs.agno.com/integrations/models/aws-bedrock)
- **Google Vertex AI**: [Documentation](https://docs.agno.com/integrations/models/google-vertex)

### Model Gateways & Aggregators
- **Portkey**: [Documentation](https://docs.agno.com/integrations/models/portkey)
- **LiteLLM**: [Documentation](https://docs.agno.com/integrations/models/litellm)
- **Together AI**: [Documentation](https://docs.agno.com/integrations/models/together)
- **Groq**: [Documentation](https://docs.agno.com/integrations/models/groq)

## Database Providers

### Overview
- **URL**: [Database Providers](https://docs.agno.com/integrations/databases/overview)
- **Description**: Persistent storage for agent sessions and knowledge

### Supported Databases
- **PostgreSQL**: [Documentation](https://docs.agno.com/integrations/databases/postgresql)
- **SQLite**: [Documentation](https://docs.agno.com/integrations/databases/sqlite)
- **MongoDB**: [Documentation](https://docs.agno.com/integrations/databases/mongodb)
- **Redis**: [Documentation](https://docs.agno.com/integrations/databases/redis)
- **DynamoDB**: [Documentation](https://docs.agno.com/integrations/databases/dynamodb)

## Vector Databases

### Overview
- **URL**: [Vector Databases](https://docs.agno.com/integrations/vectordbs/overview)
- **Description**: Vector databases for RAG and knowledge retrieval

### Supported Vector Databases
- **PgVector**: [Documentation](https://docs.agno.com/integrations/vectordbs/pgvector)
- **Pinecone**: [Documentation](https://docs.agno.com/integrations/vectordbs/pinecone)
- **Qdrant**: [Documentation](https://docs.agno.com/integrations/vectordbs/qdrant)
- **Weaviate**: [Documentation](https://docs.agno.com/integrations/vectordbs/weaviate)
- **Milvus**: [Documentation](https://docs.agno.com/integrations/vectordbs/milvus)
- **Chroma**: [Documentation](https://docs.agno.com/integrations/vectordbs/chroma)
- **LanceDB**: [Documentation](https://docs.agno.com/integrations/vectordbs/lancedb)

## Toolkits

### Overview
- **URL**: [Toolkit Index](https://docs.agno.com/integrations/toolkits/overview)
- **Description**: 100+ pre-built toolkits for common tasks

### Popular Toolkits
- **Search**: Exa, DuckDuckGo, Baidu, Arxiv
- **Social**: Twitter, Reddit, LinkedIn
- **Data**: CSV, JSON, SQL databases
- **Web Scraping**: BeautifulSoup, Selenium, Playwright
- **File Generation**: PDF, Excel, Markdown
- **Local**: Filesystem, System commands

## Memory Integrations

### Overview
- **URL**: [Memory](https://docs.agno.com/integrations/memory/overview)
- **Description**: Persistent memory for agent learning and retention

### Supported Memory Backends
- **PostgreSQL**: [Documentation](https://docs.agno.com/integrations/memory/postgresql)
- **MongoDB**: [Documentation](https://docs.agno.com/integrations/memory/mongodb)
- **Redis**: [Documentation](https://docs.agno.com/integrations/memory/redis)

## Observability

### Overview
- **URL**: [OpenTelemetry](https://docs.agno.com/integrations/observability/overview)
- **Description**: Tracing and monitoring for production deployments

### Supported Platforms
- **AgentOps**: [Documentation](https://docs.agno.com/integrations/observability/agentops)
- **Arize**: [Documentation](https://docs.agno.com/integrations/observability/arize)
- **Langfuse**: [Documentation](https://docs.agno.com/integrations/observability/langfuse)
- **LangSmith**: [Documentation](https://docs.agno.com/integrations/observability/langsmith)
- **Weave**: [Documentation](https://docs.agno.com/integrations/observability/weave)
- **Traceloop**: [Documentation](https://docs.agno.com/integrations/observability/traceloop)

## Quick Examples

### Using OpenAI Model

```python
from agno.models.openai import OpenAIResponses

agent = Agent(
    name="OpenAI Agent",
    model=OpenAIResponses(id="gpt-4"),
)
```

### Using Anthropic Model

```python
from agno.models.anthropic import Claude

agent = Agent(
    name="Claude Agent",
    model=Claude(id="claude-3-5-sonnet-20241022"),
)
```

### Using PostgreSQL Database

```python
from agno.db.postgres import PostgresDb

agent = Agent(
    name="Persistent Agent",
    db=PostgresDb(
        uri="postgresql://user:pass@localhost:5432/agno",
        table_name="agent_sessions",
    ),
)
```

### Using Pinecone Vector DB

```python
from agno.vectordb.pinecone import PineconeDb

knowledge = Knowledge(
    vector_db=PineconeDb(
        index_name="agno-knowledge",
        dimension=1536,
    ),
)
```

### Using Exa Search Toolkit

```python
from agno.tools.exa import ExaTools

agent = Agent(
    name="Search Agent",
    tools=[ExaTools()],
)
```

## Best Practices

1. **Model Selection**: Choose based on task complexity and cost
2. **Database**: Use PostgreSQL/SQLite for development, Redis for caching
3. **Vector DB**: Choose based on scale and existing infrastructure
4. **Toolkits**: Use pre-built toolkits when available
5. **Observability**: Enable tracing in production
6. **Memory**: Use persistent memory for long-running agents

## See Also

- [Context - Knowledge](../context/knowledge.md) - RAG implementation
- [Tools - Overview](../tools/overview.md) - Tool creation and usage
- [Features](../features/online-resources.md) - Evals, reasoning, multimodal
- [Cookbook](../cookbook/online-resources.md) - Ready-to-use examples
