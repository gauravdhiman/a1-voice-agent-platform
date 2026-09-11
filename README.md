# AI Voice Agent Platform

A production-grade multi-tenant SaaS platform for managing AI voice agents with Pipecat WebSocket voice transport (`voice-ws`), dynamic tool integration, and comprehensive billing/RBAC systems.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker and Docker Compose
- Supabase account (for database)
- Google Cloud account (for OAuth + Gemini API)
- Twilio account (for inbound/outbound phone calls via Media Streams)
- Public `wss://` URL for `voice-ws` when testing phone calls locally (e.g. ngrok)

### Automated Setup

```bash
# Clone repository
git clone <repository-url>
cd ai-voice-agent-platform

# Run setup script
./scripts/setup.sh

# The setup script creates the canonical local environment file if needed.
# Edit .env.local with your local Supabase and shared provider credentials.

# Run database migrations
cd backend
alembic upgrade head

# Seed notification events
python scripts/seed_notification_events.py

# Start development containers against local Supabase
cd ..
./start.sh start dev
```

### Manual Setup

1. **Clone and setup environment**

   ```bash
   git clone <repository-url>
   cd ai-voice-agent-platform
   ```

2. **Frontend Development (Non-containerized)**

   ```bash
   cd frontend
   npm install
   cp .env.local.example .env.local
   # Edit .env.local with your configuration
   npm run dev
   ```

3. **Backend Development (Non-containerized, advanced)**

   ```bash
   cd backend
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   # Run from the repository root so shared settings can load .env.local.
   ENV_FILE=.env.local python main.py
   python main.py
   ```

4. **Voice voice-ws Development (Non-containerized)**

   ```bash
   cd voice-ws
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   # JWT_SECRET_KEY must match backend; see voice-ws/README.md
   uvicorn src.main:app --host 0.0.0.0 --port 7860 --reload
   ```

5. **Supabase Realtime Setup (Required for auto-refresh tokens)**

    ```bash
    # Run SQL script in Supabase Dashboard → SQL Editor
    # The script is located at: scripts/setup-supabase-realtime.sql
    # This enables real-time updates on agent_tools and agents tables
    ```

6. **Using Docker for Development (Containerized)**

    ```bash
    # Create .env.local once from .env.local.example, then run local Supabase.
    ./start.sh start dev

    # Run the same local Docker services against cloud staging Supabase.
    ./start.sh start dev --env staging

    # Run the production Compose stack against .env.prod.
    ./start.sh start prod
    ```

    See [Environment Configuration](docs/05_operations/environment_configuration.md)
    for the environment-selection design, staging workflow, and deployment
    defaults.

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        User(["User / Caller"])
        Browser["Web Dashboard (Next.js)"]
    end

    subgraph Infrastructure ["Infrastructure & Real-time"]
        VWS["voice-ws (Pipecat WebSocket)"]
        Twilio["Twilio (Telephony + Media Streams)"]
        OTEL["OTEL Collector"]
    end

    subgraph Backend_Voice ["Core Platform (Docker)"]
        BE["FastAPI Backend (REST)"]
        VWS
        Shared["Shared Tools & Logic"]
    end

    subgraph Persistence ["Data & Identity"]
        DB[(Supabase PostgreSQL)]
        Auth[(Supabase Auth)]
    end

    subgraph External ["External Services"]
        Gemini["Google Gemini (LLM)"]
        Stripe["Stripe (Payments)"]
        Resend["Resend (Email)"]
        Google["Google / LinkedIn (OAuth)"]
        ExtTools["External Tools (G-Cal, etc)"]
    end

    %% Flow: User Dashboard Interaction
    User <--> Browser
    Browser <--> Auth
    Browser <--> BE
    
    %% Flow: Voice Call Interaction
    User <--> Twilio
    Twilio -- Media Stream wss --> VWS
    Browser -- WebSocket --> VWS
    
    %% Flow: Backend Orchestration
    BE <--> DB
    BE <--> Auth
    BE <--> Stripe
    BE --> Resend
    BE <--> Google
    BE --> VWS
    
    %% Flow: Voice AI Execution
    VWS <--> Shared
    VWS <--> DB
    VWS <--> Gemini
    VWS <--> ExtTools

    %% Flow: Observability
    BE & VWS --> OTEL
    Browser -. content-free traceparent .-> BE
    OTEL --> GC[Grafana Cloud]
    OTEL -. traces only, content-free .-> LF[Langfuse Cloud]

    %% Styling
    style BE fill:#f9f,stroke:#333,stroke-width:2px
    style VWS fill:#f9f,stroke:#333,stroke-width:2px
    style DB fill:#dfd,stroke:#333,stroke-width:2px
    style Auth fill:#dfd,stroke:#333,stroke-width:2px
    style Gemini fill:#ddf,stroke:#333,stroke-width:1px
