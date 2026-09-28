# Documentation Summary

Central index for all documentation in the AI Voice Agent Platform.

## 🧭 Roadmap & Status

- **[Sprint Board](SPRINT-BOARD.md)** — Current status, in-progress work, and voice-focused backlog (reconciled 2026-06-19).
- **[Feature Priority List](PRIORITY-LIST.md)** — Feature backlog with effort/impact and sprint planning.
- **Product direction: Voice-first.** Chat agents (F3) and general multi-channel (F14) remain deprioritized; browser-based AI avatars are an evaluated, separately priced extension documented in [AI Avatar + Voice Evolution Analysis](05_business/AI_AVATAR_VOICE_EVOLUTION_ANALYSIS.md).

- **[Role-specific dashboard](02_features/dashboard.md)** — Live call metrics, role scope, follow-up work and credit capacity.

## 📖 Documentation Structure

- **[Homepage experience](02_features/homepage-experience.md)** — Home-only visual design, particle storytelling, day/night themes, and validation.
- **[Public theme](02_features/public-theme.md)** — Shared day/night atmosphere, header, and footer across homepage, industry pages, demos, request-demo, and auth.
- **[Platform tour](02_features/platform-tour.md)** — Guided /how-it-works chapters with replayable app-view previews.

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

### Platform operations and launch

- **[Master-data seeding runbook](05_operations/master_data_seeding_runbook.md)** - Copy-paste review, plan, apply, reset, and troubleshooting commands
- **[Master-data catalog and seeding](03_implementation/master_data_seeding.md)** - Domain inventory, seed ledger, operator workflow, and provider boundaries
- **[Master-data launch strategy](05_operations/master_data_launch_strategy.md)** - Initial industries, competitive pricing signals, unit economics, and review-gated paid-plan hypothesis

### 02_features/ - Platform Features (NEW)

Comprehensive documentation organized by feature.

#### User onboarding

- **[Role-aware product walkthrough](02_features/user_onboarding/product_tour.md)** - First-login tour, role-specific steps, skip/restart behavior, and extension guidance

#### Voice Agents

1. **[Voice Agents Overview](02_features/voice_agents/overview.md)** - Voice agent system and lifecycle
2. **[Tool Connection States](02_features/voice_agents/tool_connection_states.md)** - Visual feedback for tool authentication status
3. **[Public Organization and Demo Agent Pages](02_features/voice_agents/public_agent_pages.md)** - Public agent publishing, demo agents, API contracts, billing behavior, and tests
4. **[Embed Call Button Plan](03_implementation/EMBED_CALL_BUTTON_PLAN.md)** - Embeddable call button feature architecture
5. **[voice-ws README](../voice-ws/README.md)** - Pipecat WebSocket voice voice-ws (browser + Twilio Media Streams)
6. **[Shared Module README](../shared/README.md)** - Shared code for backend and voice-ws
7. **[Outbound phone calls](03_implementation/outbound_phone_calls.md)** - Planned outbound PSTN design (reuses Media Streams)
8. **[Call transfer to a human](03_implementation/call_transfer_to_human.md)** - Deferred native human-transfer design, interim callback workflow, phone-first Twilio flow, evaluation plan, and open decisions
9. **[Platform Skills Fork Model](03_implementation/platform_skills_fork_model.md)** - Platform skills fork/refresh architecture and UI flow
10. **[Platform Skills Management (Admin)](02_features/voice_agents/platform_skills_admin.md)** - Shared `<SkillEditor>` master-detail UI used by both the platform-admin page and the org skills tab (`OrganizationSkillsTab`); platform-admin-only with frontend + backend RBAC
11. **[Voice Templates Management (Admin)](02_features/voice_agents/voice_templates_admin.md)** - Platform-admin CRUD for Markdown-backed templates used by agent creation and editing
12. **[OAuth Token Refresh and Recovery](03_implementation/token_refresh_lock.md)** - Per-connection leases, credential-generation fencing, ambiguous-outcome recovery, and durable admin alerts
13. **[Voice Engine](02_core_systems/voice_engine.md)** - Realtime (end-to-end) + modular pipeline engines, the session-builder seam, provider factory, and per-agent `speech_config` (Phase 1 done)
14. **[Free-Tier Credit Refresh](03_implementation/free_tier_credit_refresh.md)** - pg_cron-triggered monthly credit renewal; atomic RPC race hardening
15. **[Credit Usage Enforcement and Notifications](03_implementation/credit_usage_enforcement_and_notifications.md)** - system-wide usage rates, final-call settlement, phone-number grace periods, and durable low-credit emails
16. **[Resend Agent Email Tool](03_implementation/resend_email_agent_tool.md)** - organization-configured follow-up email routes for native voice agents

