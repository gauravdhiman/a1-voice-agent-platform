# AI Agent Guidelines for 24x7 AI Platform

This document provides coding guidelines and commands for AI agents working in this repository.

## Product branding

- **Product name:** 24x7 AI (never CogniNets, CogniEnts, or NeuraSaaS in user-facing copy)
- **Website:** https://247ai.live
- **Env vars:** `APP_NAME`, `RESEND_FROM_NAME`, and `NEXT_PUBLIC_APP_NAME` should all use `24x7 AI` (emails and UI read these at runtime)

## Setup Commands

# Install Python dependencies

````bash
cd backend
activate #this will activate the virtual environment
uv pip install -r requirements-dev.txt # only run if installation of packages required, virtual env should have already existing packages.
cd .. # come back to project folder to run docker commands using .start.sh script. Prefer running the project in doc, not in local machine.

## Quick Reference Commands

### Backend (Python/FastAPI)

```bash
cd backend

pytest tests/test_rbac.py                           # Run single test file
pytest tests/test_rbac.py::TestRBAC::test_create_role  # Run single test method
pytest -v                                          # Verbose output

black .                                             # Format code
isort .                                             # Sort imports
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503  # Lint
pre-commit run --all-files                            # Run all pre-commit hooks
uvicorn main:app --reload                            # Dev server
alembic upgrade head                                 # Migrate database
alembic revision --autogenerate -m "description"     # Create migration
````

### Frontend (Next.js/TypeScript)

```bash
cd frontend

npm run dev          # Development
npm run build        # Build for production
npm run lint         # Run ESLint
npx tsc --noEmit    # Type check
```

### Docker

Run these commands from the root directory of the project.

```bash
./start.sh build dev                               # Build dev container images
./start.sh build prod                              # Build prod container images
./start.sh start dev                               # Start dev containers
./start.sh start prod                              # Start prod containers
./start.sh stop dev                                # Stop dev containers
./start.sh stop prod                               # Stop prod containers
./start.sh restart dev                             # Restart dev containers
./start.sh restart prod                            # Restart prod containers
./start.sh logs dev                                # View dev logs
./start.sh logs prod                               # View prod logs
./start.sh --help                                  # Help - print all commands
```

### End-to-End (E2E) Testing

End-to-end tests use a "Grey Box" approach with an isolated Docker stack to ensure zero side effects on production/development data.

```bash
# Run the full E2E lifecycle (Build -> Start -> Init -> Migrate -> Test -> Teardown)
./scripts/run-e2e.sh

# Run E2E and record all browser videos (useful for debugging successful flows)
./scripts/run-e2e.sh --video-on

# View E2E reports locally
open e2e/reports/report.html
```

**E2E Architecture Details**:
- **Isolated Stack**: Runs on ports 3001 (FE) and 8001 (BE) using `docker-compose.e2e.yml`.
- **Transient DB**: Uses a dedicated Postgres container initialized with Supabase schemas (`auth`) and roles.
- **Mocks**: External services (Supabase Auth, Stripe, voice-ws session tokens) are mocked at the network/dependency layer.
- **Reports**: HTML reports and failure artifacts (videos/traces) are saved to `e2e/reports/` (Git ignored).

## Code Style Guidelines

### Python Backend

**Imports**: Order: standard library, third-party, local (blank lines between)
**Type Hints**: Always use type hints, Pydantic for models
**Service Pattern**: Return tuple[Result, Error] for easy error handling
**Error Handling**: Use HTTPException for API errors, log with traceback
**OpenTelemetry Tracing**: Decorate methods with tracer
**Docstrings**: Use triple quotes with comprehensive documentation (see below)
**Naming**: Classes PascalCase, functions snake_case, constants UPPER_SNAKE_CASE, private methods with leading underscore

#### Documentation Standards

**Classes**: Always include comprehensive class-level documentation

```python
class TokenRefreshService:
    """Service for automatically refreshing OAuth tokens before they expire.

    This service runs as a background task using APScheduler to check and
    refresh OAuth tokens that are approaching expiration. It ensures that users
    don't experience authentication failures during their sessions.

    Key Features:
        - Runs every 5 minutes as a background task
        - Checks all tools with OAuth authentication
        - Refreshes tokens expiring within 15 minutes
        - Updates database with new encrypted tokens
        - Logs all refresh activities for observability

    Lifecycle:
        - Call start() to begin background refresh loop
        - Call stop() to gracefully shutdown and cancel pending refreshes

    Example:
        ```python
        service = TokenRefreshService(tool_service)
        await service.start()
        # ... service runs in background ...
        await service.stop()
        ```

    Attributes:
        tool_service: Instance of ToolService for database operations
        running: Boolean flag indicating if service is active
        task: Asyncio task running the refresh loop
    """
