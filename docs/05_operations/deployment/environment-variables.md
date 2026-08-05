# Production environment variables

All production services read from **`.env.cloud`** at the repo root (gitignored).
Template: **`.env.cloud.example`**. Deploy with **`./scripts/deploy.sh`**.

> **Index:** [deployment/README.md](README.md) · **Local dev config:** [environment_configuration.md](../environment_configuration.md)

## Production stack

| Service | Cloud Run / host name | URL |
|---------|----------------------|-----|
| Backend | `backend-247ai` | https://api.247ai.live |
| Frontend | `frontend-247ai` | https://www.247ai.live |
| voice-ws | OCI ARM VM + Caddy | wss://voice.247ai.live |
| Database + Auth | Supabase | project URL in `.env.cloud` |

`gcp-env-from-cloud.py` filters `.env.cloud` into per-service env files for
Cloud Run (backend) and the OCI VM (voice-ws). Frontend `NEXT_PUBLIC_*` vars are
passed as Docker build args during `./scripts/deploy.sh frontend` or `gcp`.

---

## Backend (`backend-247ai`)

| Variable | Description | Secret? |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | No |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key | **Yes** |
| `SUPABASE_ANON_KEY` | Supabase anon key | **Yes** |
| `DATABASE_URL` | PostgreSQL connection string (Alembic) | **Yes** |
| `STRIPE_SECRET_KEY` | Stripe secret key | **Yes** |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | **Yes** |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | No |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | **Yes** |
| `TWILIO_PHONE_NUMBER_SID` | Default Twilio phone number SID | No |
| `VOICE_WS_PUBLIC_URL` | Browser WebSocket base — prod: `wss://voice.247ai.live` | No |
| `VOICE_WS_TWILIO_URL` | Twilio Media Streams base — prod: `wss://voice.247ai.live` | No |
| `VOICE_TRANSPORT` | `pipecat` in production | No |
| `JWT_SECRET_KEY` | Voice session JWT (must match voice-ws) | **Yes** |
| `RESEND_API_KEY` | Resend email API key | **Yes** |
| `GOOGLE_OAUTH_TOOL_CLIENT_ID` | Google OAuth client ID (tools) | No |
| `GOOGLE_OAUTH_TOOL_CLIENT_SECRET` | Google OAuth client secret | **Yes** |
| `GOOGLE_OAUTH_TOOL_REDIRECT_URI` | Prod: `https://api.247ai.live/api/v1/tools/callback` | No |
| `CORS_ORIGINS` | Prod: `["https://www.247ai.live"]` | No |
| `APP_BASE_URL` | Prod: `https://www.247ai.live` | No |
| `ENVIRONMENT` | `production` | No |
| `DEBUG` | `false` | No |
| `MCP_ALLOW_LOCAL_URLS` | Keep `false` in production | No |
| `TOKEN_REFRESH_*` | OAuth token refresh tuning (see `.env.cloud.example`) | No |

---

## voice-ws (OCI VM)

| Variable | Description | Secret? |
|----------|-------------|---------|
| `SUPABASE_URL` | Same as backend | No |
| `SUPABASE_SERVICE_KEY` | Same as backend | **Yes** |
| `SUPABASE_ANON_KEY` | Same as backend | **Yes** |
| `JWT_SECRET_KEY` | Must match backend | **Yes** |
| `GEMINI_API_KEY` | Gemini realtime fallback | **Yes** |
| `DEEPGRAM_API_KEY` | STT pipeline fallback | **Yes** |
| `OPENAI_API_KEY` | LLM pipeline fallback | **Yes** |
| `CARTESIA_API_KEY` | TTS pipeline fallback | **Yes** |
| `CEREBRAS_API_KEY` | LLM pipeline fallback | **Yes** |
| `OPENROUTER_API_KEY` | LLM gateway fallback | **Yes** |
| `FISH_API_KEY` | TTS fallback | **Yes** |
| `AGENT_DEFAULT_TIMEZONE` | IANA tz fallback for agent prompts | No |
| `VOICE_RECORDING_TEE` | Recording tee logs (`false` default) | No |
| `TWILIO_ACCOUNT_SID` | Optional — Media Streams hang-up | No |
| `TWILIO_AUTH_TOKEN` | Pairs with account SID | **Yes** |
| `ENVIRONMENT` | `production` | No |
| `DEBUG` | `false` | No |

Per-org provider keys are stored encrypted in the database; env vars above are
**platform fallbacks**.

---

## Frontend (`frontend-247ai`)

`NEXT_PUBLIC_*` variables are baked into the Next.js bundle at **Docker build
time** via `gcp-deploy.sh` build args.

| Variable | Production value | Secret? |
|----------|------------------|---------|
| `NEXT_PUBLIC_API_URL` | `https://api.247ai.live` | No |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | No |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | **Yes** |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Google OAuth web client ID used by GIS popup sign-in | No |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | No |
| `NEXT_PUBLIC_APP_NAME` | App display name | No |
| `NEXT_PUBLIC_APP_DESCRIPTION` | App tagline | No |
| `NODE_ENV` | `production` | No |

Browser voice calls receive `wsUrl` from the backend API — no separate public
WebSocket env var is required on the frontend.

---

## OCI SSH (not in `.env.cloud`)

Set in the shell when deploying voice-ws:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OCI_SSH_HOST` | — (required) | VM public IP |
| `OCI_SSH_USER` | `ubuntu` | SSH user |
| `OCI_SSH_KEY` | `~/.ssh/oci_voice_ws` | Private key for VM access |

---

## Pre-deploy checklist

- [ ] `.env.cloud` populated from `.env.cloud.example`
- [ ] Supabase migrations applied: `./scripts/deploy.sh migrate`
- [ ] `JWT_SECRET_KEY` identical on backend and voice-ws
- [ ] `VOICE_WS_PUBLIC_URL` / `VOICE_WS_TWILIO_URL` point at production voice host
- [ ] Stripe webhooks and OAuth redirect URIs use `https://api.247ai.live`
- [ ] All **Secret?=Yes** values stored in a team password manager

See [runbook.md](runbook.md) for full deployment steps.
