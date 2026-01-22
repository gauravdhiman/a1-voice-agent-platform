# AgentOS - Production Deployment

**See parent [SKILL.md](../SKILL.md) for overview and quickstart.**

## AgentOS Overview

AgentOS is a production service layer that turns your Agents, Teams, and Workflows into a deployable FastAPI application with pre-built endpoints, authentication, interfaces, and observability.

## Quick Start

### Basic AgentOS

```python
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS

agent = Agent(
    name="My Agent",
    model=OpenAIResponses(id="gpt-4o"),
    instructions="You are helpful",
)

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()

# Save as agent.py and run:
# fastapi dev agent.py
```

### AgentOS with Database

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS

db = SqliteDb(db_file="agents.db")

agent = Agent(
    name="My Agent",
    model=OpenAIResponses(id="gpt-4o"),
    db=db,  # Enables persistence
)

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()
```

### AgentOS with Multiple Components

```python
from agno.agent import Agent
from agno.team import Team
from agno.workflow import Workflow
from agno.os import AgentOS

agent1 = Agent(name="Agent 1")
agent2 = Agent(name="Agent 2")
team = Team(name="Team 1", members=[agent1, agent2])
workflow = Workflow(name="Workflow 1", steps=[agent1])

agent_os = AgentOS(
    agents=[agent1, agent2],
    teams=[team],
    workflows=[workflow],
)
app = agent_os.get_app()
```

## Running AgentOS

### Development Mode

```bash
fastapi dev agent.py
```

Starts at `http://localhost:8000` with auto-reload.

### Production Mode

```bash
uvicorn agent:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agent.py .

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t agno-agentos .
docker run -p 8000:8000 agno-agentos
```

## Pre-built API Endpoints

### Run Agent

```bash
POST /v1/agents/{agent_id}/run
{
    "message": "Hello!",
    "user_id": "user@example.com",
    "session_id": "session_123"
}
```

### Run Agent (Streaming)

```bash
POST /v1/agents/{agent_id}/run
{
    "message": "Hello!",
    "stream": true
}
```

Returns SSE stream of events.

### Run Team

```bash
POST /v1/teams/{team_id}/run
{
    "message": "Research this topic"
}
```

### Run Workflow

```bash
POST /v1/workflows/{workflow_id}/run
{
    "message": "Execute workflow"
}
```

### Get Sessions

```bash
GET /v1/sessions?user_id=user@example.com
```

### Create Session

```bash
POST /v1/sessions
{
    "user_id": "user@example.com",
    "session_name": "My Session"
}
```

### Search Knowledge

```bash
POST /v1/knowledge/search
{
    "query": "What is Agno?",
    "limit": 5
}
```

### Upload Knowledge

```bash
POST /v1/knowledge/upload
{
    "content": "Document content here..."
}
```

### Get Memories

```bash
GET /v1/memories?user_id=user@example.com
```

### Create Memory

```bash
POST /v1/memories
{
    "user_id": "user@example.com",
    "memory": "User prefers concise answers"
}
```

See API docs at `http://localhost:8000/docs` for complete endpoint reference.

## Configuration

### YAML Configuration

Create `agentos_config.yaml`:

```yaml
chat:
  quick_prompts:
    my-agent:
      - "What can you do?"
      - "How can you help me?"

memory:
  display_name: "User Memory"
  dbs:
      - db_id: db-0001
        tables: ["custom_memory_table"]
        domain_config:
          display_name: "Production Memories"

knowledge:
  display_name: "Knowledge Base"
  dbs:
      - db_id: db-0001
        domain_config:
          display_name: "Product Docs"

session:
  display_name: "User Sessions"

evals:
  display_name: "Evaluations"
  available_models:
      - "openai:gpt-4"
      - "anthropic:claude-sonnet-4"
```

Use with AgentOS:

```python
from agno.os import AgentOS
from agno.os.config import AgentOSConfig

agent_os = AgentOS(
    agents=[agent],
    config="agentos_config.yaml",  # Path to YAML file
)
```

### Python Configuration

```python
from agno.os.config import (
    AgentOSConfig,
    ChatConfig,
    MemoryConfig,
    KnowledgeConfig,
)

agent_os = AgentOS(
    agents=[agent],
    config=AgentOSConfig(
        chat=ChatConfig(
            quick_prompts={
                "my-agent": [
                    "What can you do?",
                    "How can you help me?",
                ],
            },
        ),
        memory=MemoryConfig(
            display_name="User Memory",
        ),
    ),
)
```

## Interfaces

### A2A Interface

Enable A2A protocol for cross-framework communication:

```python
from agno.os import AgentOS

agent_os = AgentOS(
    agents=[agent],
    a2a_interface=True,  # Enable A2A
    a2a_agents=["my-agent"],  # Expose specific agents
)
```

**Connect via A2A client:**

```python
from agno.client.a2a import A2AClient

client = A2AClient("http://localhost:8000/a2a/agents/my-agent")
result = await client.send_message("Hello!")
print(result.content)
```

### AG-UI Interface

AgentOS UI connects directly to your runtime:

