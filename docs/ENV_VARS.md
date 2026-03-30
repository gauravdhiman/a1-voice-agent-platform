# Environment Variables Reference

All environment variables required for production deployment across all 4 services.

> **Full deployment guide:** [docs/DEPLOY.md](DEPLOY.md)
> **Detailed env config notes:** [docs/05_operations/environment_configuration.md](05_operations/environment_configuration.md)

## Services

| Service | Runtime | Render Plan |
|---|---|---|
| `cog-backend` | FastAPI (Python) | Standard ($25/mo) |
| `cog-frontend` | Next.js (Node) | Starter ($7/mo) |
| `cog-worker` | LiveKit Voice Agent (Python) | Standard ($25/mo) |
| `cog-otel-collector` | OpenTelemetry Collector | Starter ($7/mo, optional) |

---

## Backend (`cog-backend`)

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `SUPABASE_URL` | Supabase project URL | Supabase Dashboard → Settings → API → Project URL | No |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key | Supabase Dashboard → Settings → API → service_role | **Yes** |
| `SUPABASE_ANON_KEY` | Supabase anon key | Supabase Dashboard → Settings → API → anon | **Yes** |
| `DATABASE_URL` | PostgreSQL connection string for Alembic migrations | Supabase Dashboard → Settings → Database → Connection Info | **Yes** |
| `STRIPE_SECRET_KEY` | Stripe live secret key | Stripe Dashboard → Developers → API Keys → Secret key (Live mode) | **Yes** |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | Stripe Dashboard → Developers → Webhooks → signing secret | **Yes** |
| `TWILIO_ACCOUNT_SID` | Twilio account identifier | Twilio Console → Account Info | No |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Twilio Console → Account Info | **Yes** |
| `GOOGLE_OAUTH_TOOL_CLIENT_ID` | Google OAuth client ID | Google Cloud Console → APIs & Services → Credentials | No |
| `GOOGLE_OAUTH_TOOL_CLIENT_SECRET` | Google OAuth client secret | Google Cloud Console → APIs & Services → Credentials | **Yes** |
| `GOOGLE_OAUTH_TOOL_REDIRECT_URI` | Google OAuth redirect URI | Set to `https://cog-backend.onrender.com/auth/google/callback` | No |
| `JWT_SECRET_KEY` | JWT signing secret | Generate: `openssl rand -hex 32` | **Yes** |
| `CORS_ORIGINS` | JSON array of allowed frontend origins | Set to `["https://cog-frontend.onrender.com"]` (update for custom domain) | No |
| `ENVIRONMENT` | Runtime environment | Set to `production` | No |
| `DEBUG` | Debug mode flag | Set to `false` | No |

---

## Worker (`cog-worker`)

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `SUPABASE_URL` | Supabase project URL | Same as backend | No |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key | Same as backend | **Yes** |
| `SUPABASE_ANON_KEY` | Supabase anon key | Same as backend | **Yes** |
| `LIVEKIT_API_KEY` | LiveKit API key | cloud.livekit.io → project → Settings → Keys | **Yes** |
| `LIVEKIT_API_SECRET` | LiveKit API secret | cloud.livekit.io → project → Settings → Keys | **Yes** |
| `LIVEKIT_URL` | LiveKit WebSocket URL | cloud.livekit.io → project → Settings (starts with `wss://`) | No |
| `LIVEKIT_SIP_DOMAIN` | LiveKit SIP domain | cloud.livekit.io → project → SIP settings | No |
| `GEMINI_API_KEY` | Google Gemini API key | Google AI Studio → API Keys | **Yes** |
| `ENVIRONMENT` | Runtime environment | Set to `production` | No |
| `DEBUG` | Debug mode flag | Set to `false` | No |

---

## Frontend (`cog-frontend`)

> **Note:** Frontend build args (`NEXT_PUBLIC_*`) are baked into the Next.js bundle at build time. Set them under **Settings → Build & Deploy → Docker Build Arguments** in Render, then trigger a manual deploy.

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Set to `https://cog-backend.onrender.com` (update for custom domain) | No |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | Same as `SUPABASE_URL` | No |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | Same as `SUPABASE_ANON_KEY` | **Yes** |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe live publishable key | Stripe Dashboard → Developers → API Keys → Publishable key (Live mode) | No |
| `NEXT_PUBLIC_LIVEKIT_URL` | LiveKit WebSocket URL | Same as `LIVEKIT_URL` | No |
| `NODE_ENV` | Node environment | Set to `production` | No |

---

## OTel Collector (`cog-otel-collector`) — Optional

> Skip this service for initial launch. Set `OTEL_ENABLED=false` on backend/worker and disable frontend OTel (`NEXT_PUBLIC_OTEL_ENABLED=false`) to skip observability entirely.

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `NEW_RELIC_LICENSE_KEY` | New Relic ingest license key | New Relic → API Keys → INGEST - LICENSE | **Yes** |
| `FRONTEND_URL` | Production frontend URL (for CORS headers) | Set to `https://cog-frontend.onrender.com` | No |

---

## Quick Checklist Before Deploying

- [ ] Production Supabase project created and `alembic upgrade head` run against it
- [ ] Stripe switched to Live mode
- [ ] LiveKit Cloud production project created
- [ ] Twilio account upgraded from trial (required for programmatic phone number purchasing)
- [ ] All `Secret?=Yes` values stored in a team password manager (1Password, Doppler, etc.)
- [ ] `render.yaml` reviewed — update `NEXT_PUBLIC_API_URL` if using a custom domain

See [docs/DEPLOY.md](DEPLOY.md) for the full step-by-step deployment runbook.