```

**Methods/Functions**: Always include comprehensive documentation with:
- Purpose (what it does and why)
- Arguments with types and descriptions
- Returns with types and descriptions
- Raises (if applicable)
- Example usage (for complex methods)

```python
async def get_agent_tools(
    self,
    agent_id: UUID
) -> tuple[List[AgentToolResponse], Optional[str]]:
    """Get all tools configured for an agent, including platform tool details.

    This method queries the database for all tool configurations associated with
    a specific agent. It joins with platform_tools to include metadata like
    tool name, description, and authentication requirements. The response
    excludes sensitive configuration (OAuth tokens) for security.

    Args:
        agent_id: Unique identifier of the agent to query tools for.
            Must be a valid UUID corresponding to an existing agent.
            Example: UUID('12345678-1234-5678-1234-567812345678')

    Returns:
        A tuple containing:
        - List[AgentToolResponse]: List of tool configurations with metadata.
            Each response includes tool details, connection status, and token
            expiry time (but NOT the actual OAuth tokens). Empty list if
            agent has no tools configured.
        - Optional[str]: Error message if query failed, None if successful.
            Example error: "Failed to query agent tools: connection timeout"

    Raises:
        ValueError: If agent_id is not a valid UUID.
        HTTPException: If database connection fails (propagated from Supabase client).

    Example:
        ```python
        agent_id = UUID('12345678-1234-5678-1234-567812345678')
        tools, error = await tool_service.get_agent_tools(agent_id)

        if error:
            print(f"Error: {error}")
        else:
            for tool in tools:
                print(f"Tool: {tool.tool.name}, Status: {tool.connection_status}")
        ```

    Notes:
        - Sensitive configuration (OAuth tokens, API keys) is excluded from response
        - Token expiry time is extracted from encrypted config for display purposes
        - Connection status is calculated based on auth requirements and token validity
        - Uses Supabase joined query to fetch agent_tools and platform_tools in one call
    """
    # Implementation...
```

**Simple Functions**: Still include comprehensive documentation even for simple functions

```python
def validate_token_status(
    sensitive_config: Optional[str]
) -> AuthStatus:
    """Validate authentication token status from encrypted sensitive config.

    This function determines whether an OAuth token is valid, expired, or
    missing based on the encrypted sensitive configuration stored in the database.
    It decrypts the configuration and checks the token expiration time
    with a 5-minute buffer to account for network latency.

    Args:
        sensitive_config: Encrypted JSON string containing OAuth tokens.
            Should contain 'access_token' and 'expires_at' fields.
            If None, indicates no authentication has been configured.
            If empty string, indicates invalid configuration.

    Returns:
        AuthStatus: Enum indicating the authentication state.
            - NOT_AUTHENTICATED: No tokens or invalid configuration
            - AUTHENTICATED: Valid tokens with time remaining (excluding 5-min buffer)
            - EXPIRED: Tokens exist but have expired (or within 5-min buffer)

    Example:
        ```python
        config = '{"access_token": "abc123", "expires_at": 1234567890.0}'
        status = validate_token_status(config)
        # Returns AuthStatus.AUTHENTICATED or AuthStatus.EXPIRED depending on timestamp
        ```

    Notes:
        - Uses decrypt_data() to decrypt the sensitive_config
        - 5-minute buffer prevents last-minute refresh failures
        - Returns NOT_AUTHENTICATED for any decryption errors
    """
    # Implementation...
```

```python
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

async def get_user(user_id: UUID) -> tuple[Optional[User], Optional[str]]:
    """Get user by ID."""
    pass

class UserService:
    async def create_user(self, data: UserCreate) -> tuple[Optional[User], Optional[str]]:
        try:
            return user, None
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return None, str(e)

from opentelemetry import trace
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("service.method_name")
async def method_name():
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(user.id))
```

### Frontend (TypeScript/React)

**No browser alerts**: Never use `window.confirm()`, `window.alert()`, or `window.prompt()`. Always use modal Dialog components for user confirmations and notifications.
**Component Structure**: Use interface for props, cn utility for className
**Service Pattern**: Return {success, error?, data?} object
**Type Safety**: Use type annotations and import types from @/types
**Naming**: Components PascalCase, hooks camelCase with "use" prefix, services camelCase with "service" suffix, types/interfaces PascalCase, constants UPPER_SNAKE_CASE

#### Documentation Standards

**Components**: Always include JSDoc comments with prop descriptions

```typescript
/**
 * ToolCard component displays a tool's connection status and allows users to
 * configure or disconnect tools.
 *
 * Features:
 * - Shows connection status badge (connected/disconnected/auth-required)
 * - Displays time until token expiry
 * - Opens configuration drawer on click
 * - Supports both authenticated and non-authenticated tools
 *
 * @example
 * ```tsx
 * <ToolCard
 *   tool={platformTool}
 *   agentTool={agentTool}
 *   onConnect={() => handleConnect(tool.name)}
 *   onDisconnect={() => handleDisconnect(agentTool.id)}
 * />
 * ```
 */
