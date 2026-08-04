# Introduction to AI Voice Agent Platform

## Overview

The AI Voice Agent Platform is a production-grade, multi-tenant SaaS platform that enables organizations to create and manage AI-powered voice agents with real-time tool integration.

## What It Does

At its core, this platform allows users to:

1. **Create Voice Agents**: Configure AI agents with custom system prompts
2. **Integrate Tools**: Connect agents to external services (Google Calendar, CRM, APIs)
3. **Handle Voice Calls**: Real-time voice via Pipecat WebSocket (`voice-ws`) and Twilio Media Streams
4. **Manage Organizations**: Multi-tenant isolation for different businesses
5. **Bill & Subscribe**: Credit-based billing with Stripe integration
6. **Control Access**: Role-based permissions for team management

## Key Features

### Voice Agent System

- **AI-Powered Voice**: Real-time voice conversations using LLMs (Gemini Realtime)
- **Dynamic Tools**: Runtime tool loading from database
- **Tool Wrapping**: Innovative pattern to make tools work with LLMs
- **Agent Greeting**: Automatic greeting when agent enters room
- **Function-Level Control**: Enable/disable individual tool functions

### Multi-Tenancy

- **Organization-Based Isolation**: Each organization has separate data
- **Row-Level Security**: Database-level access control (RLS)
- **Tenant Context**: Automatic tenant injection via middleware
- **Flexible Organization Management**: Create, update, manage organizations

### Authentication & Authorization

- **Password-Based Auth**: Strong password policies
- **Google OAuth**: Social login with Google
- **JWT Tokens**: Secure token-based authentication
- **RBAC System**: Role-based access control with fine-grained permissions

### Billing & Payments

- **Stripe Integration**: Subscription-based billing
- **Credit Management**: Track usage and credits
- **Plan-Based Tiers**: Multiple pricing tiers
- **Webhook Handling**: Real-time payment status updates
- **Idempotent Processing**: Safe webhook handling

### Observability

- **OpenTelemetry**: Comprehensive tracing, metrics, and logging
- **Manual Instrumentation**: Precise control over telemetry
- **Collector Architecture**: Centralized processing
- **New Relic Integration**: Visualization and alerting

### Developer Experience

- **Type-Safe**: Pydantic (Python) and TypeScript (Frontend)
- **Docker Support**: Easy development and deployment
- **Pre-Commit Hooks**: Code quality automation
- **Comprehensive Docs**: Extensive documentation for all components

## Architecture Overview

### Components

```
┌─────────────┐
│  Frontend   │  Next.js UI for managing agents
│  (Next.js)  │  organizations, tools, billing
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│  Backend    │  FastAPI REST API
│  (FastAPI)  │  Auth, billing, agents, tools
└──────┬──────┘
       │
       ├───┬───────────┬──────────────┐
       ▼   ▼           ▼              ▼
┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐
│ Supabase │  │  voice-ws   │  │  Twilio  │  │  Stripe   │
│ Database  │  │ Service   │  │ Cloud    │  │  API      │
│          │  │           │  │          │  │           │
└──────────┘  └───────────┘  └──────────┘  └───────────┘
     ▲             ▲              ▲              ▲
     │             │              │              │
     └─────────────┴──────────────┴──────────────┘
                    Shared Infrastructure
```

### Data Flow

1. **User Setup**: User creates account via frontend → Backend creates org/user in Supabase
2. **Agent Creation**: User configures voice agent → Backend stores in database
3. **Tool Integration**: User configures tools for agent → Backend stores tool associations
4. **Call Initiation**: Inbound PSTN → Twilio webhook → Media Stream → `voice-ws` (outbound planned — see [Outbound phone calls](../03_implementation/outbound_phone_calls.md))
5. **Session start**: Backend issues JWT → `voice-ws` loads agent preset and tools
6. **Agent Execution**: Pipecat session handles audio and LLM
7. **Tool Calling**: Agent calls tool → `voice-ws` executes platform tool or MCP
8. **Response**: Tool returns data → Agent speaks response to user
9. **Billing**: Backend tracks usage → Stripe handles payments

