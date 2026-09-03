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
# Create .env.local once from .env.local.example and edit it with credentials.
# For staging instead, use: ./start.sh start dev --env staging

./start.sh start dev                   # app services; uses an already-running local Supabase
./start.sh start dev --env staging     # all services, cloud staging Supabase
./start.sh logs dev
./start.sh stop dev
```

`start` and `restart` run `alembic upgrade head` through the backend image
before bringing up application services, and use `docker compose up -d
--build` so dependency changes are installed. A migration or image build
failure stops startup; do not bypass it by starting individual application
containers manually. The staging command mutates the shared staging database,
so use it for one release candidate at a time.

`start.sh` manages the application Compose project only; it does not create or
isolate a Supabase project. For a complete isolated environment per Git
worktree, use the worktree launcher instead:

```bash
./scripts/worktree-stack.sh up
./scripts/worktree-stack.sh status
./scripts/worktree-stack.sh down       # preserves local database volumes
```

The launcher creates a worktree-specific Supabase CLI project, applies the
worktree's Alembic migrations, synchronizes master data, and seeds the same
three local email/password accounts plus a staging-shaped `Pleasant Pediatric`
organization, `Alex` appointment agent with Call History enabled, and native
Google Calendar appointment tool link. OAuth state is intentionally not copied. It then starts
frontend/backend/voice-ws on a deterministic port slot. Its local seed creates
the neutral `24x7 AI Demo Studio` organization with the Pleasant Pediatric
appointment demo and Copper Ridge Heating & Air lead-capture demo. See [the
worktree and release strategy](worktree-and-release-strategy.md) for setup,
cleanup, and the shared-staging rule.

Provider settings for a worktree are copied from `--source-env` when supplied,
otherwise from the worktree's `.env.local`, the main checkout's `.env.local`,
or the example file. The generated `.worktree-state/app.env` is ignored local
state. On every `config` or `up`, a non-placeholder `GEMINI_API_KEY` from that
source is synchronized into the generated runtime env, including after a key
rotation. If the source has no usable value, an existing real worktree value
is preserved; `up` refuses to start when the resulting value is missing or an
example key instead of allowing a voice worker to start with an unusable
credential.

The isolated worktree launcher enables recordings for the seeded opted-in test
agent and stores them locally under that worktree's ignored
`.local-data/call-recordings/` directory. The regular local Compose profile
keeps recording disabled unless `VOICE_RECORDING_ENABLED=true` is set.

Local development also needs a valid Fernet `ENCRYPTION_KEY` because the
backend encrypts organization provider credentials before storing them. The
setup script and `start.sh` generate and persist a local key automatically when
the template placeholder is present. The worktree launcher generates a
separate key per worktree and preserves it across restarts. Staging and
production keys must remain deployment-managed secrets and are never generated
by these local helpers.

## Manual image builds

```bash
# Backend
docker build -t backend-dev -f backend/Dockerfile .
docker run -p 8000:8000 --env-file .env.local backend-dev

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
docker run -p 7860:7860 --env-file .env.local voice-ws-dev
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
