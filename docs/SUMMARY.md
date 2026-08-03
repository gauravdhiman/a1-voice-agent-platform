# Documentation Summary

Central index for all documentation in the AI Voice Agent Platform.

## 🧭 Roadmap & Status

- **[Sprint Board](SPRINT-BOARD.md)** — Current status, in-progress work, and voice-focused backlog (reconciled 2026-06-19).
- **[Feature Priority List](PRIORITY-LIST.md)** — Feature backlog with effort/impact and sprint planning.
- **Product direction: Voice-only.** Chat agents (F3) and multi-channel (F14) are deprioritized.

## 📖 Documentation Structure

### 00_getting_started/ - Getting Started

New to the platform? Start here.

- **[Project Overview](00_getting_started/project_overview.md)** - Platform overview, features, key innovations, and use cases
- **[Quick Start](00_getting_started/quick_start.md)** - Rapid setup with Docker Compose
- **[Setup Guide](00_getting_started/setup.md)** - Detailed configuration for local and Docker development
- **[Introduction](00_getting_started/introduction.md)** - Platform introduction and high-level concepts

### 01_architecture/ - System Architecture

Understanding how the system works.

- **[Architecture Overview](01_architecture/overview.md)** - High-level system design and components
- **[System Architecture Details](01_architecture/system_architecture.md)** - Complete system architecture with Twilio call flow
- **[Frontend Architecture](01_architecture/frontend_architecture.md)** - Frontend structure and design
- **[Backend Architecture](01_architecture/backend_architecture.md)** - Backend structure and design
- **[Twilio Call Flow](01_architecture/twilio_call_flow.md)** - Incoming call handling architecture
- **[Voice Engine: End-to-End + Pipeline Design](01_architecture/voice_engine_pipeline_design.md)** - High-level design (Mermaid) for supporting realtime + modular STT→LLM→TTS pipeline engines per agent

### Database

- **[Database Schema](DATABASE_SCHEMA.md)** - Complete database schema documentation with ER diagram

### 02_features/ - Platform Features (NEW)

Comprehensive documentation organized by feature.

#### Voice Agents

1. **[Voice Agents Overview](02_features/voice_agents/overview.md)** - Voice agent system and lifecycle
2. **[Tool Connection States](02_features/voice_agents/tool_connection_states.md)** - Visual feedback for tool authentication status
3. **[Embed Call Button Plan](03_implementation/EMBED_CALL_BUTTON_PLAN.md)** - Embeddable call button feature architecture
4. **[Worker README](../worker/README.md)** - Worker service architecture and setup
5. **[Shared Module README](../shared/README.md)** - Shared code for backend and worker
6. **[LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)** - Detailed tool wrapping implementation
7. **[Platform Skills Fork Model](03_implementation/platform_skills_fork_model.md)** - Platform skills fork/refresh architecture and UI flow
8. **[Platform Skills Management (Admin)](02_features/voice_agents/platform_skills_admin.md)** - Shared `<SkillEditor>` master-detail UI used by both the platform-admin page and the org skills tab (`OrganizationSkillsTab`); platform-admin-only with frontend + backend RBAC
9. **[Token Refresh Lock](03_implementation/token_refresh_lock.md)** - Postgres-backed per-tool lease lock preventing the multi-instance OAuth token-refresh race (lease vs advisory-lock rationale)
10. **[Voice Engine](02_core_systems/voice_engine.md)** - Realtime (end-to-end) + modular pipeline engines, the session-builder seam, provider factory, and per-agent `speech_config` (Phase 1 done)

### Multi-Tenancy & RBAC

1. **[System Architecture](01_architecture/system_architecture.md)** - Complete system architecture
2. **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)** - Comprehensive auth and RBAC
3. **[RBAC System](02_core_systems/rbac_system.md)** - Role-based access control implementation

### Billing & Payments

1. **[Billing Overview](02_features/billing/overview.md)** - Stripe integration and credit management
2. **[Payment Flow](03_implementation/payment_flow.md)** - Complete payment workflow
3. **[Stripe Integration](03_implementation/stripe_integration.md)** - Stripe integration details
4. **[Stripe Management](05_operations/stripe_management.md)** - CLI tool for managing Stripe products

### Phone Numbers

1. **[Phone Numbers PRD](PRD-phone-numbers.md)** - Complete phone number management feature including:
   - User stories and acceptance criteria
   - Purchase flow and credit pricing
   - Agent assignment workflow
   - Cancellation policy
   - **API Documentation** - All endpoints with request/response formats

### Authentication & OAuth

1. **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)** - Complete auth system
2. **[OAuth Setup](02_core_systems/oauth_setup.md)** - Google OAuth integration

### Observability

1. **[Observability Overview](02_features/observability/overview.md)** - OpenTelemetry implementation overview
2. **[OpenTelemetry Implementation](02_core_systems/opentelemetry_implementation.md)** - OTEL implementation

### Tools System

