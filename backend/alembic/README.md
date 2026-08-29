# Database Migrations with Alembic

This directory contains database migration files for the multi-tenant SaaS platform.

## Setup

1. Make sure you have installed the development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Set the DATABASE_URL environment variable with your Supabase connection string:

   ```bash
   export DATABASE_URL="postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"
   ```

   You can also add this to the selected root environment file, normally
   `.env.local` for local work or `.env.staging` / `.env.prod` for cloud
   migrations.

## Getting Your Supabase Database URL

1. Go to your Supabase project dashboard
2. Navigate to "Settings" → "Database"
3. Under "Connection String", you'll see a string like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres
   ```
4. Copy this URL and set it as your DATABASE_URL environment variable

Note: For migration purposes, you'll need to use the `postgres` user with the database password, not the anon or service role keys.

## Running Migrations

### Apply all pending migrations

```bash
# Using environment variable
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
alembic upgrade head

# Or using DATABASE_URL from the selected root environment file
alembic upgrade head

# Or using Docker (development environment)
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic upgrade head
```

### Apply the initial RBAC migration specifically

```bash
# Using local environment
alembic upgrade 91759229c32b

# Or using Docker (development environment)
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic upgrade 91759229c32b
```

### Rollback the last migration

```bash
alembic downgrade -1

# Or using Docker (development environment)
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic downgrade -1
```

### Rollback to a specific revision

```bash
alembic downgrade <revision_id>

# Or using Docker (development environment)
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic downgrade <revision_id>
```

### Create a new migration

```bash
alembic revision -m "Description of the migration"

# Or using Docker (development environment)
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic revision -m "Description of the migration"
```

### Create a new migration with auto-generation (if using SQLAlchemy models)

```bash
alembic revision --autogenerate -m "Description of the migration"

# Or using Docker (development environment)
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic revision --autogenerate -m "Description of the migration"
```

## Migration Workflow

1. Make changes to your database schema (add tables, columns, etc.)
2. Create a new migration file:
   ```bash
   alembic revision -m "Add new feature table"
   ```
3. Edit the generated migration file in `alembic/versions/` to implement the schema changes
4. Apply the migration:
   ```bash
   alembic upgrade head
   ```

When multiple worktrees create migrations at the same time, each worktree may
temporarily create a separate Alembic branch. Before merging into `main`,
inspect the graph without connecting to a database:

```bash
python scripts/deploy/check_alembic_compatibility.py --repository-only
```

If it reports multiple heads, create the merge revision on the integration
branch after all feature migrations are present:

```bash
cd backend
alembic merge -m "merge migration heads" <head-one> <head-two>
```

Review the merge revision and rerun the repository check. It intentionally has
no schema operations; its purpose is to join already-applied migration
branches into one release-order head.

## Important Notes

- This project uses a hybrid approach: Alembic for schema migrations and Supabase client for runtime data operations
- Do not modify the database schema directly through Supabase - always use migrations
- The initial migration (`91759229c32b_add_initial_rbac_tables.py`) sets up the RBAC tables
- Always test migrations in a development environment before applying to production
- Alembic and SQLAlchemy are development dependencies only and not included in the production requirements
- For local development, add DATABASE_URL to the selected root environment file
  (`.env.local` by default; use `ENV_FILE=.env.staging` when appropriate)
- When using Docker, the environment variables are loaded from the selected root
  environment file via the `env_file` directive in the Compose files
