# Local Docker development

Docker Compose and manual image builds for **local development**. Production
deploys use GCP Cloud Run + OCI — see [deployment/README.md](README.md).

## Services (docker-compose)

| Service | Dockerfile | Build context | Port |
|---------|------------|---------------|------|
| `backend` | `backend/Dockerfile` | repo root | 8000 |
| `frontend` | `frontend/Dockerfile` | `./frontend` | 3000 |
| `voice-ws` | `voice-ws/Dockerfile` | repo root | 7860 |
| `otel-collector` | `otel-collector/Dockerfile` | repo root | 4317, 4318, 13133 |

> The legacy LiveKit `worker/` service is not used when `VOICE_TRANSPORT=pipecat`.

## docker-compose

```bash
cp .env.example .env
# Edit .env with your credentials

docker-compose up --build              # all services
docker-compose up backend              # one service
docker-compose up --build voice-ws
docker-compose logs -f backend
docker-compose down
```

## Manual image builds

```bash
# Backend
docker build -t backend-dev -f backend/Dockerfile .
docker run -p 8000:8000 --env-file .env backend-dev

# Frontend
docker build -t frontend-dev \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key \
  --build-arg NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com \
  --build-arg NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_... \
  -f frontend/Dockerfile \
  frontend
docker run -p 3000:3000 frontend-dev

# voice-ws
docker build -t voice-ws-dev -f voice-ws/Dockerfile .
docker run -p 7860:7860 --env-file .env voice-ws-dev
```

## Health checks

| Service | Endpoint | Expected |
|---------|----------|----------|
| Backend | `GET /health` | `{"status":"healthy"}` |
| Backend | `GET /health/ready`, `/health/live` | 200 OK |
| Frontend | `GET /api/health` | healthy JSON |
| voice-ws | `GET /health` | healthy JSON |

## Dockerfile notes

### Backend
- Context: repo root (needs `shared/`)
- Non-root user: `fastapi`
- Starts: `uvicorn main:app --host 0.0.0.0 --port 8000`

### Frontend
- Multi-stage: `deps` → `builder` → `runner`
- Next.js `output: "standalone"`
- `NEXT_PUBLIC_*` must be `--build-arg` at build time

### voice-ws
- Context: repo root (needs `shared/`)
- WebSocket server on port 7860
- Routes: `/ws`, `/twilio`, `/health`

### OTel Collector (optional)
- Ports: 4317 (gRPC), 4318 (HTTP), 13133 (health)
- Disabled in production cloud deploy (`OTEL_ENABLED=false`)

## Production builds

Production uses `./scripts/deploy.sh`, which builds `linux/amd64` images locally
and pushes to GCP Artifact Registry. See [quick-reference.md](quick-reference.md).