1. Open [os.agno.com](https://os.agno.com)
2. Add new OS → Local
3. Enter endpoint: `http://localhost:8000`
4. Connect

**Features:**
- Live agent monitoring
- Session browsing
- Knowledge management
- Memory inspection
- Trace viewing

### Slack Interface

```python
from agno.os import AgentOS
from agno.os.interfaces import SlackInterface

slack_interface = SlackInterface(
    bot_token="xoxb-...",
    signing_secret="...",
)

agent_os = AgentOS(
    agents=[agent],
    interfaces=[slack_interface],
)
```

### WhatsApp Interface

```python
from agno.os.interfaces import WhatsAppInterface

whatsapp_interface = WhatsAppInterface(
    phone_number_id="...",
    access_token="...",
)

agent_os = AgentOS(
    agents=[agent],
    interfaces=[whatsapp_interface],
)
```

## Security

### JWT Authentication

```python
from agno.os.middleware import JWTMiddleware

jwt_middleware = JWTMiddleware(
    secret_key="your-secret-key",
    algorithm="HS256",
    token_prefix="Bearer",
)

agent_os = AgentOS(
    agents=[agent],
    middleware=[jwt_middleware],
)
```

### RBAC (Role-Based Access Control)

```python
from agno.os.security import RBAC

rbac = RBAC(
    scopes={
        "admin": ["*"],  # Full access
        "user": ["read:agents", "run:agents"],
        "readonly": ["read:agents"],
    },
)

agent_os = AgentOS(
    agents=[agent],
    rbac=rbac,
)
```

### Custom Middleware

```python
from fastapi import Request

async def custom_middleware(request: Request, call_next):
    """Custom middleware function."""
    # Your logic here
    response = await call_next(request)
    return response

agent_os = AgentOS(
    agents=[agent],
    middleware=[custom_middleware],
)
```

## Clients

### AgentOS Client

Connect to AgentOS from Python:

```python
from agno.client import AgentOSClient

client = AgentOSClient(base_url="http://localhost:8000")

# Run agent
response = await client.run_agent(
    agent_id="my-agent",
    message="Hello!",
    user_id="user@example.com",
)
print(response.content)

# Run with streaming
async for event in client.run_agent_stream(
    agent_id="my-agent",
    message="Tell me a story",
):
    print(event.content, end="", flush=True)

# Get sessions
sessions = await client.get_sessions(user_id="user@example.com")

# Search knowledge
knowledge = await client.knowledge_search(query="What is Agno?")

# Manage memories
memories = await client.get_memories(user_id="user@example.com")
```

### A2A Client

Connect to any A2A-compatible server:

```python
from agno.client.a2a import A2AClient

# Connect to Agno A2A
client = A2AClient("http://localhost:8000/a2a/agents/my-agent")
result = await client.send_message("Hello!")

# Connect to Google ADK
client = A2AClient("http://localhost:8001/", protocol="json-rpc")
result = await client.send_message("Hello!")
```

## Background Tasks

### Run Hooks in Background

```python
from agno.os import AgentOS
from agno.hooks import hook

@hook(run_in_background=True)
async def send_notification(run_output, agent):
    """Send notification after run completes."""
    await send_slack_message(run_output.content)

agent = Agent(
    name="My Agent",
    post_hooks=[send_notification],
)

agent_os = AgentOS(
    agents=[agent],
    run_hooks_in_background=True,  # All hooks in background
)
```

## Tracing

### Enable Tracing

```python
from agno.os import AgentOS

agent_os = AgentOS(
    agents=[agent],
    enable_tracing=True,  # Enable OpenTelemetry tracing
)
```

**View traces:**
1. Open [os.agno.com](https://os.agno.com)
2. Select your OS
3. Go to Traces tab

### Configure Tracing

```python
from agno.os import AgentOS

agent_os = AgentOS(
    agents=[agent],
    tracing_provider="open_telemetry",
    tracing_endpoint="http://localhost:4318",
)
```

## Lifecycle Management

### Custom Lifespan

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """Custom lifespan events."""
    # Startup
    print("AgentOS starting up...")
    yield
    # Shutdown
    print("AgentOS shutting down...")

agent_os = AgentOS(
    agents=[agent],
    lifespan=lifespan,
)
```

## Deployment Patterns

### Single Instance Deployment

```bash
uvicorn agent:app --host 0.0.0.0 --port 8000
```

### Docker Compose

```yaml
version: '3.8'

services:
  agentos:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - OPENAI_API_KEY=sk-...
    volumes:
      - ./data:/app/data
```

```bash
docker-compose up -d
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentos
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentos
  template:
    metadata:
      labels:
        app: agentos
    spec:
      containers:
      - name: agentos
        image: agno-agentos:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: agentos-secrets
              key: database-url
```

## See Also

- [AgentOS Clients](clients.md) - Client library usage
- [Configuration](config.md) - Detailed configuration options
- [Interfaces](interfaces.md) - Interface setup
- [Security](security.md) - Authentication and RBAC
- [Production Patterns](../../../production/overview.md) - Production deployment
