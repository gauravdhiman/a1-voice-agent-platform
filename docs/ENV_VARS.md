# Environment Variables Reference

All environment variables required for production deployment across all services.

> **Full deployment guide:** [docs/DEPLOY.md](DEPLOY.md)
> **Detailed env config notes:** [docs/05_operations/environment_configuration.md](05_operations/environment_configuration.md)

## Services

| Service | Runtime | Render Plan |
|---|---|---|
| `cog-backend` | FastAPI (Python) | Standard ($25/mo) |
| `cog-frontend` | Next.js (Node) | Starter ($7/mo) |
| `cog-voice-ws` | Pipecat WebSocket voice voice-ws (Python) | Standard ($25/mo) |
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
| `TWILIO_PHONE_NUMBER_SID` | Default Twilio phone number SID | Twilio Console → Phone Numbers → your number → SID | No |
| `VOICE_WS_PUBLIC_URL` | Browser-reachable WebSocket base for voice-ws (e.g. `ws://localhost:7860` dev, `wss://voice.example.com` prod) | Public voice-ws host | No |
| `VOICE_WS_TWILIO_URL` | Public `wss://` base Twilio Media Streams use for phone calls (e.g. ngrok tunnel to voice-ws `:7860`). **Required for inbound/outbound PSTN** | ngrok / public tunnel or production voice-ws URL | No |
| `JWT_SECRET_KEY` | JWT signing secret for voice session tokens (must match `voice-ws`) | Generate: `openssl rand -hex 32` | **Yes** |
| `RESEND_API_KEY` | Resend email API key for notification emails | resend.com → API Keys | **Yes** |
| `GOOGLE_OAUTH_TOOL_CLIENT_ID` | Google OAuth client ID | Google Cloud Console → APIs & Services → Credentials | No |
| `GOOGLE_OAUTH_TOOL_CLIENT_SECRET` | Google OAuth client secret | Google Cloud Console → APIs & Services → Credentials | **Yes** |
| `GOOGLE_OAUTH_TOOL_REDIRECT_URI` | Google OAuth redirect URI (tool OAuth flow) | Backend `oauth_callback` handler; must match an authorized redirect URI on the GCP OAuth client. Local dev: `http://localhost:8000/api/v1/tools/callback`. Prod: `https://<backend-host>/api/v1/tools/callback`. | No |
| `CORS_ORIGINS` | JSON array of allowed frontend origins | Set to `["https://cog-frontend.onrender.com"]` (update for custom domain) | No |
| `ENVIRONMENT` | Runtime environment | Set to `production` | No |
| `DEBUG` | Debug mode flag | Set to `false` | No |
| `TOKEN_REFRESH_CHECK_INTERVAL_MINUTES` | How often (minutes) to scan for tokens nearing expiry | Default `5` (1–60) | No |
| `TOKEN_REFRESH_EXPIRY_WINDOW_MINUTES` | Refresh tokens expiring within this window (minutes) | Default `15` (1–60) | No |
| `TOKEN_REFRESH_LOCK_LEASE_SECONDS` | TTL (seconds) of the per-tool refresh lease lock; must exceed the slowest OAuth refresh round-trip | Default `120` (10–600) | No |
| `TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES` | Max OAuth refresh round-trips to run in parallel per cycle | Default `5` (1–20) | No |
| `MCP_ALLOW_LOCAL_URLS` | MCP SSRF guard bypass: allow plain `http://` and loopback/private-IP URLs for the discover/save flow. **DEV/TEST ONLY — keep `false` in production** (custom MCP servers must use https and must not point at private/metadata IPs). | `true`/`false`, default `false` | No |

---