### Multi-Tenancy & RBAC

1. **[System Architecture](01_architecture/system_architecture.md)** - Complete system architecture
2. **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)** - Comprehensive auth and RBAC
3. **[RBAC System](02_core_systems/rbac_system.md)** - Role-based access control implementation

### Billing & Payments

1. **[Billing Overview](02_features/billing/overview.md)** - Stripe integration and credit management
2. **[Plan Entitlements & Limits (implementation plan)](03_implementation/plan_entitlements_and_limits.md)** - Flexible plan tiers, sparse limits/features, versioning, grandfathering, and enforcement
3. **[Entitlements Implementation Tracker](03_implementation/ENTITLEMENTS_IMPLEMENTATION_TRACKER.md)** - Live progress checklist for entitlement rollout
4. **[ADR: Plan Versioning & Entitlements](01_architecture/ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md)** - Architecture decision record for immutable plan versions
5. **[ADR: Subscription-Aware Onboarding and Credit Policy](01_architecture/ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md)** - Founder onboarding, explicit free/paid activation, credit policies, and implementation boundary
6. **[Payment Flow](03_implementation/payment_flow.md)** - Complete payment workflow
7. **[Stripe Integration](03_implementation/stripe_integration.md)** - Stripe integration details
8. **[Billing Plan Management and Credit Purchase UX](03_implementation/billing_plan_management_ux.md)** - Plan changes, transition previews, cancellation, and credit purchases

### 05_operations/ - Operations

#### Deployment (production — 247ai.live)

All deployment docs: **[05_operations/deployment/](05_operations/deployment/README.md)**

1. **[Deployment index](05_operations/deployment/README.md)** — doc map, infrastructure overview, `./scripts/deploy.sh`
2. **[Quick reference](05_operations/deployment/quick-reference.md)** — day-to-day deploy commands
3. **[Runbook](05_operations/deployment/runbook.md)** — architecture, first-time setup, DNS, webhooks
4. **[Environment variables](05_operations/deployment/environment-variables.md)** — `.env.prod` reference
5. **[Local Docker](05_operations/deployment/local-docker.md)** — docker-compose for development
6. **[CI / GitHub Actions](05_operations/deployment/ci-github-actions.md)** — local staging validation, manual production promotion, and workflow secrets
7. **[Secret management](05_operations/deployment/secret-management.md)** — GCP Secret Manager, OCI Vault, GitHub OIDC, rotation, and migration safety
8. **[Current production secret map](05_operations/deployment/production-secret-map.md)** — where each secret category lives, how GitHub/GCP/OCI interact, and the soft-production launch checklist
9. **[Worktree isolation and release strategy](05_operations/deployment/worktree-and-release-strategy.md)** — local Supabase sandboxes, shared staging, and production promotion

#### Other operations

1. **[Cloud staging environment](05_operations/staging_environment.md)** — shared release-validation DB; not for concurrent worktree sandboxes
2. **[Stripe Management](05_operations/stripe_management.md)** — CLI tool for managing Stripe products

### Phone Numbers

1. **[Phone Numbers PRD](PRD-phone-numbers.md)** - Complete phone number management feature including:
   - User stories and acceptance criteria
   - Purchase flow and credit pricing
   - Agent assignment workflow
   - Cancellation policy
   - **API Documentation** - All endpoints with request/response formats
2. **[Phone-number lifecycle](02_core_systems/phone_number_lifecycle.md)** - Source-of-truth routing, platform purchase, customer-owned import, webhook security, rental billing, release retries, and test/live-gate policy

### Authentication & OAuth

1. **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)** - Complete auth system
2. **[Backend redirect OAuth](02_features/authentication_rbac/backend-redirect-oauth.md)** - Canonical Google + LinkedIn sign-in flow
3. **[Social OAuth architecture](02_features/authentication_rbac/social-oauth-architecture.md)** - Architecture, credentials, and key files
4. **[LinkedIn sign-in (backend redirect)](02_features/authentication_rbac/linkedin-direct-oidc.md)** - LinkedIn Developer Portal setup
5. **[Google Identity Services sign-in](02_features/authentication_rbac/google-identity-services.md)** - Legacy GIS notes (historical)
6. **[OAuth Setup](02_core_systems/oauth_setup.md)** - GCP / LinkedIn console configuration

### Observability

