# 24x7 AI Startup Script

This repository includes [start.sh](start.sh), the environment-aware entry point
for starting, stopping, and managing the 24x7 AI Docker services.

## Prerequisites

- Docker and Docker Compose must be installed on your system
- Create the canonical environment file for the workflow you need. Do not
  create or maintain a root `.env` file.

## Usage

Make the script executable (already done for you):

```bash
chmod +x start.sh
```

### Starting Containers

**Development Mode:**

```bash
./start.sh start dev
```

This uses `.env.local` and an already-running local Supabase project by
default. To run the same local Docker services against cloud staging, select it
explicitly:

```bash
./start.sh start dev --env staging
```

Every `start` and `restart` command first runs `alembic upgrade head` in the
backend container and then starts the stack with `docker compose up -d
--build`. If migrations fail, the application services are not started.
Rebuilding on each start also ensures dependency changes used by voice
recordings are present in the running image.

**Production Mode:**

```bash
./start.sh start prod
```

This uses `.env.prod`, applies migrations to that selected database, and starts
the production Compose stack locally. Run it only with explicit production
release authorization. Actual 247ai.live deployment uses the protected
production promotion workflow, whose migration job must complete before any
Cloud Run or OCI deployment.

### Stopping Containers

**Development Mode:**

```bash
./start.sh stop dev
```

**Production Mode:**

```bash
./start.sh stop prod
```

### Restarting Containers

**Development Mode:**

```bash
./start.sh restart dev
```

**Production Mode:**

```bash
./start.sh restart prod
```

### Building Images

**Development Mode:**

```bash
./start.sh build dev
```

**Production Mode:**

```bash
./start.sh build prod
```

### Viewing Logs

**Development Mode:**

```bash
./start.sh logs dev
```

**Production Mode:**

```bash
./start.sh logs prod
```

### Checking Status

```bash
./start.sh status
```

### Help

```bash
./start.sh help
```

## What Gets Started

### Development Mode

- Frontend development server with hot reloading on port 3000
- Backend development server with hot reloading on port 8000
- Volumes mounted for live code updates
- Development-specific environment variables

### Production Mode

- Frontend production build served by Next.js standalone server on port 3000
- Backend production server on port 8000
- Optimized builds for performance
- Production-specific environment variables

## Accessing Services

After starting the containers, you can access:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Backend Health Check**: http://localhost:8000/health

## Environment Configuration

The repository has three canonical root environment files. The real files are
gitignored; create them from their matching committed templates. The script
validates the selected file before starting containers.

Required variables:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`

### Environment Isolation (Local vs Staging vs Production)

| File | Purpose | Supabase project |
|------|---------|------------------|
| `.env.local` | Default local development | Local Supabase (`http://127.0.0.1:54321`) |
| `.env.staging` | Selected release-candidate validation against shared cloud staging | `gdzwiwukcwbqohfwxxrx` ([staging project](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx)) |
| `.env.prod` | Production Compose and deployment | `zymiyfilulmtrmyyhvzw` |

> **Warning:** Production Supabase is for deployment and migration only. Use
> `.env.staging` only for one selected release candidate's cloud validation;
> use `scripts/worktree-stack.sh` for concurrent worktree testing. See
> [staging_environment.md](docs/05_operations/staging_environment.md).

The startup script selects the environment without copying files:

```bash
cp .env.local.example .env.local       # first-time local setup
cp .env.staging.example .env.staging   # first-time staging setup
cp .env.prod.example .env.prod         # first-time deployment setup

./start.sh config                      # inspect local selection safely
./start.sh config --env staging        # inspect staging selection safely
./start.sh config --env production     # inspect production selection safely
```

```bash
./start.sh start dev                   # .env.local + existing local Supabase
./start.sh start dev --env staging     # .env.staging
./start.sh start prod                  # .env.prod
```

### Running multiple worktrees in parallel

The startup script resolves one host-port map for the application stack. Use a
port offset to shift frontend, backend, voice-ws, and OTEL together; the offset
also gets incorporated into the Compose project name so stop/restart commands
remain isolated. This does **not** isolate the selected Supabase database, so
do not use multiple worktrees with `.env.staging` for concurrent migrations or
mutable test data.

For complete per-worktree isolation, use the full-stack launcher:

