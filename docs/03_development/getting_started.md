# Getting Started Guide

## Welcome to AI Voice Agent Platform

This guide helps you quickly understand the platform and get up and running. Whether you're a new developer, product manager, or business user, this will help you navigate the codebase and documentation.

## Quick Navigation

### By Role

**New Developer**:
1. Read this guide
2. Follow [Quick Start](../00_getting_started/quick_start.md)
3. Review [Project Overview](../00_getting_started/project_overview.md)
4. Explore [Development Guides](../03_development/)

**Product Manager**:
1. Read [Project Overview](../00_getting_started/project_overview.md)
2. Review [Business Requirements](../05_business/prd.md)
3. Explore [Feature Documentation](../02_features/)

**DevOps Engineer**:
1. Review [System Architecture](../01_architecture/system_architecture.md)
2. Check [Deployment](../05_operations/)
3. Configure [OpenTelemetry](../02_features/observability/overview.md)

**Business User**:
1. Read [Project Overview](../00_getting_started/project_overview.md)
2. Understand [Key Features](#key-features-below)
3. Review [Platform Capabilities](#platform-capabilities-below)

## Platform at a Glance

### What It Does

The AI Voice Agent Platform enables organizations to:
- **Create AI Voice Agents**: Configure intelligent agents for customer support, scheduling, and more
- **Integrate Tools**: Connect agents to business systems (Google Calendar, CRM, APIs)
- **Handle Voice Calls**: Real-time voice conversations via LiveKit
- **Manage Organizations**: Multi-tenant platform with team management
- **Bill & Subscribe**: Credit-based billing with Stripe integration
- **Control Access**: Role-based permissions for team collaboration

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| Database | Supabase (PostgreSQL) |
| Real-time Voice | LiveKit Cloud |
| AI/LLM | Google Gemini Realtime API |
| Payments | Stripe |
| Email | Resend.com |
| Observability | OpenTelemetry + New Relic |
| Containerization | Docker & Docker Compose |

### Architecture Summary

```
Frontend (Next.js)
    ↓ HTTP
Backend (FastAPI)
    ↓
├──→ Supabase (Database)
├──→ LiveKit Cloud (Voice)
├──→ Stripe (Payments)
└──→ Worker (LiveKit Agents)
```

## Key Features

### 1. Voice Agents ✅

**What**: AI-powered voice agents that handle real-time conversations

**Why It Matters**:
- Automate customer support 24/7
- Reduce wait times
- Scale support without adding staff
- Consistent quality and experience

**How It Works**:
1. Admin creates agent with system prompt and phone number
2. Caller dials agent phone number
3. LiveKit connects to backend, which creates room
4. Worker loads agent configuration and tools
5. AI handles conversation, using tools when needed
6. Responses spoken back to caller in real-time

**See Also**: [Voice Agents Feature](../02_features/voice_agents/overview.md)

### 2. Dynamic Tool System ✅

**What**: Connect agents to external APIs and services

**Why It Matters**:
- Agents can perform real actions (schedule meetings, look up orders)
- Easy to add new tools without code deployment
- Per-agent tool customization
- Secure token management

**Example Tools**:
- Google Calendar: Check availability, create events
- CRM: Look up customer data, update records
- E-commerce: Check order status, process returns

**See Also**: [Tool System Documentation](../03_implementation/tool_system.md)

### 3. Multi-Tenancy ✅

**What**: Multiple organizations on single platform with strict data isolation

**Why It Matters**:
- SaaS platform for serving multiple customers
- Strong security with Row-Level Security (RLS)
- Organization-based resource scoping
- Users can belong to multiple organizations

**How It Works**:
- Every resource (agents, tools, etc.) has `organization_id`
- Row-Level Security policies in database prevent cross-tenant access
- Users can only see resources from their organizations

**See Also**: [Multi-Tenancy Feature](../02_features/multi_tenancy/overview.md)

### 4. Authentication & RBAC ✅

**What**: Secure authentication with fine-grained permissions

**Why It Matters**:
- Secure access to platform
- Role-based access control (RBAC)
- Team collaboration with appropriate permissions
- Audit trail of all actions

**Authentication Methods**:
- Password-based login
- Google OAuth (social login)

**Predefined Roles**:
- `platform_admin`: Platform-wide control
- `org_admin`: Full control within organization
- `member`: Standard access
- `billing`: Billing management only

**See Also**: [Authentication & RBAC Feature](../02_features/authentication_rbac/overview.md)

### 5. Billing & Credits ✅

**What**: Credit-based billing with Stripe integration

**Why It Matters**:
- Transparent pricing based on usage
- Automatic billing and invoicing
- Predictable costs for organizations
- Easy to scale with more credits

**How It Works**:
- Organizations subscribe to plans (trial, starter, pro, enterprise)
- Plans include monthly credit allocation
- Credits consumed for platform usage (calls, tool execution)
- Low credit alerts sent before running out

**See Also**: [Billing Feature](../02_features/billing/overview.md)

### 6. Observability ✅

**What**: Comprehensive monitoring with OpenTelemetry and New Relic

**Why It Matters**:
- Understand system performance
- Identify bottlenecks and issues
- Track business metrics (calls, usage)
- Proactive alerting

**What's Tracked**:
- API latency and errors
- Voice agent call duration and success rate
- Tool execution metrics
- Credit consumption
- System resource usage

**See Also**: [Observability Feature](../02_features/observability/overview.md)

## Code Structure

### High-Level Organization

```
ai-voice-agent-platform/
├── frontend/          # Next.js UI application
├── backend/           # FastAPI REST API
├── worker/            # LiveKit voice agent worker
├── shared/            # Code shared by backend + worker
├── docs/              # Documentation (this folder)
└── docker-compose.yml  # Container orchestration
```

### Key Directories

| Directory | Purpose | Key Files |
|-----------|---------|------------|
| `frontend/src/app/` | Next.js pages and routes | page.tsx, layout.tsx |
| `frontend/src/components/` | React components | Button, Card, Input |
| `frontend/src/services/` | API client and business logic | auth-service.ts, agent-service.ts |
| `backend/src/` | API endpoints and business logic | auth/, voice_agents/, billing/ |
| `backend/src/shared/` | Shared utilities | middleware/, exceptions/ |
| `worker/src/` | Worker entry point and agent logic | worker.py |
| `shared/voice_agents/` | Voice agent models and services | service.py, tool_service.py |
| `shared/config/` | Configuration management | settings.py, supabase.py |

## Quick Start Options

### Option 1: Docker (Recommended for Local Dev)

Fastest way to get all services running:

```bash
# Clone repository
git clone <repository-url>
cd ai-voice-agent-platform

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# (Supabase, LiveKit, Stripe, etc.)

# Start all services
./start.sh start dev
```

**What This Does**:
- Starts Frontend (Next.js) on http://localhost:3000
- Starts Backend (FastAPI) on http://localhost:8000
- Starts Worker (LiveKit) for voice agent calls
- Starts OpenTelemetry Collector for monitoring
- Connects all services to Supabase database

**Access Points**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- OpenTelemetry Collector: http://localhost:4318

### Option 2: Manual Setup (Recommended for Contributing)

For development on individual services:

```bash
# Backend
cd backend
python -m venv .venv-backend
source .venv-backend/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env with configuration
python main.py

# Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with configuration
npm run dev

# Worker (new terminal)
cd worker
python -m venv .venv-worker
source .venv-worker/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with configuration
python -m livekit.agents.cli --dev
```

**When to Use**:
- Working on specific service changes
- Need to attach debugger
- Running tests for one service
- Contributing to one component

## Common Workflows

### Creating Your First Voice Agent

1. **Sign Up or Login**: Go to http://localhost:3000
2. **Create Organization**: Enter organization details
3. **Create Agent**: Navigate to Agents page → "Create Agent"
4. **Configure Agent**:
   - Name: "Customer Support Agent"
   - System Prompt: "You are a helpful customer support agent..."
   - Phone Number: Select or add Twilio number
5. **Add Tools**: Configure tools for agent (Google Calendar, CRM, etc.)
6. **Test Agent**: Make test call to verify functionality

### Adding a New Tool

1. **Create Tool Implementation**:
   ```python
   # shared/voice_agents/tools/implementations/my_tool.py
   from shared.voice_agents.tools.base.base_tool import BaseTool

   class MyTool(BaseTool):
       @property
       def metadata(self):
           return ToolMetadata(
               name="MyTool",
               description="My tool description"
           )

       async def my_action(self, context: RunContext, param: str):
           """Tool action."""
           return {"result": "..."}
   ```

2. **Restart Worker**: Worker auto-discovers new tools
3. **Backend Sync**: Backend syncs tool metadata to database on startup
4. **Configure in UI**: Go to Tools page, select tool for agent
5. **Test**: Make test call to verify tool works

### Adding a New API Endpoint

1. **Define Pydantic Models**:
   ```python
   # backend/src/voice_agents/models.py
   class AgentCreate(BaseModel):
       name: str
       organization_id: str
       system_prompt: str
   ```

2. **Create Route Handler**:
   ```python
   # backend/src/voice_agents/routes.py
   @router.post("/agents")
   async def create_agent(agent: AgentCreate):
       result = await agent_service.create_agent(agent)
       return result
   ```

3. **Add to Router**:
   ```python
   # backend/src/voice_agents/routes.py
   app.include_router(router, prefix="/api/v1")
   ```

4. **Test**: Use API docs at http://localhost:8000/docs

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm test

# E2E tests
cd e2e
npm run test
```

## Documentation Structure

### New to the Platform?

Start here:
1. **[Project Overview](project_overview.md)** - What is this platform?
2. **[Quick Start](quick_start.md)** - Get running in minutes
3. **[Setup Guide](setup_guide.md)** - Detailed configuration

### Want to Understand Architecture?

Check out:
1. **[System Architecture](../01_architecture/system_architecture.md)** - Overall design
2. **[Frontend Architecture](../01_architecture/frontend_architecture.md)** - Next.js structure
3. **[Backend Architecture](../01_architecture/backend_architecture.md)** - FastAPI structure
4. **[Database Schema](../01_architecture/database_schema.md)** - Data model

### Working on Specific Features?

Dive into feature documentation:
1. **[Voice Agents](../02_features/voice_agents/)** - AI voice agents
2. **[Authentication & RBAC](../02_features/authentication_rbac/)** - Security and access control
3. **[Multi-Tenancy](../02_features/multi_tenancy/)** - Organization management
4. **[Billing](../02_features/billing/)** - Payments and credits
5. **[Notifications](../02_features/notifications/)** - Email system
6. **[Observability](../02_features/observability/)** - Monitoring

### Developing the Platform?

See development guides:
1. **[Getting Started Dev](../03_development/getting_started.md)** - Local dev setup
2. **[Frontend Development](../03_development/frontend/)** - Next.js guide
3. **[Backend Development](../03_development/backend/)** - FastAPI guide
4. **[Worker Development](../03_development/worker/)** - LiveKit worker guide
5. **[API Guidelines](../04_development_guides/api_guidelines.md)** - API standards

### Operating the Platform?

Check operations documentation:
1. **[Docker Deployment](../05_operations/docker_deployment.md)** - Container deployment
2. **[Environment Configuration](../05_operations/environment_configuration.md)** - Settings guide
3. **[Stripe Management](../05_operations/stripe_management.md)** - Billing operations

## Learning Path

### Beginner (0-2 Weeks)

**Week 1: Understanding**
- Read all getting started guides
- Explore the UI (create account, organization, agent)
- Review architecture documentation
- Understand core features (voice agents, tools, billing)

**Week 2: Hands-On**
- Create your first voice agent
- Add a tool (Google Calendar)
- Make a test call
- Review traces in New Relic
- Modify system prompt and see changes

### Intermediate (1-2 Months)

**Month 1: Development**
- Set up local development environment
- Explore the codebase
- Make small changes (modify agent greeting, add logging)
- Run tests and fix issues
- Create a custom tool

**Month 2: Features**
- Add new feature (e.g., new API endpoint)
- Implement in backend + frontend
- Write tests for your changes
- Update documentation
- Submit pull request

### Advanced (3+ Months)

- Understand entire system architecture
- Contribute major features
- Debug complex issues
- Performance optimization
- Production deployment
- Guide other developers

## Getting Help

### Documentation

- Check the relevant feature documentation in `docs/02_features/`
- Review architecture docs in `docs/01_architecture/`
- Read implementation guides in `docs/03_implementation/`
- Check README files in individual folders

### Code Examples

- Look at existing tool implementations in `shared/voice_agents/tools/implementations/`
- Review API routes in `backend/src/`
- Check frontend components in `frontend/src/components/`
- Study worker logic in `worker/src/worker.py`

### Troubleshooting

- **Frontend Not Loading**: Check backend is running and CORS is configured
- **Agent Not Responding**: Check worker is running and LiveKit connection is healthy
- **Tools Not Working**: Verify OAuth tokens are valid and tool configuration is correct
- **Database Errors**: Check Supabase connection string and permissions
- **Docker Issues**: Verify Docker is running and ports are not in use

### Community

- Review existing issues
- Create new issue for bugs or questions
- Provide detailed steps to reproduce
- Include relevant logs and error messages

## Best Practices

### For New Developers

1. **Start with Docker**: Use Docker Compose for easiest setup
2. **Read Before Coding**: Understand existing patterns before making changes
3. **Test Everything**: Write tests for new features
4. **Update Documentation**: Keep docs in sync with code
5. **Ask Questions**: Don't hesitate to ask for clarification

### For All Contributors

1. **Follow Code Style**: Use project's linting and formatting rules
2. **Type Safety**: Use TypeScript (frontend) and type hints (backend)
3. **Security**: Never commit secrets or keys
4. **Git Hygiene**: Write meaningful commit messages
5. **PR Quality**: Provide clear description and testing steps

## Next Steps

Now that you have an overview:

1. **Get Running**: Follow [Quick Start](quick_start.md) to start the platform
2. **Explore**: Browse the UI and create your first agent
3. **Deep Dive**: Read feature-specific documentation for areas of interest
4. **Develop**: Set up local environment and make changes
5. **Contribute**: Submit pull requests to improve the platform

---

**Welcome to the AI Voice Agent Platform!** We're excited to have you on board. If you have any questions, don't hesitate to ask.

Happy building! 🚀
