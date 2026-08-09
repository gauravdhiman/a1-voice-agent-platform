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

This uses `.env.local` and local Supabase by default. To run the same local
Docker services against cloud staging, select it explicitly:

```bash
./start.sh start dev --env staging
```

**Production Mode:**

```bash
./start.sh start prod
```

This uses `.env.prod`. It starts the production Compose stack locally; actual
247ai.live deployment uses `./scripts/deploy.sh`, which also defaults to
`.env.prod`.

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
| `.env.staging` | Local Docker against cloud staging | `gdzwiwukcwbqohfwxxrx` ([staging project](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx)) |
| `.env.prod` | Production Compose and deployment | `zymiyfilulmtrmyyhvzw` |

> **Warning:** Production Supabase is for deployment and migration only. Use
> `.env.staging` for cloud validation. See
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
./start.sh start dev                   # .env.local
./start.sh start dev --env staging     # .env.staging
./start.sh start prod                  # .env.prod
```

For first-time staging setup, bootstrap the database before starting the app:

```bash
./scripts/bootstrap-staging-db.sh
./start.sh restart dev --env staging
```

For production deployment, use:

```bash
./scripts/deploy.sh                  # defaults to .env.prod
./scripts/deploy.sh --env-file PATH  # explicit override when needed
```

**Starting local Supabase** (required for local dev):
```bash
supabase start        # start local Supabase
supabase status       # confirm running at http://127.0.0.1:54321
```

**Running migrations against local Supabase**:
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