1. **[Tool Connection States](02_features/voice_agents/tool_connection_states.md)** - Visual feedback for tool authentication status
2. **[LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)** - Tool wrapping patterns and type hints handling
3. **[Dynamic Tool Architecture](03_implementation/dynamic_tool_architecture.md)** - Dynamic tool loading design
4. **[Tool Implementation Summary](03_implementation/tool_implementation_summary.md)** - Tool implementation details including Gmail tool

### Notifications

1. **[Notifications Overview](02_features/notifications/overview.md)** - Email notification system
2. **[Notification Implementation Summary](../NOTIFICATION_IMPLEMENTATION_SUMMARY.md)** - Implementation details (legacy)

### Development

1. **[AGENTS.md](../AGENTS.md)** - AI agent coding guidelines
2. **[Getting Started Dev](03_development/getting_started.md)** - Quick start for developers
3. **[Development Setup](04_development_guides/development_setup.md)** - Local dev environment setup

## 🎯 Quick Start Guide

### New to the Platform?

1. Read **[Project Overview](00_getting_started/project_overview.md)** - Understand what the platform does
2. Follow **[Quick Start](00_getting_started/quick_start.md)** - Get running in minutes
3. Review **[Setup Guide](00_getting_started/setup.md)** - Configure environment properly
4. Explore **[System Architecture](01_architecture/system_architecture.md)** - Understand system design

### Working on Voice Agents?

1. Read **[Voice Agents Overview](02_features/voice_agents/overview.md)** - Voice agent system
2. Study **[LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)** - Tool wrapping patterns
3. Review **[Worker README](../worker/README.md)** - Worker service details
4. Check **[Shared Module](../shared/README.md)** - Shared code architecture

### Building a New Tool?

1. Read **[Tool System](03_implementation/tool_system.md)** - Understand tool architecture
2. Review **[LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)** - Tool wrapping patterns
3. Study **[Tool Implementation Summary](03_implementation/tool_implementation_summary.md)** - Implementation details
4. See existing tools in `shared/voice_agents/tools/implementations/`

### Implementing Phone Numbers?

1. Read **[Phone Numbers PRD](PRD-phone-numbers.md)** - Complete feature specification
2. Review API Documentation section in the PRD
3. Check **[Backend Phone Numbers Module](../backend/src/phone_numbers/)** - Implementation details

### Implementing Billing?

1. Read **[Billing Overview](02_features/billing/overview.md)** - System overview
2. Review **[Payment Flow](03_implementation/payment_flow.md)** - Complete workflow
3. Check **[Stripe Integration](03_implementation/stripe_integration.md)** - Implementation details

### Deploying to Production?

1. Follow **[Docker Deployment](05_operations/docker_deployment.md)** - Container deployment (coming soon)
2. Configure **[Environment Variables](05_operations/environment_configuration.md)** - Production settings
3. Set up **[Observability](02_features/observability/overview.md)** - Monitoring and alerting

## 📊 Documentation Coverage

### Completed Documentation ✅

- Platform overview and features
- Feature-based documentation (NEW)
- Voice agents system
- Authentication and RBAC
- Billing system
- Notification system
- Observability
- Multi-tenancy architecture
- LiveKit tool wrapping
- Tool calling challenges
- Worker setup and operation
- Shared module documentation
- Development setup guide
- API guidelines
- Database migrations
- Testing strategies
- **Comprehensive Testing Plan** (95% coverage roadmap)
- **Phone Numbers feature** with API documentation

### In Progress 🚧

- Frontend development guide
- Backend development guide
- Worker development guide
- Shared module development guide
- Docker deployment guide
- Advanced topics
- Troubleshooting guides
- Security best practices

### Planned 📋

- Performance optimization
- CI/CD pipeline documentation
- Kubernetes deployment guide
- Multi-language support
- FAQ
- Video tutorials
- Interactive tutorials

## 🔍 Finding Documentation

### By Component

- **Frontend**: See **[Frontend Architecture](01_architecture/frontend_architecture.md)** and `frontend/README.md`
- **Backend**: See **[Backend Architecture](01_architecture/backend_architecture.md)** and `backend/README.md`
- **Worker**: See **[Worker README](../worker/README.md)** and **[Voice Agents Overview](02_features/voice_agents/overview.md)**
- **Shared**: See **[Shared Module README](../shared/README.md)**

### By Feature

- **Voice Agents**: See **[Voice Agents Overview](02_features/voice_agents/overview.md)** and **[Platform Skills Fork Model](03_implementation/platform_skills_fork_model.md)**
- **Tools**: See **[Tool System](03_implementation/tool_system.md)** and **[LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)**
- **Authentication**: See **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)**
- **Multi-tenancy**: See **[System Architecture](01_architecture/system_architecture.md)**
- **Billing**: See **[Billing Overview](02_features/billing/overview.md)**
- **Phone Numbers**: See **[Phone Numbers PRD](PRD-phone-numbers.md)**
- **RBAC**: See **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)**

### By Task

- **Setup**: See **[Getting Started Dev](03_development/getting_started.md)**
- **Deployment**: See **[Docker Deployment](05_operations/docker_deployment.md)** (coming soon)
- **Development**: See **[Development Guides](04_development_guides/)**
- **Testing**: See **[Testing Guide](04_development_guides/testing.md)** and **[Comprehensive Testing Plan](04_development_guides/TESTING_PLAN.md)**
- **Troubleshooting**: See relevant feature documentation