```

### Frontend (Next.js)

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Shadcn/ui
- **State Management**: React Context
- **Routing**: App Router with protected routes

### Backend (FastAPI)

- **Framework**: Python FastAPI
- **Database**: Supabase (PostgreSQL with RLS)
- **Authentication**: JWT with OAuth (Google, LinkedIn)
- **Multi-tenancy**: Organization-based isolation with Row-Level Security
- **Billing**: Stripe integration with credit-based billing
- **RBAC**: Role-based access control with fine-grained permissions

### voice-ws (Pipecat WebSocket)

- **Framework**: Pipecat + FastAPI WebSocket server
- **LLM Integration**: Gemini Realtime or modular STT→LLM→TTS pipeline
- **Tool System**: Dynamic tool loading (platform tools, MCP, skills)
- **Real-time Communication**: Browser `/ws` and Twilio Media Streams `/twilio`
- **Session auth**: Short-lived JWT from backend (`voice_session_service`)

### Infrastructure

- **Containerization**: Docker & Docker Compose
- **Scalability**: Horizontal scaling ready
- **Observability**: OpenTelemetry with an authenticated Collector boundary
- **Monitoring**: Grafana Cloud dashboards, logs, traces and alerts; optional
  Langfuse Cloud metadata-only AI trace navigation

## 📁 Project Structure

```
ai-voice-agent-platform/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   │   ├── (dashboard)/  # Protected dashboard
│   │   │   └── auth/          # Authentication
│   │   ├── components/      # React components
│   │   ├── contexts/        # React Context providers
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # Utilities and API client
│   │   ├── services/        # Business logic services
│   │   └── types/          # TypeScript definitions
│   ├── Dockerfile          # Production Docker config
│   ├── Dockerfile.dev      # Development Docker config
│   └── package.json
├── backend/                 # FastAPI application
│   ├── src/
│   │   ├── auth/            # Authentication and RBAC
│   │   ├── billing/         # Stripe billing integration
│   │   ├── notifications/    # Email notification system
│   │   ├── organization/     # Organization management
│   │   ├── voice_agents/    # Voice agent API endpoints
│   │   └── shared/         # Shared utilities
│   ├── config/              # Configuration management
│   ├── alembic/             # Database migrations
│   ├── tests/               # Backend tests
│   ├── Dockerfile           # Production Docker config
│   ├── Dockerfile.dev       # Development Docker config
│   └── requirements.txt
├── voice-ws/                # Pipecat WebSocket voice worker
│   ├── src/
│   │   ├── main.py          # /health, /ws, /twilio
│   │   ├── session_setup.py # Agent + preset + tools
│   │   └── speech/          # Provider factory
│   ├── Dockerfile
│   └── requirements.txt
├── shared/                  # Shared code (backend + voice-ws)
│   ├── voice_agents/         # Voice agent services and models
│   │   ├── service.py       # Voice agent CRUD
│   │   ├── tool_service.py  # Tool management
│   │   ├── tools/          # Tool implementations
│   │   └── models.py       # Data models
│   ├── config/              # Shared configuration
│   └── common/             # Common utilities
├── docs/                   # Documentation
│   ├── 00_introduction/     # Project overview
│   ├── 01_architecture/     # System architecture
│   ├── 02_implementation/  # Implementation details
│   ├── 03_development_guides/  # Development guides
│   ├── 04_operations/       # Operations & deployment
│   ├── 05_business/        # Business requirements
│   ├── legacy/             # Historical documentation
│   └── new_docs/          # Old documentation (to be migrated)
├── docker-compose.yml       # Production Docker Compose
├── docker-compose.dev.yml   # Development Docker Compose
├── start.sh                # Container management script
├── AGENTS.md               # AI agent guidelines
└── README.md
```

## 📦 Features

### Core Platform

- ✅ Multi-tenant SaaS architecture with organization-based isolation
- ✅ Row-Level Security (RLS) for data isolation
- ✅ Role-Based Access Control (RBAC) with fine-grained permissions
- ✅ Password-based authentication with strong password policies
- ✅ Google OAuth integration
- ✅ Stripe billing integration with credit-based subscriptions
- ✅ Email notification system (Resend.com)
- ✅ OpenTelemetry observability (traces, metrics, logs)

### Voice Agent System

- ✅ AI voice agents with Pipecat WebSocket (`voice-ws`)
- ✅ **Dynamic system prompt generation from organization and agent context**
- ✅ **System prompt preview in agent configuration UI**
- ✅ Dynamic tool loading from database
- ✅ Pipecat-compatible tool schemas for LLM function calling
- ✅ Tool function-level enable/disable
- ✅ Google Calendar tool implementation
- ✅ Agent greeting on session start
- ✅ OAuth token management for tools
- ✅ Two-tier tool service (safe API, full voice-ws)
- ✅ Real-time UI synchronization (Supabase Realtime)
- ✅ Auto-refresh of OAuth tokens before expiry

### Developer Experience

- ✅ Docker containerization (dev & prod)
- ✅ Docker Compose orchestration
- ✅ Automated setup script
- ✅ OpenTelemetry manual instrumentation
- ✅ Type-safe APIs (Pydantic, TypeScript)
- ✅ Comprehensive documentation
- ✅ Pre-commit hooks (Black, isort, ESLint)

### Testing & Quality

- ✅ Pytest for backend testing
- ✅ Playwright for E2E testing
- ✅ Code formatting (Black, Prettier)
- ✅ Linting (Flake8, ESLint)
- 🚧 Comprehensive test coverage

### Infrastructure

- ✅ Supabase database (PostgreSQL)
- ✅ Twilio Media Streams + browser WebSocket voice transport
- ✅ Google Realtime API (Gemini)
- ✅ OpenTelemetry Collector architecture
- ✅ Environment-based configuration
- 🚧 Kubernetes deployment manifests
- 🚧 CI/CD pipeline

## 🎯 Key Features

### Voice Agent System

**Dynamic Tool Loading**: Tools are loaded from database at runtime, enabling:

- Runtime tool configuration without code deployment
- Per-organization tool customization
- Easy addition of new tools

**Two-Tier Tool Service**:

- **API Layer**: Returns safe metadata (no OAuth tokens)
- **voice-ws Layer**: Returns full tool instances with all secrets

**Pipecat tool schemas**: Platform tools expose JSON schemas the LLM runtime calls via `PlatformToolRegistry`.

**Agent Greeting**: On connect, voice-ws queues an initial user instruction so the agent speaks first.

### Multi-Tenancy

**Shared Database + Shared Schema**:

- `organization_id` column on all tenant tables
- Row-Level Security (RLS) policies enforce isolation
- Tenant context injected via middleware

**RBAC System**:

- Predefined roles: platform_admin, org_admin, member, billing
- Platform admins can create custom roles
- Fine-grained permissions: `resource.action` format
- One role per user per organization

### Billing & Credits

**Stripe Integration**:

- Plan-based subscriptions (monthly/annual)
- Credit allocation on payment
- Webhook-driven status updates
- Idempotent event handling

**Credit Management**:

- Track usage, top-ups, and adjustments
- Enforce restrictions on low balance
- Low credit alerts via notifications

### Observability

**OpenTelemetry Stack**:

- Manual instrumentation for precise control
- Collector architecture for centralized processing
- CORS-enabled for browser telemetry
- Grafana Cloud dashboards and alerting through the minimal cloud collector
- Optional Langfuse Cloud metadata-only AI trace navigation

## 🔄 Development Priorities

1. **Voice Agent Enhancements**:

   - Multi-LLM support (OpenAI, Claude, etc.)
   - Conversation state persistence
   - Advanced error handling and recovery
   - Agent analytics dashboard

2. **Tool Expansion**:

   - More tool implementations (CRM, messaging, custom APIs)
   - Tool composition and chaining
   - Tool dependencies and versioning
   - Tool health monitoring

3. **Testing**:

   - Comprehensive test coverage (>80%)
   - E2E test scenarios for voice agents
   - Performance testing (load, stress)
   - Integration tests for tool wrapping

4. **Operations**:

   - CI/CD pipeline (GitHub Actions)
   - Kubernetes deployment manifests
   - Production runbooks
   - Monitoring and alerting setup

5. **Features**:
   - Agent analytics dashboard
   - Conversation history and playback
   - Tool usage metrics
   - Advanced RBAC permissions
   - Multi-language support

## 📚 Documentation

### Documentation Structure

```
docs/
├── 00_getting_started/     # Getting started guides
│   ├── project_overview.md       # Platform overview and features
│   ├── quick_start.md           # Quick start with Docker
│   ├── setup.md                # Detailed setup guide
│   └── introduction.md          # Platform introduction
├── 01_architecture/          # System architecture
│   ├── overview.md              # High-level system design
│   ├── system_architecture.md    # Complete architecture
│   ├── frontend_architecture.md  # Frontend design
│   ├── backend_architecture.md   # Backend design
│   ├── database_schema.md        # Database schema
│   └── twilio_call_flow.md     # Call handling flow
├── 02_features/             # Platform features (NEW)
│   ├── voice_agents/           # Voice agents system
│   ├── authentication_rbac/     # Authentication & RBAC
│   ├── multi_tenancy/          # Multi-tenant support
│   ├── billing/                # Billing and payments
│   ├── notifications/           # Email notifications
│   └── observability/         # Monitoring & metrics
├── 03_implementation/       # Implementation details
│   ├── tool_system.md          # Tool architecture
│   ├── dynamic_tool_architecture.md  # Tool runtime design
│   ├── tool_calling_challenges.md  # Problems & solutions
│   ├── dynamic_tool_architecture.md  # Dynamic tool loading
│   ├── tool_implementation_summary.md  # Implementation summary
│   ├── payment_flow.md        # Payment workflows
│   ├── stripe_integration.md    # Stripe integration
│   └── polymorphic_relationships.md  # Database patterns
├── 03_development/          # Development workflows (NEW)
│   ├── getting_started.md      # Quick start for developers
│   ├── frontend/              # Frontend development
│   ├── backend/               # Backend development
│   ├── voice-ws/                # Voice voice-ws development
│   └── shared_module/         # Shared code guide
├── 04_development_guides/  # Development guidelines
│   ├── development_setup.md    # Local dev setup
│   ├── api_guidelines.md      # API standards
│   ├── database_migrations.md  # Migration best practices
│   └── testing.md            # Testing strategies
├── 05_operations/           # Operations & deployment
│   ├── deployment/            # Production deploy (GCP + OCI + Supabase)
│   ├── environment_configuration.md
│   └── stripe_management.md
└── 05_business/             # Business requirements
    ├── prd.md                 # Product requirements
    └── SUMMARY.md              # Business summary
