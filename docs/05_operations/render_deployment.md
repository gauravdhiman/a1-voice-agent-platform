# Production Deployment Guide — Render.com

This guide covers deploying all platform services to Render.com using the `render.yaml` Blueprint.

## Architecture Overview

| Service | Type | Plan | URL Pattern |
|---|---|---|---|
| `cog-backend` | Web Service | Standard ($25/mo) | `https://cog-backend.onrender.com` |
| `cog-frontend` | Web Service | Starter ($7/mo) | `https://cog-frontend.onrender.com` |
| `cog-worker` | Background Worker | Standard ($25/mo) | — (no HTTP) |
| `cog-otel-collector` | Web Service | Starter ($7/mo) | `https://cog-otel-collector.onrender.com` |

**Estimated monthly cost: ~$64/mo** (or ~$32/mo if OTel Collector skipped)

> **OTel Collector is optional.** For initial launch, you can skip it and point the backend/worker directly to New Relic's OTLP endpoint. See [Skip OTel Collector](#option-b-skip-otel-collector-use-new-relic-directly) below.

---

## Prerequisites

Before deploying, gather all credentials:

### Supabase (Production Project)
- Create a **separate Supabase project** for production (do not reuse dev)
- Go to Project Settings → API:
  - `SUPABASE_URL` — Project URL
  - `SUPABASE_SERVICE_KEY` — service_role key (keep secret)
  - `SUPABASE_ANON_KEY` — anon key
  - `NEXT_PUBLIC_SUPABASE_URL` — same as SUPABASE_URL
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — same as SUPABASE_ANON_KEY
- Go to Settings → Database → Connection Info:
  - `DATABASE_URL` = `postgresql://postgres:<password>@<project-ref>.supabase.co:5432/postgres`

