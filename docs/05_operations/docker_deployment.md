# Docker Deployment Guide

This guide covers both local Docker deployment (docker-compose) and production Docker deployment via Render.com.

## Services

| Service | Dockerfile | Build Context | Port |
|---|---|---|---|
| `backend` | `backend/Dockerfile` | `.` (repo root) | 8000 |
| `frontend` | `frontend/Dockerfile` | `./frontend` | 3000 |
| `worker` | `worker/Dockerfile` | `.` (repo root) | — |
| `otel-collector` | `otel-collector/Dockerfile` | `.` (repo root) | 4317, 4318, 13133 |

## Local Development (docker-compose)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up --build

# Start specific service
docker-compose up backend

# Rebuild a single service
docker-compose up --build backend

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

## Production Docker Build (Manual)

Build and run each service manually for testing:

```bash
# Backend
docker build -t cog-backend -f backend/Dockerfile .
docker run -p 8000:8000 --env-file .env cog-backend

# Frontend (requires build args for NEXT_PUBLIC_* vars)
docker build -t cog-frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://your-backend.onrender.com \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key \
  --build-arg NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_... \
  -f frontend/Dockerfile \
  ./frontend
docker run -p 3000:3000 cog-frontend

# Worker
docker build -t cog-worker -f worker/Dockerfile .
docker run --env-file .env cog-worker

# OTel Collector
docker build -t cog-otel-collector -f otel-collector/Dockerfile .
docker run -p 4317:4317 -p 4318:4318 -p 13133:13133 \
  -e NEW_RELIC_LICENSE_KEY=your-key \
  -e FRONTEND_URL=http://localhost:3000 \
  cog-otel-collector
```

## Health Check Endpoints

| Service | Endpoint | Expected Response |
|---|---|---|
| Backend | `GET /health` | `{"status":"healthy"}` |
| Backend | `GET /health/ready` | 200 OK |
| Backend | `GET /health/live` | 200 OK |
| Frontend | `GET /api/health` | `{"status":"healthy","service":"cog-frontend"}` |
| OTel Collector | `GET /` on port 13133 | 200 OK |

## Render.com Production Deployment

For full production deployment instructions, see [render_deployment.md](render_deployment.md).

Quick summary:
1. Run database migrations: `alembic upgrade head`
2. Deploy via Render Blueprint (`render.yaml` in repo root)
3. Set secret env vars in Render Dashboard
4. Configure Stripe webhooks pointing to production backend URL
5. Set Docker build args for frontend (requires manual re-deploy)
6. Verify all health check endpoints

## Dockerfile Notes

### Backend
- Context: repo root (needs access to `shared/` module)
- Non-root user: `fastapi` (uid 1001)
- HEALTHCHECK built in (curl to `/health`)
- Starts with: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1`

### Frontend
- Multi-stage build: `deps` → `builder` → `runner`
- Uses Next.js `output: "standalone"` for minimal image size
- `NEXT_PUBLIC_*` vars must be provided as `--build-arg` (baked at build time)
- Context: `./frontend` directory only
- Non-root user: `nextjs` (uid 1001)
- Starts with: `node server.js`

### Worker
- Context: repo root (needs access to `shared/` module)
- Non-root user: `worker` (uid 1001)
- GStreamer dependencies included for audio processing
- No HTTP port — runs as persistent background process
- Starts with: `python src/worker.py start`

### OTel Collector
- Context: repo root (to access `otel-collector/config.production.yml`)
- Config baked into image at `/etc/otel-collector-config.yml`
- Env var substitution: `${env:NEW_RELIC_LICENSE_KEY}` and `${env:FRONTEND_URL}`
- Ports: 4317 (gRPC), 4318 (HTTP), 13133 (health check)