interface ToolCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Platform tool metadata including name, description, auth requirements */
  tool: PlatformTool;
  /** Agent-specific tool configuration including status and expiry */
  agentTool: AgentTool;
  /** Callback when user clicks to connect/configure tool */
  onConnect: () => void;
  /** Callback when user disconnects tool */
  onDisconnect: () => void;
}

export function ToolCard({ tool, agentTool, onConnect, onDisconnect, className, ...props }: ToolCardProps) {
  // Implementation...
}
```

**Hooks**: Always include JSDoc with purpose, parameters, return value

```typescript
/**
 * Custom hook for subscribing to real-time updates for a specific agent.
 *
 * This hook manages Supabase Realtime subscriptions to automatically refresh
 * UI components when database changes occur. It handles subscription cleanup
 * on component unmount to prevent memory leaks.
 *
 * @param agentId - The UUID of the agent to subscribe to updates for
 * @param tables - Optional list of database tables to monitor (default: ['agent_tools', 'agents'])
 * @returns Object containing subscription status and error state
 *
 * @example
 * ```tsx
 * function AgentDetailPage({ params }: { params: { agentId: string } }) {
 *   const { agentId } = params
 *
 *   // Subscribe to real-time updates for this agent
 *   useRealtime(agentId, ['agent_tools', 'agents'])
 *
 *   const { data: agent } = useAgent(agentId)
 *   const { data: tools } = useAgentTools(agentId)
 *
 *   // ... component renders with automatic updates
 * }
 * ```
 */
export function useRealtime(
  agentId: string,
  tables: string[] = ['agent_tools', 'agents']
) {
  const queryClient = useQueryClient()

  useEffect(() => {
    // Implementation...
  }, [agentId, tables, queryClient])

  return {
    subscribed: true,
    error: null,
  }
}
```

**Services**: Always include JSDoc with method signatures and return types

```typescript
/**
 * Service for handling agent-related API calls and data management.
 *
 * This service provides methods for CRUD operations on voice agents,
 * including creation, updates, deletion, and fetching agent tools.
 * All methods return a consistent response object with success, error, and data.
 *
 * @example
 * ```typescript
 * const result = await agentService.getAgent(agentId)
 * if (result.success) {
 *   console.log('Agent:', result.data)
 * } else {
 *   console.error('Error:', result.error)
 * }
 * ```
 */
class AgentService {
  /**
   * Fetches a single agent by its unique identifier.
   *
   * This method retrieves agent details from the API including configuration,
   * tools, and status. It returns a structured response object that
   * can be used to handle success and error cases consistently.
   *
   * @param agentId - The UUID of the agent to fetch
   * @returns Promise resolving to response object with success flag, optional error message, and agent data
   *
   * @throws {NetworkError} When API request fails due to network issues
   * @throws {ValidationError} When agentId is not a valid UUID
   *
   * @example
   * ```typescript
   * const result = await agentService.getAgent('123e4567-e89b-12d3-a456-426614174000')
   * if (result.success) {
   *   console.log('Agent name:', result.data?.name)
   *   console.log('Tools configured:', result.data?.tools.length)
   * }
   * ```
   */
  async getAgent(agentId: string): Promise<{
    success: boolean;
    error?: string;
    data?: Agent;
  }> {
    try {
      const response = await apiClient.get(`/agents/${agentId}`)
      return { success: true, data: response.data }
    } catch (error) {
      return { success: false, error: (error as Error).message }
    }
  }
}
```

**Utility Functions**: Always include JSDoc even for simple functions

```typescript
/**
 * Formats a Unix timestamp into a human-readable time-until string.
 *
 * This function calculates the time difference between the current time
 * and the provided expiry timestamp, then returns a formatted string
 * like "5 minutes", "2 hours", or "3 days".
 *
 * @param expiresAt - Unix timestamp when token expires (in seconds)
 * @returns Formatted string like "5 minutes", "2 hours", "3 days", or "Expired"
 *
 * @example
 * ```typescript
 * formatTimeUntilExpiry(Date.now() / 1000 + 300) // Returns "5 minutes"
 * formatTimeUntilExpiry(Date.now() / 1000 - 100) // Returns "Expired"
 * formatTimeUntilExpiry(Date.now() / 1000 + 7200) // Returns "2 hours"
 * ```
 */