1. **[Observability Overview](02_features/observability/overview.md)** - OpenTelemetry implementation overview
2. **[OpenTelemetry Implementation](02_core_systems/opentelemetry_implementation.md)** - OTEL implementation
3. **[Operating observability](05_operations/observability.md)** - Local verification, production cloud profile, signal definitions, privacy and alert thresholds
4. **[Production Observability, Monitoring, Traceability & Alerting Plan (historical)](05_operations/observability-monitoring-plan.md)** - Earlier assessment and roadmap retained for decision history

### Tools System

1. **[Tool Connection States](02_features/voice_agents/tool_connection_states.md)** - Visual feedback for tool authentication status
2. **[Tool System](../voice-ws/README.md)** - Tool architecture and Pipecat runtime integration
3. **[Dynamic Tool Architecture](03_implementation/dynamic_tool_architecture.md)** - Dynamic tool loading design
4. **[Tool Implementation Summary](03_implementation/tool_implementation_summary.md)** - Tool implementation details including Gmail tool
5. **[Resend Agent Email Tool](03_implementation/resend_email_agent_tool.md)** - Native route-based Resend tool, contract, configuration, and operational limits

### Notifications

1. **[Notifications Overview](02_features/notifications/overview.md)** - Email notification system
2. **[Notification Implementation Summary](../NOTIFICATION_IMPLEMENTATION_SUMMARY.md)** - Implementation details (legacy)

### Development

1. **[AGENTS.md](../AGENTS.md)** - AI agent coding guidelines
2. **[Getting Started Dev](03_development/getting_started.md)** - Quick start for developers
3. **[Development Setup](05_operations/deployment/worktree-and-release-strategy.md)** - Isolated local dev environment setup
4. **[Test User Cleanup](04_development_guides/cleanup_test_user.md)** - Remove test/sandbox users and their resources
5. **[Agent Evaluations](04_development_guides/agent-evaluations.md)** - Deterministic tool workflows and model trace checks
6. **[Integration-function acceptance gate](04_development_guides/testing.md#integration-function-acceptance-gate)** - Agent checklist for semantic fit, runtime wiring, side effects, and evidence-based review

## 🎯 Quick Start Guide

### New to the Platform?

1. Read **[Project Overview](00_getting_started/project_overview.md)** - Understand what the platform does
2. Follow **[Quick Start](00_getting_started/quick_start.md)** - Get running in minutes
3. Review **[Setup Guide](00_getting_started/setup.md)** - Configure environment properly
4. Explore **[System Architecture](01_architecture/system_architecture.md)** - Understand system design

### Working on Voice Agents?

1. Read **[Voice Agents Overview](02_features/voice_agents/overview.md)** - Voice agent system
2. Study **[Tool System](../voice-ws/README.md)** - Tool architecture
3. Review **[voice-ws README](../voice-ws/README.md)** - Pipecat voice worker
4. Check **[Shared Module](../shared/README.md)** - Shared code architecture

### Building a New Tool?

1. Read **[Tool System](../voice-ws/README.md)** - Understand tool architecture
2. Study **[Dynamic Tool Architecture](03_implementation/dynamic_tool_architecture.md)** - Runtime loading design
3. Study **[Tool Implementation Summary](03_implementation/tool_implementation_summary.md)** - Implementation details
4. See existing tools in `shared/voice_agents/tools/implementations/`

### Implementing Phone Numbers?

1. Read **[Phone Numbers PRD](PRD-phone-numbers.md)** - Complete feature specification
2. Read **[Phone-number lifecycle](02_core_systems/phone_number_lifecycle.md)** for implementation and ownership decisions
3. Read **[Maintenance jobs and horizontal scaling](02_core_systems/maintenance_jobs.md)** before enabling multiple backend scheduler instances
4. Review API Documentation section in the PRD
5. Check **[Backend Phone Numbers Module](../backend/src/phone_numbers/)** - Implementation details

### Implementing Billing?

1. Read **[Billing Overview](02_features/billing/overview.md)** - System overview
2. Review **[Payment Flow](03_implementation/payment_flow.md)** - Complete workflow
3. Check **[Stripe Integration](03_implementation/stripe_integration.md)** - Implementation details

### Deploying to Production?

1. Follow **[Local Docker](05_operations/deployment/local-docker.md)** — docker-compose for development
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
- Pipecat tool integration
- Tool calling challenges
- voice-ws setup and operation
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
- voice-ws development guide
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
- **voice-ws**: See **[voice-ws README](../voice-ws/README.md)** and **[Voice Agents Overview](02_features/voice_agents/overview.md)**
- **Shared**: See **[Shared Module README](../shared/README.md)**

### By Feature

- **Voice Agents**: See **[Voice Agents Overview](02_features/voice_agents/overview.md)** and **[Platform Skills Fork Model](03_implementation/platform_skills_fork_model.md)**
- **Tools**: See **[Tool System](../voice-ws/README.md)** and **[Dynamic Tool Architecture](03_implementation/dynamic_tool_architecture.md)**
- **Authentication**: See **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)**
- **Multi-tenancy**: See **[System Architecture](01_architecture/system_architecture.md)**
- **Billing**: See **[Billing Overview](02_features/billing/overview.md)**
- **Phone Numbers**: See **[Phone Numbers PRD](PRD-phone-numbers.md)**
- **RBAC**: See **[Authentication & RBAC Overview](02_features/authentication_rbac/overview.md)**

