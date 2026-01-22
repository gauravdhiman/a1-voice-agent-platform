# Cookbook - Online Resources

**See parent [../../SKILL.md](../../SKILL.md) for overview and quickstart.**

## Overview

This directory references Agno's extensive cookbook with 2000+ production-ready examples covering 40+ models, 100+ tools, and 18 vector databases.

## Cookbook Overview

- **URL**: [Cookbook Overview](https://docs.agno.com/cookbook/overview)
- **GitHub**: [agno/cookbook](https://github.com/agno-agi/agno/tree/main/cookbook)
- **Description**: Ready-to-copy examples for learning and production

## By the Numbers

| Category | Count | Highlights |
|----------|-------|------------|
| Examples | 2000+ | Agents, teams, workflows, knowledge, RAG |
| Model Providers | 40+ | OpenAI, Anthropic, Google, Groq, Mistral, local |
| Storage Backends | 12 | PostgreSQL, SQLite, MongoDB, Redis, DynamoDB |
| Vector Databases | 18 | PgVector, Pinecone, Qdrant, Weaviate, Milvus |
| Built-in Tools | 100+ | Search, databases, APIs, social media, AI/media |

## Categories

### Models
- **Overview**: [Models Overview](https://docs.agno.com/cookbook/models/overview)
- **Examples**:
  - [OpenAI](https://docs.agno.com/cookbook/models/openai) - GPT-4, GPT-3.5, responses API
  - [Anthropic](https://docs.agno.com/cookbook/models/anthropic) - Claude 3.5 Sonnet, Opus
  - [Google](https://docs.agno.com/cookbook/models/google) - Gemini Pro, Flash
  - [Open Source](https://docs.agno.com/cookbook/models/open-source) - Llama 3, Mistral
  - [Enterprise](https://docs.agno.com/cookbook/models/enterprise) - Azure, AWS, Vertex
  - [Local](https://docs.agno.com/cookbook/models/local) - Ollama, vLLM

### Tools
- **Overview**: [Tools Overview](https://docs.agno.com/cookbook/tools/overview)
- **Examples**:
  - [MCP](https://docs.agno.com/cookbook/tools/mcp) - Model Context Protocol tools
  - [Custom Tools](https://docs.agno.com/cookbook/tools/custom-tools) - Creating custom tools
  - [Tool Hooks](https://docs.agno.com/cookbook/tools/tool-hooks) - Tool lifecycle hooks
  - [Built-in Tools](https://docs.agno.com/cookbook/tools/built-in) - Search, databases, APIs

### Knowledge & RAG
- **Overview**: [Knowledge Overview](https://docs.agno.com/cookbook/knowledge/overview)
- **Examples**:
  - [Vector Databases](https://docs.agno.com/cookbook/knowledge/vector-databases) - RAG with PgVector, Pinecone, etc.
  - [Embedders](https://docs.agno.com/cookbook/knowledge/embedders) - OpenAI, Cohere, local embedders
  - [Readers](https://docs.agno.com/cookbook/knowledge/readers) - PDF, web, file readers
  - [Chunking](https://docs.agno.com/cookbook/knowledge/chunking) - Text chunking strategies

### Storage
- **Overview**: [Storage Overview](https://docs.agno.com/cookbook/storage/overview)
- **Examples**: PostgreSQL, SQLite, MongoDB, Redis, DynamoDB

### Agents
- **Overview**: [Agents Overview](https://docs.agno.com/cookbook/agents/overview)
- **Examples**:
  - Knowledge & RAG
  - Research & Analysis
  - Multimodal
  - Integrations

### Teams
- **Overview**: [Teams Overview](https://docs.agno.com/cookbook/teams/overview)
- **Examples**:
  - Content & Research
  - Support & Routing

### Workflows
- **Overview**: [Workflows Overview](https://docs.agno.com/cookbook/workflows/overview)
- **Examples**:
  - [Blog Post Generator](https://docs.agno.com/cookbook/workflows/blog-post-generator)
  - [Company Description Workflow](https://docs.agno.com/cookbook/workflows/company-description)
  - [Employee Recruiter](https://docs.agno.com/cookbook/workflows/employee-recruiter)
  - [Notion Knowledge Manager](https://docs.agno.com/cookbook/workflows/notion-knowledge-manager)

### Learning
- **Overview**: [Learning Overview](https://docs.agno.com/cookbook/learning/overview)
- **Examples**:
  - [Personal Assistant](https://docs.agno.com/cookbook/learning/personal-assistant)
  - [Support Agent](https://docs.agno.com/cookbook/learning/support-agent)

### Streamlit Apps
- **Overview**: [Streamlit Overview](https://docs.agno.com/cookbook/streamlit/overview)
- **Examples**:
  - [Agentic RAG](https://docs.agno.com/cookbook/streamlit/agentic-rag)
  - [SQL Agent](https://docs.agno.com/cookbook/streamlit/text-to-sql)
  - [Sage: Answer Engine](https://docs.agno.com/cookbook/streamlit/answer-engine)

## Running the Cookbook

### Clone and Run

```bash
git clone https://github.com/agno-agi/agno.git
cd agno/cookbook

# Models
python 92_models/openai/responses/basic.py
python 92_models/anthropic/basic.py

# Tools
python 90_tools/mcp/filesystem.py

# Knowledge
python 07_knowledge/vector_db/pgvector/pgvector_db.py
```

### Finding Examples

1. Browse the [Cookbook Overview](https://docs.agno.com/cookbook/overview)
2. Navigate to the category you need
3. Find the example matching your use case
4. Click the GitHub link to view source
5. Copy and adapt to your project

## Popular Examples

### Simple Agent with OpenAI
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    name="Simple Agent",
    model=OpenAIChat(id="gpt-4"),
    instructions=["You are a helpful assistant."],
)

response = agent.run("Hello!")
print(response.content)
```

### RAG with Pinecone
```python
from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.vectordb.pinecone import PineconeDb

knowledge = Knowledge(
    vector_db=PineconeDb(
        index_name="my-knowledge",
        dimension=1536,
    ),
    reader=PdfReader(),
)

agent = Agent(
    name="RAG Agent",
    knowledge=knowledge,
    instructions=["Answer questions using the knowledge base."],
)

response = agent.run("What is the document about?")
```

### Team with Supervisor Pattern
```python
from agno.team import Team
from agno.agent import Agent

researcher = Agent(name="Researcher", instructions=["Research topics"])
writer = Agent(name="Writer", instructions=["Write content"])

team = Team(
    name="Content Team",
    members=[researcher, writer],
    instructions=["Coordinate research and writing"],
)

response = team.run("Write a blog post about AI")
```

## Best Practices

1. **Start Simple**: Begin with basic examples before complex workflows
2. **Read Documentation**: Each example links to detailed documentation
3. **Adapt Carefully**: Modify examples to fit your specific use case
4. **Test Locally**: Run examples locally to understand behavior
5. **Version Compatibility**: Check Agno version compatibility
6. **Contribute**: Share your examples with the community

## See Also

- [Basics - Agents](../basics/agents.md) - Agent creation and patterns
- [Basics - Teams](../basics/teams.md) - Team coordination patterns
- [Basics - Workflows](../basics/workflows.md) - Workflow orchestration
- [Context - Knowledge](../context/knowledge.md) - RAG implementation
- [Integrations](../integrations/online-resources.md) - Model providers and databases