## 📝 Contributing to Documentation

When adding new features:

1. **Update Feature Docs** - Add to `02_features/[feature_name]/`
2. **Document Implementation** - Add details to `03_implementation/`
3. **Create Development Guide** - Add to `03_development/`
4. **Update Operations** - Add deployment notes to `05_operations/`
5. **Update SUMMARY.md** - Add links to new documentation

## 🔄 Recent Updates

### August 2026

- 🚧 **Voice transport migration (Phases 1–2):** Pipecat WebSocket + Gemini Realtime via `voice-ws/` (browser `/ws` + Twilio Media Streams `/twilio`); LiveKit worker off by default (`VOICE_TRANSPORT=pipecat`). See **[ADR](01_architecture/ADR_VOICE_WS_PIPECAT.md)**, **[Phase 1](03_implementation/voice_ws_phase1.md)**, **[Phase 2](03_implementation/voice_ws_phase2.md)**.

### January 2026

- ✅ **Reorganized documentation** into feature-based structure
- ✅ Created comprehensive getting started guide for developers
- ✅ Added feature overviews for all major platform features
- ✅ Created dedicated sections for voice agents, auth/rbac, billing, notifications, observability
- ✅ Improved documentation navigation and discoverability
- ✅ Added learning paths for beginners, intermediate, and advanced users
- ✅ Created quick reference by topic and task

### December 2025

- Documented dynamic tool loading architecture
- Documented tool architecture refactoring
- Updated agent greeting implementation

### November 2025

- Billing system implementation
- RBAC system documentation
- OAuth integration docs
- Notification system implementation

## 📞 Getting Help

### Documentation Questions

- Check relevant feature documentation in `02_features/`
- Review implementation docs in `03_implementation/`
- Read component-specific README files

### Development Questions

- Review **[AGENTS.md](../AGENTS.md)** for coding guidelines
- Check **[Getting Started Dev](03_development/getting_started.md)**
- Refer to component README files

### Operational Issues

- Check **[Docker Deployment](05_operations/docker_deployment.md)** (coming soon)
- Review **[Environment Configuration](05_operations/environment_configuration.md)**
- Check relevant feature documentation in `02_features/`

## 🎓 Learning Path

### Beginner (0-2 weeks)

1. Read **[Project Overview](00_getting_started/project_overview.md)**
2. Follow **[Getting Started Dev](03_development/getting_started.md)**
3. Study **[System Architecture](01_architecture/system_architecture.md)**
4. Complete **[Quick Start](00_getting_started/quick_start.md)**

### Intermediate (1-2 months)

1. Deep dive into **[Voice Agents Overview](02_features/voice_agents/overview.md)**
2. Understand **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)**
3. Learn **[LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)**
4. Review **[Billing Overview](02_features/billing/overview.md)**

### Advanced (3+ months)

1. Study **[LiveKit Tool Wrapping Architecture](03_implementation/livekit_tool_wrapping.md)**
2. Understand **[Dynamic Tool Loading](03_implementation/dynamic_tool_architecture.md)**
3. Review **[Payment Flow](03_implementation/payment_flow.md)**
4. Explore **[Observability Overview](02_features/observability/overview.md)**
5. Implement **[Custom Tools](../shared/voice_agents/tools/implementations/)**

## 🎯 Key Concepts

### Voice Agents

- **Agent Configuration**: System prompts, greetings, phone numbers
- **Tool Integration**: Dynamic tool loading and execution
- **Real-Time Communication**: WebRTC via LiveKit
- **LLM Integration**: Google Gemini Realtime API

### Multi-Tenancy

- **Organization Isolation**: Data separation by organization
- **Row-Level Security**: Database-level access control
- **Tenant Context**: Middleware-based tenant injection

### Tool System

- **Dynamic Loading**: Tools loaded from database at runtime
- **Function-Level Control**: Enable/disable individual tool functions
- **OAuth Integration**: Secure token management
- **Tool Wrapping**: LiveKit-compatible function wrappers

### Billing

- **Stripe Integration**: Subscription-based billing
- **Credit Management**: Track usage and credits
- **Plan-Based Tiers**: Multiple pricing tiers
- **Webhook Handling**: Real-time payment status updates

## 🔗 External Resources

### Official Documentation

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LiveKit Documentation](https://docs.livekit.io/)
- [Supabase Documentation](https://supabase.com/docs)
- [Stripe Documentation](https://stripe.com/docs)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

### Project Resources

- **[AGENTS.md](../AGENTS.md)** - AI agent coding guidelines
- **[Backend README](../backend/README.md)** - Backend service details
- **[Frontend README](../frontend/README.md)** - Frontend service details
- **[Worker README](../worker/README.md)** - Worker service details
- **[Shared README](../shared/README.md)** - Shared module documentation

---

**Note**: Documentation is continuously evolving. Check back regularly for updates.