```

### Key Documentation

- **[Documentation Summary](docs/SUMMARY.md)** - Complete documentation index
- **[Getting Started](docs/00_getting_started/)** - Quick start and setup guides
- **[Feature Documentation](docs/02_features/)** - Comprehensive feature guides
- **[Development Guides](docs/03_development/)** - Developer workflows
- **[System Architecture](docs/01_architecture/system_architecture.md)** - Complete architecture
- **[AGENTS.md](AGENTS.md)** - AI agent coding guidelines

### Component Documentation

- **[Frontend README](frontend/README.md)** - Next.js application
- **[Backend README](backend/README.md)** - FastAPI application
- **[voice-ws README](voice-ws/README.md)** - Pipecat voice voice-ws service
- **[Shared Module README](shared/README.md)** - Shared code architecture

## 🔧 Quick Reference

### Starting Services

```bash
# Development containers
./start.sh start dev

# Production containers
./start.sh start prod

# View logs
./start.sh logs dev

# Stop services
./start.sh stop dev
```

### Database Migrations

```bash
cd backend
alembic upgrade head              # Apply all migrations
alembic revision -m "message"   # Create new migration
alembic downgrade -1             # Rollback one migration
```

### Supabase Realtime Setup (One-time)

```bash
# Run SQL script in Supabase Dashboard → SQL Editor
# File location: scripts/setup-supabase-realtime.sql
# This enables real-time updates for tool status and token auto-refresh
```

### Testing

#### Backend Tests (Pytest)
```bash
cd <project-root>/backend

