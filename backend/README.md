# Backend - Multi-Tenant SaaS Platform

FastAPI backend for the multi-tenant SaaS platform with health endpoints and Docker support.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- pip

### Local Development

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (runtime + development tools)
pip install -r requirements-dev.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your configuration, including DATABASE_URL for migrations
# See docs/ENVIRONMENT.md for instructions on getting your Supabase database password

# Run the application
python main.py
```

The API will be available at [http://localhost:8000](http://localhost:8000)

## 🏗️ Architecture

### Tech Stack

- **Framework**: FastAPI 0.115.6
- **Python**: 3.11+
- **Settings**: Pydantic Settings for type-safe configuration
- **ASGI Server**: Uvicorn with auto-reload
- **Code Quality**: Black, isort
- **Testing**: pytest with async support

### Tool Metadata Synchronization

**Feature**: Sync tool authentication metadata from code to database

**Implementation**:
- Backend startup reads tool metadata from code via `tool_registry.sync_with_db()`
- Syncs `required_auth`, `auth_type`, `auth_config` to `platform_tools` table
- Frontend uses this metadata to:
  - Show "Authenticate" button for OAuth tools
  - Configure OAuth provider settings
  - Display connection status correctly

**File**: `shared/voice_agents/tool_service.py`

```python
async def sync_with_db(self) -> None:
    """
    Sync all tool metadata from code to database.
    Creates or updates platform_tools with authentication requirements.
    """
    for tool_name, tool_class in platform_tool_registry._tools.items():
        tool_instance = tool_class()
        metadata = tool_instance.metadata

        # Upsert to database
        await self.supabase.table("platform_tools").upsert({
            "name": metadata.name,
            "description": metadata.description,
            "config_schema": metadata.config_schema,
            "requires_auth": metadata.requires_auth,  # Synced
            "auth_type": metadata.auth_type,           # Synced
            "auth_config": metadata.auth_config          # Synced
        })
```

### Project Structure

```
backend/
├── config/                 # Configuration management
│   ├── __init__.py        # Config exports
│   └── settings.py        # Pydantic settings
├── src/                   # Source code modules
│   ├── auth/              # Authentication (future)
│   └── shared/            # Shared utilities
│       ├── middleware/    # Custom middleware
│       ├── exceptions/    # Exception handlers
│       └── utils/         # Utility functions
├── scripts/               # Development and deployment scripts
├── main.py                # FastAPI application entry point
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── Dockerfile            # Production container
├── Dockerfile.dev        # Development container
└── README.md
```

## 🔗 API Endpoints

### Health Endpoints

| Endpoint        | Method | Description                  |
| --------------- | ------ | ---------------------------- |
| `/`             | GET    | Root API information         |
| `/health`       | GET    | Comprehensive health check   |
| `/health/ready` | GET    | Readiness check (Kubernetes) |
| `/health/live`  | GET    | Liveness check (Kubernetes)  |

### Phone Numbers

| Endpoint                        | Method | Description                        |
| ------------------------------- | ------ | ---------------------------------- |
| `/api/v1/phone-numbers/available` | GET    | Search available phone numbers    |
| `/api/v1/phone-numbers/purchase` | POST   | Purchase a phone number           |
| `/api/v1/phone-numbers`          | GET    | List organization phone numbers   |
| `/api/v1/phone-numbers/{id}/assign` | POST | Assign number to agent             |
| `/api/v1/phone-numbers/{id}`     | DELETE | Cancel (release) a phone number   |

For detailed API documentation, see [Phone Numbers PRD](../docs/PRD-phone-numbers.md).

### Example Response

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00.000Z",
  "version": "1.0.0",
  "environment": "development",
  "checks": {
    "api": "ok"
  }
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Application Settings
APP_NAME=24x7 AI
APP_VERSION=1.0.0
DEBUG=true
ENVIRONMENT=development

# Server Settings
HOST=0.0.0.0
PORT=8000
RELOAD=true

# CORS Settings
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
CORS_CREDENTIALS=true

# Future integrations (commented out in requirements.txt)
# DATABASE_URL=
# SUPABASE_URL=
# SUPABASE_SERVICE_KEY=
# REDIS_URL=
# JWT_SECRET_KEY=
```

### Settings Management

The application uses Pydantic Settings for type-safe configuration:

```python
from config import settings

# Access configuration
print(settings.app_name)
print(settings.debug)
print(settings.cors_origins)
```