export function formatTimeUntilExpiry(expiresAt: number): string {
  const now = Date.now() / 1000
  const diff = expiresAt - now

  if (diff <= 0) return 'Expired'

  const minutes = Math.floor(diff / 60)
  const hours = Math.floor(diff / 3600)
  const days = Math.floor(diff / 86400)

  if (days > 0) return `${days} day${days > 1 ? 's' : ''}`
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`
  return `${minutes} minute${minutes > 1 ? 's' : ''}`
}
```

```typescript
import * as React from "react"
import { cn } from "@/lib/utils"

interface ComponentProps extends React.HTMLAttributes<HTMLDivElement> {
  // props here
}

export function Component({ className, ...props }: ComponentProps) {
  return (
    <div className={cn("base-class", className)} {...props}>
      {/* content */}
    </div>
  )
}

class AuthService {
  async login(email: string, password: string): Promise<{
    success: boolean;
    error?: string;
    data?: unknown;
  }> {
    try {
      const response = await apiClient.post('/auth/login', { email, password })
      return { success: true, data: response.data }
    } catch (error) {
      return { success: false, error: (error as Error).message }
    }
  }
}
export const authService = new AuthService()
```

## Testing Guidelines

### Test-Driven Development (red-green) — REQUIRED

All code changes must follow the **red-green TDD** cycle:

1. **Red — write the test first.** Add/extend a test that asserts the *new or
   changed* behavior **before** writing the implementation. Run it and confirm
   it **fails** (for the right reason — assertion failure, missing method, etc.),
   not for an unrelated infra reason. This proves the test actually exercises the
   behavior.
2. **Green — implement the minimum to pass.** Write the implementation so the
   test passes. Re-run the test (and the surrounding suite) until green.
3. **Refactor — keep tests green.** Clean up while tests stay passing.

Rules:
- **No production code change without a corresponding test change.** If you
  changed behavior, there must be a test that would have failed without the
  change. (See also *Validation Requirements* below.)
- When fixing a bug, write a failing test that reproduces the bug first, then fix.
- When modifying existing behavior, **update the existing tests** that the change
  affects (don't delete them to make the suite pass).
- Run the relevant suite after each step (red, green, refactor) — not only at the
  end.
- Prefer focused unit tests (mock external/DB/HTTP) so behavior is deterministic
  and fast; add integration tests where the boundary itself is the risk.

### Coverage expectations

Aim for **100% coverage of changed/added code paths**, including failure/edge
branches (auth denial, errors, empty input, concurrency guards). It is acceptable
for project-wide coverage to be below 100%, but **new/changed code should not
ship with uncovered branches**. Run coverage locally (`pytest --cov`) and review
the diff's uncovered lines before considering a task done.

### Python Tests

```python
import pytest

class TestExample:
    """Test cases for example module."""

    @pytest.mark.asyncio
    async def test_something(self):
        """Test description."""
        # Arrange
        test_data = {"key": "value"}

        # Act
        result, error = await service.do_something(test_data)

        # Assert
        assert error is None
        assert result is not None
        assert result.key == "value"
```

## Project Architecture

### Key Directories

- `backend/src/`: FastAPI application code (auth, billing, voice_agents, notifications, organization)
- `shared/`: Shared code between backend and voice-ws (voice_agents models, services, tools)
- `voice-ws/`: Pipecat WebSocket voice worker (realtime + pipeline presets)
- `frontend/src/`: Next.js application (components, services, hooks, types)

### Important Patterns

1. **No Session Manager**: voice-ws fetches tools directly from database each call
2. **Two-Tier Tool Service**: Frontend gets safe responses, voice-ws gets full tool objects with OAuth tokens
3. **Voice session JWT**: Backend issues short-lived tokens; browser/Twilio connect to `voice-ws` WebSocket endpoints
4. **OpenTelemetry**: Manual instrumentation for traces, metrics, and logs throughout

## Environment Variables

- Containerized dev: Root `.env` file
- Local dev: `backend/.env` and `frontend/.env.local`
- Use `.env.example` as template

## Pre-Commit Hooks

The project uses pre-commit hooks for code quality:

- Black (Python formatter)
- isort (Python import sorter)
- Flake8 (Python linter)
- ESLint (JavaScript/TypeScript linter)
- Prettier (Code formatter for JS/TS/JSON/CSS)

Run `pre-commit run --all-files` manually before pushing.

## Important Notes

### Why Comprehensive Documentation Matters

**For Human Developers**:
- Reduces onboarding time for new team members
- Makes code review faster and more effective
- Reduces need for verbal explanations
- Enables faster debugging and troubleshooting
- Provides context when revisiting code months later

**For AI/LLMs**:
- LLMs can read and understand well-documented code
- Clear docstrings help LLMs provide accurate assistance
- Type hints and return types improve LLM code generation
- Examples and notes give LLMs context on usage patterns
- Makes AI-assisted development more effective

**Documentation Checklist**:
- ✅ Class docstring explains purpose, key features, lifecycle
- ✅ Method docstring explains what, why, args, returns, raises
- ✅ Types are explicitly defined in docstrings
- ✅ Examples provided for complex methods
- ✅ Notes section for important implementation details
- ✅ JSDoc for TypeScript with @param, @returns, @example
- ✅ Comments explain non-obvious logic, not what the code does

## Thinking

- Always think critically. You don't need to agree with user always.
  - If you feel that user's suggestion is not good or is not following best practices, guide user with constructive critical thinking and plan.
- Think and plan like a senior or principal software engineer.
  - Look for all pros and cons of your approach and then finalize.

### Documentation

- Keep the project documentation always up-to-date in `docs` folder, organized properly in sub-folders for each module / functionality
  - Always ensure the structure of documentation in `docs` folder is rational, intuitive to user and easy to follow.
  - Always ensure cross references to other documents or files (docs and code) are accurate and not broken.
  - **For diagrams, ALWAYS use Mermaid syntax** for any visual representations:
    - Flowcharts: Use `flowchart TD` or `flowchart LR`
    - Sequence diagrams: Use `sequenceDiagram`
    - Architecture diagrams: Use `graph TB` or `graph LR`
    - State diagrams: Use `stateDiagram-v2`
    - Gantt charts: Use `gantt`
    - Pie charts: Use `pie`
    - Mermaid is supported by GitHub, GitLab, and most Markdown editors
    - Always validate Mermaid syntax using https://mermaid.live/
    - Avoid ASCII art or text-based diagrams - use Mermaid instead
- For each key directories (`backend`, `frontend`, `voice-ws`, `shared`), add a `README.md` file with the module documentation) and keep that always up to date.
- For each key files, add a docstring with the file documentation

#### Database Schema Documentation

- **Keep database schema documentation up-to-date** in `docs/DATABASE_SCHEMA.md`
- **When to update database schema documentation**:
  - After creating or running any new Alembic migration
  - When adding/modifying database tables or columns
  - When adding new indexes or constraints
  - When updating RLS (Row Level Security) policies
  - When adding new table relationships or foreign keys
  - When modifying existing table relationships
- **What to update in DATABASE_SCHEMA.md**:
  - Add new table documentation (including columns, types, constraints, descriptions)
  - Update ER diagram with new tables and relationships
  - Add new indexes to the indexes section
  - Update migration history with new migration file
  - Document any new JSON schemas or configuration formats
  - Update RLS policy documentation if policies change
- **Diagram Validation**:
  - Validate Mermaid syntax using mermaid skill, if you have acess to it.
- **Migration History**:
  - Add new migrations to the migration history section in order
  - Include migration ID, descriptive name, and what changed
  - Reference the migration file path for details
- **References**:
  - Always keep migration files in sync with documentation
  - Migration files are located in `backend/alembic/versions/`
  - Use `alembic revision --autogenerate -m "description"` to create migrations
- **Example update process**:
  1. Create migration: `alembic revision --autogenerate -m "Add new feature table"`
  2. Review migration file in `backend/alembic/versions/`
  3. Run migration (with user permission)
  4. Update `docs/DATABASE_SCHEMA.md` with new table details
  5. Update ER diagram with new relationships
  6. Add migration to migration history section
  7. Update `docs/SUMMARY.md` if needed

### TODO Comments and Future Enhancements

- **Always add TODO comments** in code for future enhancements or improvements that should be addressed later
- TODO comments should be placed at the relevant location in the code where the enhancement would be implemented
- Include context in TODO comments to explain:
  - What needs to be done
  - Why it's important
  - When it should be done (e.g., "before scaling to multiple instances", "in v2.0")
  - Any alternative approaches considered
- Example TODO comment formats:

```python
# TODO: Future Enhancement
# When scaling to multiple backend instances, this approach will cause race conditions
# as each instance will attempt to refresh tokens independently.
# Migrate to Celery + Redis for distributed task queue with proper locking.
# Current approach works for single-instance deployments.

# TODO: [Feature] Add rate limiting for this endpoint
# Rationale: Prevent API abuse and ensure fair usage across organizations
# Priority: Medium
# Timeline: Before public beta launch

# TODO: [Performance] Cache frequently accessed database queries
# Rationale: Current N+1 query pattern causes performance issues at scale
# Priority: High
# Timeline: Before 1000 concurrent users

# TODO: [Security] Add CSRF protection for form submissions
# Rationale: Current implementation is vulnerable to cross-site request forgery
# Priority: Critical
# Timeline: Immediately
```

- Benefits of TODO comments:
  - Provides context during code reviews
  - Makes pending work visible to all team members
  - Helps prioritize technical debt and enhancements
  - Documents design decisions and trade-offs
  - Easier to reference when planning future sprints
- During code review, check for:
  - Are TODO comments appropriate and necessary?
  - Do they include sufficient context?
  - Should any TODOs be addressed now instead of later?
  - Are there related TODOs that should be grouped?

### Working Directory

- All changes MUST be made within this project's root directory. Do NOT modify files outside this directory (e.g. external tooling directories, etc.).
- If Docker containers are running from a different copy (e.g. a other porject  instance), stop them and recreate from this project root using `docker compose -f docker-compose.dev.yml up -d`.

### Local Development Environment

- **Backend, frontend, and voice-ws** run via Docker Compose (`docker-compose.dev.yml`).
- **Local Supabase** is used for default development (not cloud Supabase). It runs on `http://127.0.0.1:54321`.
- The `.env` file in the project root has local Supabase credentials.
- **Staging (cloud):** `.env.staging` → `gdzwiwukcwbqohfwxxrx` — use for pre-prod validation (`cp .env.staging .env`). Bootstrap: `./scripts/bootstrap-staging-db.sh`. See `docs/05_operations/staging_environment.md`.
- **Production (cloud):** `.env.cloud` → `zymiyfilulmtrmyyhvzw` (247ai.live) — deploy/migrate only. Never use for local feature testing.
- **Legacy:** `.env.dev` pointed at production; prefer `.env.staging` / `.env.cloud` instead.
- Local Google ID-token auth is enabled in `supabase/config.toml` and reads `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID` plus `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET` from the root `.env`; keep `skip_nonce_check=false`.
- Backend hot-reloads via volume mounts (`./backend:/app`, `./shared:/app/shared`).

### Test User (Local Supabase)

- **Email:** `test@cogninets.local` (legacy local-only domain; product branding is **24x7 AI**)
- **Password:** `Password123!`

### Onboarding vs invitations

- **Founder onboarding** (`/onboarding`) is only for **org admins / platform admins** of an org with `onboarding_completed === false`.
- **Invited users** skip founder onboarding and land on `/dashboard` with a soft welcome toast.
- Email signup and OAuth process `invitation_token` **before** org provisioning, so invitees join the inviting tenant instead of creating a new personal org.
- Provisioned orgs are normal orgs with a **name-based slug** (not `*-dummy-org` / `*-default-org`). There is no "dummy org" concept.
- After invite accept, set `currentOrganizationId` to the **invited org**; the org switcher still allows switching to other memberships later.

### Validation Requirements

After implementing any fix or new feature, you MUST:

1. **Add or update tests** for every code change, BEFORE raising a PR:
   - **Unit tests** (Python `pytest`): Test models, validators, service methods, PromptBuilder logic
   - **Route/integration tests** (Python `pytest`): Test API endpoints with mocked dependencies
   - **voice-ws integration tests**: Test PromptBuilder integration, tool integration
   - **Frontend tests** (if applicable): Test service methods, component behavior
   - Rule: If you changed code, there must be a corresponding test change. No exceptions.
2. **Run relevant unit/integration tests** and ensure they pass with good coverage.
3. **Use the `agent-browser` skill** to validate the change from a user's perspective:
   - Open the application at `http://localhost:3000`
   - Log in with the test account (`test@cogninets.local` / `Password123!`)
   - Navigate through the complete implemented functionality or affected workflow
   - Verify the change works as expected from the UI
4. **If browser testing reveals issues**, fix them and re-test before marking the task as done.
5. **Update documentation** if the change affects user-facing behavior, API contracts, or developer workflows:
   - `docs/DATABASE_SCHEMA.md` — Update when tables/columns change
   - `docs/` relevant section — Update when API endpoints, features, or architecture change
   - `AGENTS.md` — Update when new conventions or rules are established
6. **Clean up after browser / smoke validation.** Any artifacts created only to validate the change (temporary skills, rows, files, screenshots, permission grants, role changes) MUST be removed before the task is marked done. Browser smoke tests are not exempt from the unit/E2E rule that tests clean up after themselves. Concretely:
   - Delete any platform/org skills, agents, files, or other rows that the smoke run created (use the API where one exists; SQL only as a last resort, and prefer soft-delete when the model supports it so audit history is preserved).
   - Revert any role/permission grants made solely to reach the smoke target (e.g. granting `platform_admin` to the local test user).
   - Delete screenshots, video recordings, downloaded fixtures, and any throwaway scripts that were written only for this validation.
   - Keep cleanup scripts in `/tmp/` or under `.tmp/` and remove them too. Persistent smoke artifacts in the repo (committed PNGs, leftover fixture data) are considered a regression and must be flagged in code review.
   - The only exception is durable tests (unit, integration, E2E) where leaving fixtures is the point of the test. Smoke tests are not durable.
7. **Verify syntax/build** after every code change:
   - **Python**: Run `python -m py_compile <file>` on every changed `.py` file to confirm it compiles without syntax errors.
   - **Frontend**: Run `docker exec <container> npx tsc --noEmit` to confirm TypeScript compiles with no errors in source files (ignore pre-existing `.next/types` and test file errors).
     - **IMPORTANT**: Never run `next build` or `npm run build` inside the frontend **dev** container. The build output overwrites the `.next` directory used by the dev server, causing `ENOENT` errors and `Internal Server Error`. Instead, use `tsc --noEmit` for type checking only.
     - **Frontend unit tests (vitest) cannot run inside the frontend dev container**: the dev image ships Node 18, but `vitest@4` requires Node 20+. Running `npx vitest` in the container fails with `ERR_REQUIRE_ESM` from `vite`. Run frontend tests on the **host** instead (`cd frontend && npx vitest run <file>`), where Node 22 is available and `frontend/node_modules` is installed.
8. A task is only considered **done** when: tests are added/updated, tests pass, coverage is adequate, docs are current, syntax/build checks pass, agent browser testing confirms correct behavior, and the smoke-test cleanup in step 6 has run.

### Development

- Use `async/await` for all async operations
- Use `pydantic` for data validation
- Use `FastAPI` for backend APIs
- Use `Next.js` for frontend
- IMPORTANT: Never stage the code changes in git by yourself, unless user explicitly asks you to do so. Always let user review and stage them manually.
- CRITICAL: **NEVER commit changes to Git without explicit user approval.** The user must always review and stage changes themselves. You may make changes, run tests, and validate — but only the user commits. Always keep the user in the loop and ask for approval before any git commit.
- Use Docker for development and production. Even when start application on local machine for dev, use `./start.sh` script to manage docker containers.
- Never install Python packages in global scope / env. Always install it in virtual env and docker containers. Same for NodeJS too.
- You can create alembic migrations scripts but never run them without user's permission. Always ask first.

### Python: Avoid local imports that shadow top-level imports

Never use `from X import Y` inside a function if `Y` is already imported at the top of the file. In Python, a local import makes the name local to the **entire function** — even lines before the import statement. This causes `UnboundLocalError` on earlier references. If you need a conditional import, use a different variable name or import the module instead (`import X; X.Y`).

### Voice transport (Pipecat WebSocket — voice-ws)

- **All call surfaces** (dashboard test call, embed, public org page, Twilio phone)
  use **`voice-ws/`** (Pipecat WebSocket). Backend returns `{ token, wsUrl, sessionId }`.
- The legacy **`worker/`** LiveKit package was **removed**; history lives in git only.
- The deprecated **`livekit_inference`** preset provider slug was removed. Pipeline
  presets use direct providers only; migration
  `20260803000001_remove_livekit_inference_from_presets` rewrites any remaining DB rows.
- Browser clients use `@pipecat-ai/client-js` + `@pipecat-ai/websocket-transport` (`WS /ws`).
- Phone calls use Twilio Media Streams → `voice-ws` `WS /twilio`. Set **`VOICE_WS_TWILIO_URL`** to a public `wss://` base (ngrok); localhost is rejected.
- Session auth is a short-lived `voice_ws_session` JWT (`shared/voice_agents/voice_session_service.py`), signed with `JWT_SECRET_KEY` shared by backend and voice-ws.
- Phase 3 parity lives in `voice-ws/src/session_setup.py`, `src/tools/`, and
  `src/speech/`. Platform tools register via `shared/voice_agents/tools/base/platform_tool_registry.py`.
- OpenTelemetry in `voice-ws/src/main.py` uses lazy imports so tests/dev images
  without OTLP exporters still start; add `opentelemetry-exporter-otlp-proto-grpc`
  to `voice-ws/requirements.txt` for full export in prod.
- Local `Google_calendar_mcp` (`http://127.0.0.1:8733/mcp`) is started as a
  co-process by `voice-ws/entrypoint.dev.sh`. If calendar tools are missing at runtime, recreate
  `voice-ws-dev` — a plain uvicorn CMD will not start the connector.
- After changing `voice-ws/requirements.txt`, rebuild the image
  (`docker compose -f docker-compose.dev.yml build voice-ws-dev`); restart alone
  does not install new packages.
- Docs: `docs/01_architecture/ADR_VOICE_WS_PIPECAT.md`, `docs/03_implementation/voice_ws_phase1.md`, `docs/03_implementation/voice_ws_phase2.md`, `docs/03_implementation/voice_ws_phase3.md`.

### Frontend: Tailwind CSS v4

This project uses **Tailwind CSS v4**, which has a fundamentally different configuration system from v3:

- **Plugins**: Add via `@plugin` directive in `globals.css`, NOT via `require()` in `tailwind.config.js`.
  ```css
  /* In src/app/globals.css */
  @import "tailwindcss";
  @plugin "@tailwindcss/typography";
  ```
- **Theme customization**: Uses `@theme inline {}` blocks in CSS, not `theme.extend` in JS config.
- **Custom variants**: Use `@custom-variant` in CSS (e.g., `@custom-variant dark (&:is(.dark *))`).
- **The `tailwind.config.js`** file still exists for `content` paths and color definitions, but the `plugins` array should remain empty — all plugins go in CSS.
- After adding a new `@plugin`, the frontend container may need a restart for Tailwind to regenerate CSS.

### Continuous Learning (Self-Update)

After every significant implementation, debugging session, or resolved issue, **self-analyze what was learned** and update this file (`AGENTS.md`) if any of the following apply:

- A **new "do" or "don't"** was discovered (e.g., "don't run `next build` in the dev container")
- A **technology-specific gotcha** was hit (e.g., Tailwind v4 plugin system differs from v3)
- A **project convention** was established or clarified through trial and error
- A **debugging pattern** was found that would save time in the future
- A **best practice** was validated or invalidated for this specific codebase

**What to update:**
- Add the learning to the most relevant section in this file (e.g., frontend gotchas go under "Frontend: Tailwind CSS v4", backend patterns go under "Python Backend")
- If no section fits, create a new subsection under the appropriate parent
- Keep entries concise — lead with the rule, then briefly explain why

**What NOT to add:**
- One-off fixes that are obvious from the code or git history
- Generic programming knowledge that any developer would know
- Temporary workarounds that will be removed soon

This ensures that `AGENTS.md` evolves into a living knowledge base that prevents repeated mistakes and encodes project-specific expertise. The goal is that any agent (or developer) reading this file gets the full picture of how to work effectively in this codebase.

### Skill Creation (Reusable Workflows)

When a process, workflow, or technique proves valuable through repeated use or significant trial-and-error, consider whether it should become a **reusable skill** in the `.claude/skills/` project directory.

**When to create a skill:**
- A multi-step workflow was refined through iteration and is likely to be reused (e.g., a specific testing pattern, a deployment checklist, a code review process)
- A complex domain-specific procedure was figured out that would be hard to rediscover (e.g., how to set up a specific integration, a migration strategy)
- The knowledge is **procedural** ("how to do X step by step") rather than **declarative** ("always do X") — declarative rules belong in `AGENTS.md`

**When NOT to create a skill (put it in `AGENTS.md` instead):**
- Simple rules, conventions, or do's/don'ts → `AGENTS.md`
- Technology-specific gotchas or config notes → `AGENTS.md`
- One-time processes that won't be repeated → nowhere (it's in git history)

**Skill vs AGENTS.md boundary:**
| Type of Knowledge | Where It Goes |
|-------------------|---------------|
| "Don't run `next build` in dev container" | `AGENTS.md` (simple rule) |
| "Tailwind v4 uses `@plugin` in CSS" | `AGENTS.md` (config note) |
| "How to create and validate an Alembic migration end-to-end" | **Skill** (multi-step procedure) |
| "How to set up and run E2E tests with the isolated Docker stack" | **Skill** (complex workflow) |
| "How to analyze a competitor repo and produce implementation docs" | **Skill** (reusable methodology) |

**Skill management guidelines:**
- Keep the number of project-level skills small and focused — quality over quantity
- Each skill should have clear boundaries — if two skills overlap, merge them
- Store project-level skills in the `.claude/` project directory (not in the repo itself)
- Review existing skills before creating new ones to avoid duplication

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