# Set up test environment (run once per session)
source ./test-env.sh

# Run all backend tests
pytest backend/tests/

# Run specific module tests
pytest backend/tests/organization/
pytest backend/tests/notifications/

#Run specific test file
pytest backend/tests/organization/test_service.py

# Run specific test
pytest backend/tests/organization/test_service.py::TestOrganizationService::test_create_organization_success -v

# Run with coverage
pytest --cov

```

#### voice-ws Test (Pytest)
```bash
cd <project-root>/voice-ws
../backend/.venv/bin/python -m pytest tests/ --cov
```

#### Frontend Unit Tests (Vitest)
```bash
cd <project-root>/frontend
# Run all tests
npm run test
or
npx vitest run

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test -- --watch

# Run with UI
npm run test:ui

# Run specific test file
npm run test -- tests/lib/test-utils.test.ts

# Run specific test
npm run test -- tests/lib/test-utils.test.ts -t "cn utility"

# Run tests in a directory
npm run test -- tests/lib/
npm run test -- tests/services/
npm run test -- tests/hooks/

# Run tests without watching (CI mode)
npm run test:run
```

#### End-to-End Tests (Playwright + Isolated Stack)
Run all e2e tests. This will start the test specific container app stack and after test will also tear it down.
```bash
cd <project-root>