## 🐳 Docker

### Development

```bash
# Build development image
docker build -f Dockerfile.dev -t saas-backend-dev .

# Run development container
docker run -p 8000:8000 -v $(pwd):/app saas-backend-dev
```

### Production

```bash
# Build production image
docker build -t saas-backend .

# Run production container
docker run -p 8000:8000 saas-backend
```

### Docker Compose

```bash
# Development with hot reload
docker compose -f docker-compose.dev.yml up --build

# Production deployment
docker compose up --build -d
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_health.py
```

## 🛠️ Development

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Run both
black . && isort .
```

### Adding New Endpoints

1. Create new module in `src/`
2. Define Pydantic models
3. Implement endpoints with proper error handling
4. Add to main application
5. Write tests

### Future Integrations

The backend is prepared for:

- **Supabase**: Database and authentication
- **Redis**: Caching and session storage
- **JWT**: Authentication tokens
- **Middleware**: Tenant context, rate limiting
- **Background Tasks**: Async processing

### Database Migrations

This project uses Alembic for database schema migrations while continuing to use Supabase client for runtime data operations.

### Setup

1. Install development dependencies (includes Alembic and SQLAlchemy):

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Set the DATABASE_URL environment variable with your Supabase connection string:

   ```bash
   export DATABASE_URL="postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"
   ```

   You can find this connection string in your Supabase dashboard under Settings → Database → Connection String.

   **To get your database password**:

   1. Go to your Supabase project dashboard
   2. Navigate to "Settings" → "Database"
   3. Under "Connection Info", you'll see your database password (different from your Supabase project password)

### Running Migrations

#### Using Local Environment

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# Create a new migration
alembic revision -m "Description of the migration"
```

#### Using Docker (Development Environment)

```bash
# Apply all pending migrations
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic upgrade head

# Rollback the last migration
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic downgrade -1

# Create a new migration
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic revision -m "Description of the migration"
```

For more detailed information about using Alembic with this project, see [alembic/README.md](alembic/README.md).

## 📊 Monitoring

### Health Checks

- **Basic Health**: `/health` - Overall system status
- **Readiness**: `/health/ready` - Ready to receive traffic
- **Liveness**: `/health/live` - Application is running

### Production Considerations

- Health checks included for load balancers
- Non-root user in Docker for security
- Multi-stage Docker builds for optimization
- Structured logging (to be implemented)
- Metrics collection (to be implemented)

## 🔄 Next Steps

1. **Authentication**: JWT-based auth with Supabase
2. **Database**: Supabase integration with models
3. **Multi-tenancy**: Tenant context middleware
4. **API Endpoints**: CRUD operations for core entities
5. **Testing**: Comprehensive test suite
6. **Monitoring**: Logging and metrics
7. **Documentation**: OpenAPI schema optimization

## 📝 Skills System

The backend supports a **platform skills fork/refresh model** for managing reusable AI capabilities:

- **Platform Skills** (`platform_skills` table): Immutable templates maintained by platform admins. Seeded on startup from `backend/src/voice_agents/skill_seeds.py`.
- **Organization Skills** (`organization_skills` table): Editable copies forked from platform templates, created from scratch, or imported from GitHub/skills.sh URLs.
- **Agent Assignments** (`agent_skills` table): Junction table linking agents to their org's skills.
- **Update Logs** (`skill_update_logs` table): Audit trail for refresh operations.

### Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/organizations/{id}/skills/fork` | Fork a platform skill into an org library |
| `POST /api/v1/organizations/{id}/skills/{id}/refresh` | Refresh forked skill from latest platform version |
| `GET /api/v1/organizations/{id}/skills/{id}/update-check` | Check if a forked skill has updates available |
| `GET /api/v1/platform/skills` | List all platform skills (platform admin) |
| `POST /api/v1/platform/skills` | Create/update a platform skill (platform admin) |

For the full architecture, see [Platform Skills Fork Model](../docs/03_implementation/platform_skills_fork_model.md).

## 🚨 Development Commands

```bash
# Start local development
source .venv/bin/activate && python main.py

# Check code quality
black --check . && isort --check .

# Run full development stack with Docker
docker compose -f docker-compose.dev.yml up --build

# View logs
docker compose -f docker-compose.dev.yml logs -f backend-dev
```

---

For more information, see the main [project README](../README.md).
