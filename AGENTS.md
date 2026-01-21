# AI Agent Guidelines for AI Voice Agent Platform

This document provides coding guidelines and commands for AI agents working in this repository.

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
- **Mocks**: External services (Supabase Auth, Stripe, LiveKit) are mocked at the network/dependency layer.
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
- `shared/`: Shared code between backend and worker (voice_agents models, services, tools)
- `worker/`: LiveKit worker for voice AI agents
- `frontend/src/`: Next.js application (components, services, hooks, types)

### Important Patterns

1. **No Session Manager**: Worker fetches tools directly from database each call
2. **Two-Tier Tool Service**: Frontend gets safe responses, worker gets full tool objects with OAuth tokens
3. **LiveKit Room Creation**: Webhook validates agent, LiveKit dispatch creates room, worker extracts phone from room name
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
- For each key directories (`backend`, `frontend`, `worker`, `shared`), add a `README.md` file with the module documentation) and keep that always up to date.
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

### Development

- Use `async/await` for all async operations
- Use `pydantic` for data validation
- Use `FastAPI` for backend APIs
- Use `Next.js` for frontend
- IMPORTANT: Never stage the code changes in git by yourself, unless user explicitly asks you to do so. Always let user review and stage them manually.
- Use Docker for development and production. Even when start application on local machine for dev, use `./start.sh` script to manage docker containers.
- Never install Python packages in global scope / env. Always install it in virtual env and docker containers. Same for NodeJS too.
- You can create alembic migrations scripts but never run them without user's permission. Always ask first.

