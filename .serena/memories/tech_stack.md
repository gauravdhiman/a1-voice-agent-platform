# Tech Stack

## Backend
- Python 3.11, FastAPI 0.115, Pydantic v2, Uvicorn
- Supabase (Postgres + Auth + Storage + Realtime) — local via Docker on port 54321
- Alembic for migrations (`backend/alembic/versions/`)
- SQLAlchemy 2.0 (used by Alembic), psycopg2-binary
- Pipecat WebSocket voice runtime (`voice-ws/`), Twilio (phone numbers)
- Stripe (billing), Resend (email)
- OpenTelemetry (traces, metrics, logs)
- APScheduler (background token refresh)
- httpx (HTTP client), PyJWT, cryptography (encryption)

## Frontend
- Next.js 15.5 (App Router, Turbopack), React 19, TypeScript 5
- Tailwind CSS v4 (NOT v3 — uses `@plugin` in CSS, `@theme` blocks)
- shadcn/ui components (Radix UI primitives)
- TanStack React Query 5, TanStack React Table 8
- React Hook Form + Zod (forms/validation)
- Supabase JS client, `@pipecat-ai/client-js` + websocket transport
- Vitest 4 for unit tests (requires Node 20+ on host, NOT in container)

## voice-ws
- Python, Pipecat, Gemini Realtime + pipeline presets
- Runs in Docker; fetches tools from DB per call (no session manager)

## Infrastructure
- Docker Compose for dev (`docker-compose.dev.yml`) and prod
- Local Supabase stack (Kong, Auth, Postgres, Realtime, Storage, Studio)
- OpenTelemetry Collector
- Render.com for production deployment

## Testing
- pytest (asyncio_mode=auto) for backend + shared + voice-ws
- Vitest for frontend (run on host, not in container)
- Playwright for E2E (isolated stack)
- Coverage via pytest-cov and vitest coverage