# This script handles building an isolated stack, initializing the DB, and running Playwright tests.
./scripts/run-e2e.sh

# Optional: Record all videos for E2E tests
./scripts/run-e2e.sh --video-on

# E2E test results are saved to: e2e/reports/report.html
```

Run specific e2e tests against already running app stack. Example below assumes the app (UI server) is running on port 3000:
```bash
E2E_BASE_URL=http://localhost:3000 backend/.venv/bin/python -m pytest e2e/tests/test_skill_workflow.py -x -v
```

**Note**: Always source `./test-env.sh` before running tests. This sets up the Python paths for all modules (backend/src, shared). Run tests from project root directory for best results.

### Code Quality

```bash
# Backend
cd backend
black .                    # Format code
isort .                    # Sort imports
flake8 src/                 # Lint

# Frontend
cd frontend
npm run lint                # Run ESLint
npx tsc --noEmit         # Type check
```

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] **Environment Configuration**
  - [ ] Populate `.env.prod` from `.env.prod.example` for production deployment
  - [ ] Configure Supabase credentials (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`)
  - [ ] Configure OAuth provider credentials (Google, Microsoft, etc.)
  - [ ] Set `ENCRYPTION_KEY` for production
  - [ ] Configure token refresh timing (default: 5 min check, 15 min window)
  - [ ] Verify the selected environment with `./start.sh config --env production`

 - [ ] **Database Setup**
  - [ ] Run database migrations: `alembic upgrade head`
     - This creates/updates tables including `agent_tools` and `agents`
  - [ ] Run Supabase Realtime setup: `scripts/setup-supabase-realtime.sql`
     - Run in Supabase SQL Editor (ONE-TIME setup after tables exist)
     - Verify output shows `agent_tools` and `agents` tables in publication
  - [ ] Verify `last_refreshed_at` column exists in `agent_tools` table

- [ ] **Docker Configuration**
  - [ ] Verify Docker Compose files have token refresh environment variables
  - [ ] Build images: `./start.sh build dev` (or `prod`)
  - [ ] Test containers start: `./start.sh start dev`

- [ ] **Local Testing**
  - [ ] Start backend: `cd backend && python main.py`
  - [ ] Start frontend: `cd frontend && npm run dev`
  - [ ] Test token refresh service starts successfully
    - Check logs: "Token refresh service started"
    - Check logs: "Checking X tools for token refresh"
  - [ ] Test real-time subscriptions
    - Navigate to agent detail page
    - Make database change (enable/disable tool)
    - Verify UI updates automatically without page refresh
    - Check browser console for change notifications

### Production Deployment

- [ ] **Environment Variables**
  - [ ] Set production values in environment variables or secrets manager
  - [ ] Token refresh timing: 10 min check, 20 min window (recommended)
  - [ ] OAuth credentials from production accounts
  - [ ] Supabase production project
  - [ ] `ENCRYPTION_KEY` from secure secret management (not hardcoded)

- [ ] **Infrastructure**
  - [ ] Configure DNS records
  - [ ] Set up SSL/TLS certificates
  - [ ] Configure load balancer (if multiple instances)
  - [ ] Provision the production observability profile from
    [Operating observability](docs/05_operations/observability.md): one
    authenticated collector host, one Grafana Cloud stack and one Langfuse
    project
  - [ ] Import the cloud dashboard, create owned alert contact points, and
    verify one firing and recovery notification

