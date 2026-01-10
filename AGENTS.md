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

## Code Style Guidelines

### Python Backend

**Imports**: Order: standard library, third-party, local (blank lines between)
**Type Hints**: Always use type hints, Pydantic for models
**Service Pattern**: Return tuple[Result, Error] for easy error handling
**Error Handling**: Use HTTPException for API errors, log with traceback
**OpenTelemetry Tracing**: Decorate methods with tracer
**Docstrings**: Use triple quotes with Args and Returns sections
**Naming**: Classes PascalCase, functions snake_case, constants UPPER_SNAKE_CASE, private methods with leading underscore

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

### Documentation

- Keep the project documentation always up-to-date in `docs` folder, organized properly in sub-folders for each module / functionality
  - Always ensure the structure of documentation in `docs` folder is rational, intuitive to user and easy to follow.
  - Always ensure cross references to other documents or files (docs and code) are accurate and not broken.
  - For diagrams, use mermaid syntax - ensure it is valid.
- For each key directories (`backend`, `frontend`, `worker`, `shared`), add a `README.md` file with the module documentation) and keep that always up to date.
- For each key files, add a docstring with the file documentation

### Development

- Use `async/await` for all async operations
- Use `pydantic` for data validation
- Use `FastAPI` for backend APIs
- Use `Next.js` for frontend
- After making changes in files, always run `pre-commit run --all-files` to ensure code quality
- Use Docker for development and production. Even when start application on local machine for dev, use `./start.sh` script to manage docker containers.
- Never install Python packages in global scope / env. Always install it in virtual env and docker containers. Same for NodeJS too.
- You can create alembic migrations scripts but never run them without user's permission. Always ask first.

<skills_system priority="1">

## Available Skills

<!-- SKILLS_TABLE_START -->
<usage>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively. Skills provide specialized capabilities and domain knowledge.

How to use skills:

- Invoke: Bash("openskills read <skill-name>")
- The skill content will load with detailed instructions on how to complete the task
- Base directory provided in output for resolving bundled resources (references/, scripts/, assets/)

Usage notes:

- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already loaded in your context
- Each skill invocation is stateless
  </usage>

<available_skills>

<skill>
<name>doc-coauthoring</name>
<description>Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks.</description>
<location>project</location>
</skill>

<skill>
<name>docx</name>
<description>"Comprehensive document creation, editing, and analysis with support for tracked changes, comments, formatting preservation, and text extraction. When Claude needs to work with professional documents (.docx files) for: (1) Creating new documents, (2) Modifying or editing content, (3) Working with tracked changes, (4) Adding comments, or any other document tasks"</description>
<location>project</location>
</skill>

<skill>
<name>frontend-design</name>
<description>Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.</description>
<location>project</location>
</skill>

<skill>
<name>mcp-builder</name>
<description>Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).</description>
<location>project</location>
</skill>

<skill>
<name>pdf</name>
<description>Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.</description>
<location>project</location>
</skill>

<skill>
<name>pptx</name>
<description>"Presentation creation, editing, and analysis. When Claude needs to work with presentations (.pptx files) for: (1) Creating new presentations, (2) Modifying or editing content, (3) Working with layouts, (4) Adding comments or speaker notes, or any other presentation tasks"</description>
<location>project</location>
</skill>

<skill>
<name>skill-creator</name>
<description>Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.</description>
<location>project</location>
</skill>

<skill>
<name>web-artifacts-builder</name>
<description>Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts.</description>
<location>project</location>
</skill>

<skill>
<name>webapp-testing</name>
<description>Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.</description>
<location>project</location>
</skill>

<skill>
<name>xlsx</name>
<description>"Comprehensive spreadsheet creation, editing, and analysis with support for formulas, formatting, data analysis, and visualization. When Claude needs to work with spreadsheets (.xlsx, .xlsm, .csv, .tsv, etc) for: (1) Creating new spreadsheets with formulas and formatting, (2) Reading or analyzing data, (3) Modify existing spreadsheets while preserving formulas, (4) Data analysis and visualization in spreadsheets, or (5) Recalculating formulas"</description>
<location>project</location>
</skill>

</available_skills>

<!-- SKILLS_TABLE_END -->

</skills_system>