### By Task

- **Setup**: See **[Getting Started Dev](03_development/getting_started.md)**
- **Deployment**: See **[Deployment docs](05_operations/deployment/README.md)**
- **Development**: See **[Development Guides](04_development_guides/)**
- **Testing**: See **[Testing Guide](04_development_guides/testing.md)**, the **[Integration-function acceptance gate](04_development_guides/testing.md#integration-function-acceptance-gate)**, **[Agent Evaluations](04_development_guides/agent-evaluations.md)**, and **[Comprehensive Testing Plan](04_development_guides/TESTING_PLAN.md)**
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

- ✅ **Voice transport (Phases 1–3):** Pipecat WebSocket is the only transport — browser `/ws`, Twilio `/twilio`, Gemini Realtime, modular speech pipeline, shared tools, MCP, and skills. See **[ADR](01_architecture/ADR_VOICE_WS_PIPECAT.md)** and **[Phase 3](03_implementation/voice_ws_phase3.md)**.
- 🚀 **Production deploy on `247ai.live`** — **`./scripts/deploy.sh`** (GCP Cloud Run + OCI voice-ws + Supabase). See **[Deployment docs](05_operations/deployment/README.md)**.
- ✅ GCP Artifact Registry + Cloud Run deploy scripts; Alembic monorepo path fix for production migrations

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

- Check **[Deployment docs](05_operations/deployment/README.md)**
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
3. Learn **[Tool System](../voice-ws/README.md)**
4. Review **[Billing Overview](02_features/billing/overview.md)**

### Advanced (3+ months)

1. Study **[Dynamic Tool Architecture](03_implementation/dynamic_tool_architecture.md)**
2. Understand **[Dynamic Tool Loading](03_implementation/dynamic_tool_architecture.md)**
3. Review **[Payment Flow](03_implementation/payment_flow.md)**
4. Explore **[Observability Overview](02_features/observability/overview.md)**
5. Implement **[Custom Tools](../shared/voice_agents/tools/implementations/)**

## 🎯 Key Concepts

### Voice Agents

- **Agent Configuration**: System prompts, greetings, phone numbers
- **Tool Integration**: Dynamic tool loading and execution
- **Real-Time Communication**: Pipecat WebSocket via `voice-ws` (browser + Twilio Media Streams)
- **LLM Integration**: Google Gemini Realtime API

### Multi-Tenancy

- **Organization Isolation**: Data separation by organization
- **Row-Level Security**: Database-level access control
- **Tenant Context**: Middleware-based tenant injection

### Tool System

- **Dynamic Loading**: Tools loaded from database at runtime
- **Function-Level Control**: Enable/disable individual tool functions or the full catalog
- **OAuth Integration**: Secure token management
- **Tool Wrapping**: Pipecat-compatible function schemas for LLM tool calls

### Billing

- **Stripe Integration**: Subscription-based billing
- **Credit Management**: Track usage and credits
- **Plan-Based Tiers**: Multiple pricing tiers
- **Webhook Handling**: Real-time payment status updates

## 🔗 External Resources

### Official Documentation

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Supabase Documentation](https://supabase.com/docs)
- [Stripe Documentation](https://stripe.com/docs)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

### Project Resources

- **[AGENTS.md](../AGENTS.md)** - AI agent coding guidelines
- **[Backend README](../backend/README.md)** - Backend service details
- **[Frontend README](../frontend/README.md)** - Frontend service details
- **[voice-ws README](../voice-ws/README.md)** - Pipecat voice voice-ws details
- **[Shared README](../shared/README.md)** - Shared module documentation

---

**Note**: Documentation is continuously evolving. Check back regularly for updates.
