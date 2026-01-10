# Documentation Index

This directory contains comprehensive documentation for the AI Voice Agent Platform.

## Documentation Structure

### 01_business/

Business context and requirements

- [Product Requirements Document (PRD)](01_business/prd.md) - Complete product requirements, features, and scope

### 02_architecture/

System architecture and technical design

- [Platform Architecture Overview](02_architecture/platform_architecture.md) - High-level system architecture
- [Voice Agents Architecture](02_architecture/voice_agents_architecture.md) - Voice agent system design
- [LiveKit Integration Architecture](02_architecture/livekit_integration.md) - LiveKit real-time communication
- [Tool Calling Architecture](02_architecture/tool_calling_architecture.md) - How tool functions work with LLMs

### 03_implementation/

Implementation details and development notes

- [Voice Agents Implementation](03_implementation/voice_agents_implementation.md) - Voice agent implementation guide
- [LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md) - How we wrap tool methods for LLMs
- [Dynamic Tool Loading](03_implementation/dynamic_tool_loading.md) - Runtime tool configuration from database
- [Agent Greeting Implementation](03_implementation/agent_greeting.md) - Agent greeting when entering rooms
- [Tool Calling Challenges & Solutions](03_implementation/tool_calling_challenges.md) - Problems we faced and how we solved them

### 04_development_guides/

Development and contribution guides

- [Development Setup](04_development_guides/development_setup.md) - How to set up development environment
- [Backend Development](04_development_guides/backend_development.md) - Backend development guidelines
- [Frontend Development](04_development_guides/frontend_development.md) - Frontend development guidelines
- [Worker Development](04_development_guides/worker_development.md) - Worker development guidelines
- [Testing Guide](04_development_guides/testing.md) - Testing strategies and tools
- [Code Style Guidelines](04_development_guides/code_style.md) - Coding conventions and best practices

### 05_operations/

Operations, deployment, and monitoring

- [Docker Deployment](05_operations/docker_deployment.md) - Docker deployment guide
- [Environment Configuration](05_operations/environment_config.md) - Environment variables setup
- [OpenTelemetry Setup](05_operations/opentelemetry_setup.md) - Observability and monitoring setup
- [Billing & Stripe Integration](05_operations/billing_integration.md) - Stripe payment integration
- [OAuth Setup](05_operations/oauth_setup.md) - Google OAuth authentication setup

### 06_archives/

Historical documentation and legacy docs

- [Legacy Architecture](06_archives/legacy_architecture.md) - Original architecture docs
- [Legacy Implementation](06_archives/legacy_implementation.md) - Original implementation notes

## Quick Links

- **New to the project?** Start with [Platform Architecture Overview](02_architecture/platform_architecture.md)
- **Want to understand voice agents?** Read [Voice Agents Architecture](02_architecture/voice_agents_architecture.md)
- **Building a new tool?** Check [LiveKit Tool Wrapping](03_implementation/livekit_tool_wrapping.md)
- **Setting up development?** See [Development Setup](04_development_guides/development_setup.md)
- **Deploying to production?** Read [Docker Deployment](05_operations/docker_deployment.md)

## Key Design Decisions

### Multi-Tenancy

- Shared database + shared schema with `tenant_id` columns
- Row-Level Security (RLS) in PostgreSQL for data isolation
- Tenant context injected via middleware

### Tool System Architecture

- **Dynamic Tool Loading**: Tools fetched from database at runtime
- **Two-Tier Service**: Frontend gets safe responses, worker gets full objects with OAuth tokens
- **LiveKit Wrapper Pattern**: Tool methods wrapped to remove `self` parameter for LiveKit compatibility
- **Optional Parameters**: Must use `type | None = None` for truly optional fields (Pydantic 2.x)

### LiveKit Integration

- **LiveKit Room Creation**: Webhook validates agent, LiveKit dispatch creates room, worker extracts phone from room name
- **No Session Manager**: Worker fetches tools directly from database each call
- **Function Wrapping**: Tool methods wrapped with exact parameter signatures for LLM compatibility
- **Agent Greeting**: Automatic greeting when agent enters room

### Observability

- **OpenTelemetry**: Manual instrumentation for traces, metrics, and logs
- **Collector Architecture**: Centralized OTLP collector with CORS support
- **New Relic Integration**: Collector forwards to New Relic for visualization

## Recent Changes

### LiveKit Tool Wrapping (January 2026)

- Fixed tool calling with LiveKit agents by implementing proper wrapper functions
- Challenge: Tool methods have `self` parameter, but LiveKit cannot accept bound methods
- Solution: Create standalone wrapper with exact same signature, delegate to bound method
- Key insight: Must use explicit parameters, not `**kwargs`, for Pydantic model creation

### Agent Greeting (January 2026)

- Added automatic greeting when agent enters LiveKit room
- Greets user with agent name from database
- Eliminates awkward silence when agent joins

### Tool Architecture Refactoring (December 2025)

- Moved to dynamic tool loading from database
- Separated concerns between worker and backend APIs
- Implemented two-tier service pattern for different security needs

## Legacy Documentation

Legacy documentation from the original SaaS platform implementation has been moved to `06_archives/`. These docs describe the billing, RBAC, OAuth, and other foundational systems that were built before the voice agent functionality was added.

## Maintaining Documentation

When making changes:

1. Update relevant architecture docs in `02_architecture/`
2. Add implementation details to `03_implementation/`
3. Update guides in `04_development_guides/`
4. Add challenges and solutions to `03_implementation/tool_calling_challenges.md`

## Questions?

For questions about:

- **Business requirements**: See `01_business/prd.md`
- **System design**: Check `02_architecture/`
- **How to implement**: Read `03_implementation/`
- **How to contribute**: Follow `04_development_guides/`