### Stripe (Production Mode)
- Switch to **Live mode** in Stripe Dashboard
- `STRIPE_SECRET_KEY` — starts with `sk_live_...`
- `STRIPE_PUBLISHABLE_KEY` / `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` — starts with `pk_live_...`
- `STRIPE_WEBHOOK_SECRET` — create after deployment (see [Stripe Webhooks](#4-configure-stripe-webhooks))

### Twilio (Production Account)
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`

### LiveKit Cloud
- Create a production project at cloud.livekit.io
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_URL` — e.g., `wss://your-project.livekit.cloud`
- `LIVEKIT_SIP_DOMAIN` — your SIP domain

### Google OAuth
- Create production OAuth credentials at console.cloud.google.com
- `GOOGLE_OAUTH_TOOL_CLIENT_ID`
- `GOOGLE_OAUTH_TOOL_CLIENT_SECRET`
- `GOOGLE_OAUTH_TOOL_REDIRECT_URI` — `https://cog-backend.onrender.com/auth/google/callback`

### AI Models
- `GEMINI_API_KEY` — from Google AI Studio

### New Relic (Optional — for OTel)
- `NEW_RELIC_LICENSE_KEY` — from New Relic → API Keys → INGEST - LICENSE

### Auth
- `JWT_SECRET_KEY` — generate a secure random string: `openssl rand -hex 32`

---

## Deployment Steps

### 1. Run Database Migrations

Run Alembic migrations against your production Supabase before deploying services:

```bash
# From project root
cd backend
DATABASE_URL="postgresql://postgres:<password>@<project-ref>.supabase.co:5432/postgres" \
  alembic upgrade head
```

Verify all migrations applied:
```bash
alembic current
```

### 2. Deploy via Render Blueprint

**Option A: Connect via Render Dashboard**
1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click **New** → **Blueprint**
3. Connect your GitHub repository
4. Render detects `render.yaml` automatically
5. Review services → click **Apply**

**Option B: Render CLI**
```bash
# Install Render CLI
npm install -g @render-oss/render-cli

# Authenticate
render login

# Deploy blueprint
render blueprint apply
```

### 3. Configure Environment Variables

After the Blueprint creates services, set all `sync: false` env vars in Render Dashboard:

For each service → Settings → Environment Variables:

**cog-backend:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
SUPABASE_ANON_KEY=<anon_key>
DATABASE_URL=postgresql://postgres:<password>@<project-ref>.supabase.co:5432/postgres
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_... (set after step 4)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
GOOGLE_OAUTH_TOOL_CLIENT_ID=...
GOOGLE_OAUTH_TOOL_CLIENT_SECRET=...
GOOGLE_OAUTH_TOOL_REDIRECT_URI=https://cog-backend.onrender.com/auth/google/callback
JWT_SECRET_KEY=<random_32_bytes_hex>
CORS_ORIGINS=["https://cog-frontend.onrender.com"]
```

**cog-worker:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
SUPABASE_ANON_KEY=<anon_key>
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_SIP_DOMAIN=...
GEMINI_API_KEY=...
```

**cog-otel-collector** (if deploying):
```
NEW_RELIC_LICENSE_KEY=...
FRONTEND_URL=https://cog-frontend.onrender.com
```

**cog-frontend** (Docker Build Args — requires re-deploy):
> Build args are set under **Settings → Build & Deploy → Docker Build Arguments**
```
NEXT_PUBLIC_API_URL=https://cog-backend.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
NEXT_PUBLIC_OTEL_ENABLED=true
NEXT_PUBLIC_OTEL_SERVICE_NAME=cog-frontend-prod
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://cog-otel-collector.onrender.com/v1/traces
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://cog-otel-collector.onrender.com/v1/metrics
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://cog-otel-collector.onrender.com/v1/logs
```

After setting build args, trigger a manual deploy for `cog-frontend`.

### 4. Configure Stripe Webhooks

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://cog-backend.onrender.com/billing/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the signing secret and set `STRIPE_WEBHOOK_SECRET` in cog-backend env vars
5. Trigger a re-deploy of cog-backend

### 5. Configure Google OAuth Redirect URIs

In Google Cloud Console → Credentials → your OAuth client:
- Add Authorized redirect URI: `https://your-project.supabase.co/auth/v1/callback`
- Add Authorized redirect URI: `https://cog-backend.onrender.com/auth/google/callback`

In Supabase Dashboard → Authentication → Providers → Google:
- Set Client ID and Secret

### 6. Verify Health Checks

Once all services are deployed and running:

```bash
# Backend
curl https://cog-backend.onrender.com/health
# Expected: {"status":"healthy",...}

curl https://cog-backend.onrender.com/health/ready
curl https://cog-backend.onrender.com/health/live

# Frontend
curl https://cog-frontend.onrender.com/api/health
# Expected: {"status":"healthy","service":"cog-frontend",...}

# OTel Collector (if deployed)
curl https://cog-otel-collector.onrender.com
# Expected: health check response on port 13133
```

### 7. Configure Custom Domain (Optional)

In Render Dashboard → your web service → Settings → Custom Domains:
1. Add your domain (e.g., `app.yourdomain.com` for frontend, `api.yourdomain.com` for backend)
2. Add the CNAME record to your DNS provider as shown
3. Render provisions SSL automatically

After adding custom domain, update:
- `CORS_ORIGINS` in cog-backend: `["https://app.yourdomain.com"]`
- `NEXT_PUBLIC_API_URL` build arg in cog-frontend: `https://api.yourdomain.com`
- Stripe webhook URL
- Google OAuth redirect URIs
- LiveKit allowed origins

---

## Option B: Skip OTel Collector (Use New Relic Directly)

For a simpler initial deployment, skip `cog-otel-collector` and send telemetry directly to New Relic.

**cog-backend** (update these env vars):
```
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://otlp.nr-data.net:4317
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_TRACES_INSECURE=false
OTEL_EXPORTER_OTLP_TRACES_HEADERS=api-key=<NEW_RELIC_LICENSE_KEY>
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://otlp.nr-data.net:4317
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_METRICS_INSECURE=false
OTEL_EXPORTER_OTLP_METRICS_HEADERS=api-key=<NEW_RELIC_LICENSE_KEY>
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://otlp.nr-data.net:4317
OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_LOGS_INSECURE=false
OTEL_EXPORTER_OTLP_LOGS_HEADERS=api-key=<NEW_RELIC_LICENSE_KEY>
```

For **cog-frontend**, disable OTel entirely in build args:
```
NEXT_PUBLIC_OTEL_ENABLED=false
```

---

## Automatic Deployments

Render auto-deploys on push to the connected branch (default: `main`).

To configure:
- Dashboard → service → Settings → Build & Deploy → Auto-Deploy: **Yes**
- Branch: `main`

---

## Environment Variables Reference

Full list of all environment variables across all services, to be stored securely in a team password manager (not in the repo):

| Variable | Service(s) | Description |
|---|---|---|
| `SUPABASE_URL` | backend, worker | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | backend, worker | Supabase service_role key |
| `SUPABASE_ANON_KEY` | backend, worker | Supabase anon key |
| `NEXT_PUBLIC_SUPABASE_URL` | frontend (build arg) | Same as SUPABASE_URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | frontend (build arg) | Same as SUPABASE_ANON_KEY |
| `DATABASE_URL` | backend | PostgreSQL connection string |
| `STRIPE_SECRET_KEY` | backend | Stripe live secret key |
| `STRIPE_WEBHOOK_SECRET` | backend | Stripe webhook signing secret |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | frontend (build arg) | Stripe live publishable key |
| `TWILIO_ACCOUNT_SID` | backend | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | backend | Twilio auth token |
| `LIVEKIT_API_KEY` | worker | LiveKit API key |
| `LIVEKIT_API_SECRET` | worker | LiveKit API secret |
| `LIVEKIT_URL` | worker | LiveKit WebSocket URL |
| `LIVEKIT_SIP_DOMAIN` | worker | LiveKit SIP domain |
| `NEXT_PUBLIC_LIVEKIT_URL` | frontend (build arg) | Same as LIVEKIT_URL |
| `GEMINI_API_KEY` | worker | Google Gemini API key |
| `JWT_SECRET_KEY` | backend | JWT signing secret |
| `CORS_ORIGINS` | backend | JSON array of allowed origins |
| `GOOGLE_OAUTH_TOOL_CLIENT_ID` | backend | Google OAuth client ID |
| `GOOGLE_OAUTH_TOOL_CLIENT_SECRET` | backend | Google OAuth client secret |
| `GOOGLE_OAUTH_TOOL_REDIRECT_URI` | backend | Google OAuth redirect URI |
| `NEW_RELIC_LICENSE_KEY` | otel-collector | New Relic ingest license key |
| `FRONTEND_URL` | otel-collector | Production frontend URL (for CORS) |

---

## Troubleshooting

**Frontend shows blank page / API errors**
- Verify `NEXT_PUBLIC_API_URL` build arg points to correct backend URL
- Rebuild frontend after updating build args (Settings → Manual Deploy)

**Backend returns 401 on all requests**
- Check `JWT_SECRET_KEY` is set correctly
- Verify Supabase keys are correct (service_role vs anon)

**Worker doesn't connect to LiveKit**
- Verify `LIVEKIT_URL` starts with `wss://` (not `ws://` for production)
- Check LiveKit Cloud dashboard for active connections

**OTel Collector not receiving data**
- On Render, services in the same region can talk via `http://<service-name>:<port>`
- Verify `cog-otel-collector` is deployed and healthy
- Check backend logs for OTel exporter errors

**Stripe webhooks failing**
- Verify webhook URL is `https://cog-backend.onrender.com/billing/webhook`
- Check `STRIPE_WEBHOOK_SECRET` matches the webhook's signing secret
- Test with Stripe CLI: `stripe trigger checkout.session.completed`

---

*Last updated: 2026-03-29*