```bash
./scripts/worktree-stack.sh up
./scripts/worktree-stack.sh status
./scripts/worktree-stack.sh down       # stop while preserving local data
./scripts/worktree-stack.sh purge --yes # explicit destructive cleanup
```

It creates a dedicated local Supabase project, runs Alembic and seed setup,
and starts the app services against that local database. The generated
worktree Supabase profile keeps DB/Auth/REST/Storage/Realtime enabled while
omitting nonessential Studio, analytics, Inbucket, and Edge Runtime services
so multiple stacks can run without exhausting Docker resources. See
[`docs/05_operations/deployment/worktree-and-release-strategy.md`](docs/05_operations/deployment/worktree-and-release-strategy.md).

Each worktree receives the same staging-shaped manual-test fixture: the
`Pleasant Pediatric` organization, agent `Alex` with Call History enabled, and
the native `Google_calendar_appointment` tool (without copied OAuth state).
The launcher prints these fixed local credentials:

| Role | Email | Password |
| --- | --- | --- |
| Regular user | `regular-user@247ai.local` | `Password123!` |
| Org admin | `org-admin@247ai.local` | `Password123!` |
| Platform admin | `platform-admin@247ai.local` | `Password123!` |

The worktree launcher also carries non-placeholder voice-provider credentials
into the generated `.worktree-state/app.env`. It checks the worktree's
`.env.local` first and then the main checkout's `.env.local`, refreshing those
values on each `config` or `up`. A worktree `up` fails before starting services
if `GEMINI_API_KEY` is missing or still a template placeholder; use
`--source-env PATH` to select another private environment file.

If you intentionally need only the application-container offset, the legacy
launcher still supports:

```bash
./start.sh start dev --port-offset 20
./start.sh start dev --env staging --port-offset 40
./start.sh config --env staging --port-offset 40
```

The default map uses 3000/8000/7860 for frontend/backend/voice-ws. For an
explicit non-uniform map, set `HOST_FRONTEND_PORT`, `HOST_BACKEND_PORT`,
`HOST_VOICE_WS_PORT`, `HOST_OTEL_GRPC_PORT`, `HOST_OTEL_HTTP_PORT`, and
`HOST_OTEL_HEALTH_PORT` in the selected environment file. The resolved host
URLs, API URL, WebSocket URL, CORS origin, OAuth callback, and frontend OTEL
URLs are derived automatically.

For first-time staging setup, bootstrap an empty database before starting the
app. For an existing database, the startup migration gate is sufficient:

```bash
./scripts/bootstrap-staging-db.sh
./start.sh restart dev --env staging
```

For production deployment, use:

```bash
./scripts/deploy.sh                  # defaults to .env.prod
./scripts/deploy.sh --env-file PATH  # explicit override when needed
```

**Starting the shared local Supabase project** (only needed for the lightweight
`start.sh` flow):
```bash
supabase start        # start local Supabase
supabase status       # confirm running at http://127.0.0.1:54321
```

The per-worktree launcher creates and manages its own Supabase CLI project and
does not use this shared default project.

**Running migrations manually** (the startup commands already do this):
```bash
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic upgrade head
```

> **Note:** Local Supabase CLI v2.75+ uses ES256 JWT signing (asymmetric keys), while cloud Supabase uses HS256. The backend middleware auto-detects the algorithm via the JWT header and fetches the public key from the JWKS endpoint when ES256 is used. No manual configuration is needed when switching environments.

## Smart Features

The startup script includes several smart features:

1. **Container Status Check**: Before starting containers, the script checks if they're already running to prevent conflicts
2. **Environment Validation**: The script validates the selected canonical file and required variables
3. **Graceful Handling**: If containers are already running, the script will inform you rather than failing
4. **Build Management**: You can build images separately using the `build` command
5. **Color-coded Output**: Clear, color-coded feedback for different operations
6. **Environment Isolation**: Local, staging, and production Compose projects use separate project names

## Troubleshooting

If you encounter issues:

1. Make sure Docker is running
2. Check that ports 3000 and 8000 are not already in use
3. Verify the selected environment with `./start.sh config --env NAME`
4. Check container logs using `./start.sh logs [dev|prod]`
5. Try building images explicitly with `./start.sh build [dev|prod]`
6. If containers fail to start, check the status with `./start.sh status`