## Technology Stack

### Frontend

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Shadcn/ui
- **State**: React Context
- **Testing**: Playwright (E2E)

### Backend

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: Supabase (PostgreSQL)
- **ORM**: SQLAlchemy + Alembic
- **Auth**: JWT + OAuth
- **Testing**: Pytest

### voice-ws

- **Framework**: Pipecat + FastAPI WebSocket
- **LLM**: Gemini Realtime or modular pipeline presets
- **Tools**: Dynamic loading from database
- **Communication**: Browser `/ws` and Twilio `/twilio` Media Streams
- **Testing**: Custom test framework

### Infrastructure

- **Containers**: Docker + Docker Compose
- **Orchestration**: Docker Compose (dev), Kubernetes (prod planned)
- **Observability**: OpenTelemetry Collector
- **Database**: Supabase (managed PostgreSQL)
- **Real-time voice**: `voice-ws` (Pipecat) + Twilio
- **Payments**: Stripe
- **Email**: Resend.com

## Who Is This For?

### Target Users

- **Business Owners**: Want voice agents for customer support, scheduling, etc.
- **Developers**: Want to build custom tools for voice agents
- **Organizations**: Need multi-tenant platform with RBAC

### Use Cases

1. **Customer Support**: AI agents answer common questions
2. **Appointment Scheduling**: Agents schedule meetings via calendar tools
3. **Information Retrieval**: Agents fetch data from CRM or APIs
4. **Order Processing**: Agents process orders via e-commerce tools
5. **Lead Qualification**: Agents qualify leads and route to human agents

## Key Innovations

### 1. Pipecat tool integration

Platform tools in `voice-ws` expose JSON schemas for LLM function calling via `PlatformToolRegistry`.

This allows any tool with any signature to work seamlessly with LLMs.

### 2. Two-Tier Tool Service

We provide different tool data for different security needs:

- **API Layer**: Safe metadata (no OAuth tokens, API keys)
- **voice-ws Layer**: Full tool instances with all secrets

This keeps sensitive data secure while enabling powerful tool functionality.

### 3. Dynamic Tool Loading

Tools are loaded from database at runtime, enabling:

- Runtime configuration without code deployment
- Per-organization customization
- Easy addition of new tools
- Tool versioning and updates

### 4. Multi-Tenant with RLS

Strong data isolation using:

- `organization_id` on all tenant tables
- Row-Level Security policies in database
- Tenant context injection via middleware
- No cross-tenant data leakage possible

### 5. Agent Greeting

Automatic greeting when agent enters room:

- Eliminates awkward silence
- Personalized with agent name
- Sets clear user expectation
- Improves user experience

## Next Steps

- Explore [Quick Start Guide](quick_start.md)
- Read [Setup Guide](setup.md)
- Learn about [Architecture](../01_architecture/)
- Understand [Voice Agents](../01_architecture/voice_agents.md)
- Review [Development Guidelines](../../AGENTS.md)

## Roadmap

### Completed ✅

- Multi-tenant architecture
- RBAC system
- Stripe billing
- Email notifications
- Voice agent core system
- Pipecat tool integration
- Google Calendar tool
- OpenTelemetry observability

### In Progress 🚧

- Additional tool implementations
- Comprehensive testing
- Agent analytics dashboard

### Planned 📋

- Multi-LLM support (OpenAI, Claude, etc.)
- Conversation history and playback
- Tool composition and chaining
- Tool dependencies and versioning
- Advanced error handling
- Multi-language support
- Kubernetes deployment
- CI/CD pipeline

## Support & Community

- **Documentation**: See `docs/` folder
- **Issue Tracking**: GitHub Issues
- **Contribution**: See [AGENTS.md](../../AGENTS.md)

## License

[Add your license information here]

---

**Built with ❤️ for the future of AI-powered voice interactions.**