- [ ] **Security**
  - [ ] Verify Supabase RLS policies meet production requirements
  - [ ] Ensure `.env` files are not committed to version control
  - [ ] Rotate secrets regularly (OAuth credentials, encryption keys)
  - [ ] Enable audit logging for sensitive operations

- [ ] **Performance**
  - [ ] Configure appropriate refresh intervals based on OAuth provider token lifetimes
  - [ ] Monitor API rate limits to OAuth providers
  - [ ] Set up database connection pooling
  - [ ] Enable CDN for static assets
  - [ ] Configure caching strategy

### Post-Deployment Verification

- [ ] **Functionality**
  - [ ] Verify backend health endpoint returns 200: `curl http://your-domain/health`
  - [ ] Verify frontend loads: Navigate to production URL
  - [ ] Test user authentication flow
  - [ ] Test OAuth authentication with a tool (e.g., Gmail)
  - [ ] Verify tool configuration persists in database
  - [ ] Verify token refresh service is running
  - [ ] Verify real-time UI updates work without page refresh

- [ ] **Token Refresh Service**
  - [ ] Check logs: "Token refresh service started"
  - [ ] Authenticate a tool (e.g., Gmail)
  - [ ] Wait for token expiry (or simulate by adjusting `expires_at` in database)
  - [ ] Verify backend logs: "Token refreshed successfully for tool [name]"
  - [ ] Verify `last_refreshed_at` timestamp is updated in database
  - [ ] Verify frontend UI shows "authenticated" status automatically

- [ ] **Real-Time Subscriptions**
  - [ ] Open browser DevTools Console
  - [ ] Navigate to agent detail page
  - [ ] Make a database change (enable/disable tool or wait for token refresh)
  - [ ] Verify console log: "Tool updated in database: { eventType: 'UPDATE', ... }"
  - [ ] Verify UI updates automatically (no page refresh needed)
  - [ ] Check tool status badge changes immediately

- [ ] **Monitoring & Observability**
  - [ ] Monitor backend logs for token refresh activity
  - [ ] Check for token refresh errors (watch logs for 24-48 hours)
  - [ ] Monitor memory usage (long-running background task)
  - [ ] Verify graceful shutdown works (restart container)
  - [ ] Check database performance during refresh operations
  - [ ] Verify no memory leaks in frontend (real-time subscriptions)

- [ ] **Error Handling**
  - [ ] Test with expired tokens (should refresh automatically)
  - [ ] Test with invalid `refresh_token` (should log warning, not crash)
  - [ ] Test network failures (should retry or log error, not crash)
  - [ ] Test with multiple OAuth providers (Google, Microsoft, etc.)
  - [ ] Test concurrent tool refreshes

### Rollback Plan

If deployment fails:

- [ ] Stop new deployment: `./start.sh stop prod`
- [ ] Switch back to previous version (if using blue-green deployment)
- [ ] Restore database backup (if schema changes were applied)
- [ ] Revert environment variables
- [ ] Clear Redis cache (if using)
- [ ] Verify application starts successfully

### Ongoing Operations

- [ ] **Daily**
  - [ ] Monitor token refresh success rate (should be near 100%)
  - [ ] Check for refresh failures in logs
  - [ ] Verify `last_refreshed_at` timestamps are recent
  - [ ] Monitor OAuth API usage rate limits

- [ ] **Weekly**
  - [ ] Review logs for patterns or anomalies
  - [ ] Check database growth
  - [ ] Verify real-time subscriptions remain stable
  - [ ] Review security alerts

- [ ] **Monthly**
  - [ ] Review OAuth token lifetime and adjust refresh windows
  - [ ] Check for deprecated OAuth provider versions
  - [ ] Review and rotate secrets (encryption keys, OAuth credentials)
  - [ ] Update dependencies (backend/frontend)

---

## 🤝 Contributing

1. Follow the established code style and linting rules
2. Use TypeScript for frontend, type hints for backend
3. Add tests for new features
4. Update documentation as needed
5. Use conventional commit messages

See [AGENTS.md](AGENTS.md) for detailed coding guidelines.

## 📄 License

[Add your license information here]

---

## 🛟 Support

For questions and support:

- Review the documentation in `docs/`
- Check [voice-ws Documentation](voice-ws/README.md) for voice agent details
- Check [Shared Module Documentation](shared/README.md) for shared code
- Review [Development Guidelines](AGENTS.md) for coding standards
- Check existing issues
- Create a new issue if needed

Built with ❤️ using Next.js, FastAPI, Pipecat, and modern web technologies.