## Voice voice-ws (`cog-voice-ws`)

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `SUPABASE_URL` | Supabase project URL | Same as backend | No |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key | Same as backend | **Yes** |
| `SUPABASE_ANON_KEY` | Supabase anon key | Same as backend | **Yes** |
| `JWT_SECRET_KEY` | Voice session JWT verification (must match backend) | Same as backend | **Yes** |
| `GEMINI_API_KEY` | Google Gemini API key (platform fallback for realtime presets) | Google AI Studio → API Keys | **Yes** |
| `DEEPGRAM_API_KEY` | Deepgram STT (pipeline preset fallback) | deepgram.com | **Yes** |
| `OPENAI_API_KEY` | OpenAI LLM (pipeline preset fallback) | platform.openai.com | **Yes** |
| `CARTESIA_API_KEY` | Cartesia TTS (pipeline preset fallback) | cartesia.ai | **Yes** |
| `CEREBRAS_API_KEY` | Cerebras LLM (pipeline preset fallback) | cerebras.ai | **Yes** |
| `OPENROUTER_API_KEY` | OpenRouter LLM (pipeline preset fallback) | openrouter.ai | **Yes** |
| `FISH_API_KEY` | Fish Audio TTS (pipeline preset fallback) | fish.audio | **Yes** |
| `AGENT_DEFAULT_TIMEZONE` | Platform fallback IANA timezone when an organization has no `organizations.timezone` set. Used by `voice-ws` to anchor the CURRENT DATE AND TIME section in agent prompts (grounds "today"/"tomorrow"/"now" reasoning). Per-org timezone is preferred — set it on the Organization settings page. | IANA tz name, e.g. `America/Phoenix`; defaults to `UTC` when unset | No |
| `VOICE_RECORDING_TEE` | Enable pass-through recording tee logging (`true`/`false`; storage not implemented yet) | Default `false` | No |
| `TWILIO_ACCOUNT_SID` | Twilio account SID (optional; enables Media Streams auto hang-up) | Twilio Console | No |
| `TWILIO_AUTH_TOKEN` | Twilio auth token (optional; pairs with account SID) | Twilio Console | **Yes** |
| `ENVIRONMENT` | Runtime environment | Set to `production` | No |
| `DEBUG` | Debug mode flag | Set to `false` | No |

Per-org provider keys (Google, Deepgram, etc.) are stored encrypted in the database and resolved at runtime; env vars above are **platform fallbacks**.

---

## Frontend (`cog-frontend`)

> **Note:** Frontend build args (`NEXT_PUBLIC_*`) are baked into the Next.js bundle at build time. Set them under **Settings → Build & Deploy → Docker Build Arguments** in Render, then trigger a manual deploy.

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Set to `https://cog-backend.onrender.com` (update for custom domain) | No |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | Same as `SUPABASE_URL` | No |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | Same as `SUPABASE_ANON_KEY` | **Yes** |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe live publishable key | Stripe Dashboard → Developers → API Keys → Publishable key (Live mode) | No |
| `NODE_ENV` | Node environment | Set to `production` | No |

Browser test calls receive `wsUrl` from the backend API; no separate public WebSocket env var is required on the frontend.

---

## OTel Collector (`cog-otel-collector`) — Optional

> Skip this service for initial launch. Set `OTEL_ENABLED=false` on backend/voice-ws and disable frontend OTel (`NEXT_PUBLIC_OTEL_ENABLED=false`) to skip observability entirely.

| Variable | Description | Where to get it | Secret? |
|---|---|---|---|
| `NEW_RELIC_LICENSE_KEY` | New Relic ingest license key | New Relic → API Keys → INGEST - LICENSE | **Yes** |
| `FRONTEND_URL` | Production frontend URL (for CORS headers) | Set to `https://cog-frontend.onrender.com` | No |

---

## Quick Checklist Before Deploying

- [ ] Production Supabase project created and `alembic upgrade head` run against it
- [ ] Stripe switched to Live mode
- [ ] `voice-ws` deployed and reachable at public `wss://` URL
- [ ] `VOICE_WS_TWILIO_URL` set on backend to that public `wss://` base (required for phone calls)
- [ ] `JWT_SECRET_KEY` identical on backend and `voice-ws`
- [ ] Twilio account upgraded from trial (required for programmatic phone number purchasing)
- [ ] All `Secret?=Yes` values stored in a team password manager (1Password, Doppler, etc.)
- [ ] `render.yaml` reviewed — update `NEXT_PUBLIC_API_URL` if using a custom domain

See [docs/DEPLOY.md](DEPLOY.md) for the full step-by-step deployment runbook.
