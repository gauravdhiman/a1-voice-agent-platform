# Deployment Runbook — Render.com

Step-by-step guide for deploying the Voice AI Agents Platform to Render.com production.

> **Environment variables reference:** [docs/ENV_VARS.md](ENV_VARS.md)
> **Full ops guide:** [docs/05_operations/render_deployment.md](05_operations/render_deployment.md)

## Architecture

4 services deployed to Render.com:

| Service | Type | Estimated Cost |
|---|---|---|
| `cog-backend` (FastAPI) | Web Service — Standard | $25/mo |
| `cog-frontend` (Next.js) | Web Service — Starter | $7/mo |
| `cog-worker` (LiveKit Voice Agent) | Background Worker — Standard | $25/mo |
| `cog-otel-collector` (OTel, optional) | Web Service — Starter | $7/mo |

**Total: ~$57–64/mo** (skip OTel collector to save $7/mo)

---

## Prerequisites

Gather all credentials before starting. See [docs/ENV_VARS.md](ENV_VARS.md) for the full list.

1. **Supabase** — create a production project (separate from dev):
   - Run database migrations first: `cd backend && alembic upgrade head`
   - Collect: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`, `DATABASE_URL`

2. **Stripe** — switch to Live mode:
   - Collect: `STRIPE_SECRET_KEY` (`sk_live_...`), `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (`pk_live_...`)
   - `STRIPE_WEBHOOK_SECRET` is created in step 5

3. **Twilio** — must be a paid account (trial cannot purchase numbers):
   - Collect: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

4. **LiveKit Cloud** — create a production project at cloud.livekit.io:
   - Collect: `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`, `LIVEKIT_SIP_DOMAIN`

5. **Google OAuth** — production credentials from Google Cloud Console:
   - Collect: `GOOGLE_OAUTH_TOOL_CLIENT_ID`, `GOOGLE_OAUTH_TOOL_CLIENT_SECRET`

6. **JWT secret** — generate a secure random value:
   ```bash
   openssl rand -hex 32
   ```

7. **New Relic** (optional, for observability):
   - Collect: `NEW_RELIC_LICENSE_KEY`

---

## Step 1 — Run Database Migrations

Run Alembic migrations against production Supabase **before** deploying backend:

```bash
cd backend
DATABASE_URL="postgresql://postgres:<password>@<project-ref>.supabase.co:5432/postgres" \
  alembic upgrade head

# Verify all migrations applied
alembic current
```

---

## Step 2 — Connect GitHub Repo to Render

1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click **New** → **Blueprint**
3. Connect your GitHub account and select the `a1-voice-agent-platform` repository
4. Render detects `render.yaml` automatically and shows a preview of all 4 services
5. Review → click **Apply**

> Render creates all services in draft state. They will not deploy until env vars are set.

---

## Step 3 — Set Environment Variables

For each service in Render Dashboard → service → **Settings → Environment Variables**:

### cog-backend
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
SUPABASE_ANON_KEY=<anon_key>
DATABASE_URL=postgresql://postgres:<password>@<project-ref>.supabase.co:5432/postgres
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...   ← set after Step 5
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=<auth_token>
TWILIO_PHONE_NUMBER_SID=<phone_number_sid>
LIVEKIT_API_KEY=<api_key>
LIVEKIT_API_SECRET=<api_secret>
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_SIP_DOMAIN=<sip_domain>
RESEND_API_KEY=<resend_api_key>
GOOGLE_OAUTH_TOOL_CLIENT_ID=<client_id>
GOOGLE_OAUTH_TOOL_CLIENT_SECRET=<client_secret>
GOOGLE_OAUTH_TOOL_REDIRECT_URI=https://cog-backend.onrender.com/auth/google/callback
JWT_SECRET_KEY=<generated_32_byte_hex>
CORS_ORIGINS=["https://cog-frontend.onrender.com"]
```

### cog-worker
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
SUPABASE_ANON_KEY=<anon_key>
LIVEKIT_API_KEY=<api_key>
LIVEKIT_API_SECRET=<api_secret>
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_SIP_DOMAIN=<sip_domain>
GEMINI_API_KEY=<gemini_key>
```

### cog-frontend (Docker Build Args)
> Set under **Settings → Build & Deploy → Docker Build Arguments** (not regular env vars)
```
NEXT_PUBLIC_API_URL=https://cog-backend.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
```

### cog-otel-collector (if deploying)
```
NEW_RELIC_LICENSE_KEY=<license_key>
FRONTEND_URL=https://cog-frontend.onrender.com
```

---

## Step 4 — Trigger First Deploy

1. In Render Dashboard, trigger a manual deploy for services in this order:
   - `cog-otel-collector` (if using) → wait for healthy
   - `cog-backend` → wait for healthy
   - `cog-worker` → wait for running
   - `cog-frontend` (last — needs backend URL baked in) → wait for healthy

2. Watch build logs for errors. Common issues:
   - Missing env var → service crashes on start (check logs)
   - Docker build failure → usually a dependency install issue

---

## Step 5 — Configure Stripe Webhooks

1. Go to Stripe Dashboard → Developers → Webhooks → **Add endpoint**
2. URL: `https://cog-backend.onrender.com/billing/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`, `updated`, `deleted`
   - `invoice.payment_succeeded`, `invoice.payment_failed`
4. Copy the signing secret → set `STRIPE_WEBHOOK_SECRET` on `cog-backend` → re-deploy backend

---

## Step 6 — Configure Google OAuth

In Google Cloud Console → Credentials → your OAuth 2.0 Client:
- Add authorized redirect URI: `https://your-project.supabase.co/auth/v1/callback`
- Add authorized redirect URI: `https://cog-backend.onrender.com/auth/google/callback`

In Supabase Dashboard → Authentication → Providers → Google:
- Set Client ID and Secret

---

## Step 7 — Verify Health Checks

```bash
# Backend health
curl https://cog-backend.onrender.com/health
# Expected: {"status":"healthy",...}

curl https://cog-backend.onrender.com/health/ready
curl https://cog-backend.onrender.com/health/live

# Frontend health
curl https://cog-frontend.onrender.com/api/health
# Expected: {"status":"healthy","service":"cog-frontend",...}

# OTel Collector (if deployed)
curl https://cog-otel-collector.onrender.com
```

---

## Step 8 — Smoke Tests

- [ ] Open `https://cog-frontend.onrender.com` — landing page loads
- [ ] Sign up / log in with Supabase auth
- [ ] Create an organization, configure an AI agent
- [ ] Test voice call through LiveKit
- [ ] Purchase a Twilio phone number (requires paid Twilio account)
- [ ] Verify Stripe subscription flow
- [ ] Check New Relic / OTel traces are arriving (if configured)

---

## Step 9 — Configure Twilio SMS Webhook

Once backend is deployed, set the Twilio incoming SMS webhook:
- URL: `https://cog-backend.onrender.com/api/sms` (or relevant endpoint)
- Set in Twilio Console → Phone Numbers → your number → Messaging

---

## Automatic Deployments

Render auto-deploys on push to `main`. To configure:
- Dashboard → service → Settings → Build & Deploy → **Auto-Deploy: Yes**

> **Note:** Frontend requires a manual re-deploy whenever build args change (e.g., backend URL update), since `NEXT_PUBLIC_*` vars are baked at build time.

---

## Custom Domain (Optional)

1. Dashboard → service → Settings → Custom Domains → Add domain
2. Add CNAME record in your DNS provider as shown
3. After adding: update `CORS_ORIGINS` (backend), `NEXT_PUBLIC_API_URL` build arg (frontend), Stripe webhook URL, Google OAuth redirect URIs

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Frontend blank page / API errors | `NEXT_PUBLIC_API_URL` build arg → rebuild frontend |
| Backend 401 on all requests | `JWT_SECRET_KEY` matches Supabase JWT secret |
| Worker not connecting to LiveKit | `LIVEKIT_URL` starts with `wss://` (not `ws://`) |
| Stripe webhooks failing | Webhook URL is `/billing/webhook`, `STRIPE_WEBHOOK_SECRET` is correct |
| OTel data missing | Services in same Render region; `OTEL_ENABLED=true`; collector healthy |

See [docs/05_operations/render_deployment.md](05_operations/render_deployment.md) for full troubleshooting details.
