# Production environment variables

Manual production deployments read from **`.env.prod`** at the repo root
(gitignored). The template is **`.env.prod.example`**. Deploy manually with
**`./scripts/deploy.sh`**.

The GitHub Actions deployment uses the same file format, but does not read a
developer's local `.env.prod`. The workflow reads the Repository secret
`ENV_PROD`, writes its contents to a temporary `.env.prod` in the CI runner,
and then runs the same deployment script. Therefore, changing a local
`.env.prod` affects manual deployments only; changing `ENV_PROD` affects CI
deployments.

> **Index:** [deployment/README.md](README.md) · **Local dev config:** [environment_configuration.md](../environment_configuration.md)

## Local Docker host-port configuration

When running local or staging application Compose services from multiple
worktrees, use `./start.sh --port-offset N` to shift the application host-port
map without editing Compose files. The observability ports are used by the
isolated worktree launcher, which shifts its application and monitoring ports
together; use `./scripts/worktree-stack.sh config` to inspect that map.

For a non-uniform application map, set `HOST_FRONTEND_PORT`,
`HOST_BACKEND_PORT`, and `HOST_VOICE_WS_PORT` in the selected environment file.
The worktree launcher additionally derives `HOST_OTEL_*`, Grafana,
Prometheus, and Alertmanager ports and updates browser endpoints from the same
offset.

## Production stack

| Service         | Cloud Run / host name | URL                        |
| --------------- | --------------------- | -------------------------- |
| Backend         | `backend-247ai`       | https://api.247ai.live     |
| Frontend        | `frontend-247ai`      | https://www.247ai.live     |
| voice-ws        | OCI ARM VM + Caddy    | wss://voice.247ai.live     |
| Database + Auth | Supabase              | project URL in `.env.prod` |

`gcp-env-from-cloud.py` filters the selected `.env.prod` into per-service env
files for Cloud Run (backend) and the OCI VM (voice-ws). Frontend
`NEXT_PUBLIC_*` vars are passed as Docker build args during
`./scripts/deploy.sh frontend` or `gcp`.

For CI, the selected file is the temporary file generated from `ENV_PROD`; for
manual deployment, it is the local `.env.prod` file.

---

## Backend (`backend-247ai`)

| Variable                                             | Description                                                                                                  | Secret?                               |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------- |
| `SUPABASE_URL`                                       | Supabase project URL                                                                                         | No                                    |
| `SUPABASE_SERVICE_KEY`                               | Supabase service_role key                                                                                    | **Yes**                               |
| `SUPABASE_ANON_KEY`                                  | Supabase anon key                                                                                            | **Yes**                               |
| `DATABASE_URL`                                       | PostgreSQL connection string (Alembic)                                                                       | **Yes**                               |
| `ENCRYPTION_KEY`                                     | Current Fernet key for organization provider credentials and OAuth token encryption                          | **Yes**                               |
| `ENCRYPTION_KEY_FALLBACKS`                           | Optional comma-separated previous Fernet keys during controlled rotation                                     | **Yes**                               |
| `STRIPE_SECRET_KEY`                                  | Stripe secret key                                                                                            | **Yes**                               |
| `STRIPE_WEBHOOK_SECRET`                              | Stripe webhook signing secret                                                                                | **Yes**                               |
| `TWILIO_ACCOUNT_SID`                                 | Twilio account SID                                                                                           | No                                    |
| `TWILIO_AUTH_TOKEN`                                  | Twilio auth token                                                                                            | **Yes**                               |
| `TWILIO_PHONE_NUMBER_SID`                            | Default Twilio phone number SID                                                                              | No                                    |
| `TWILIO_SMS_FROM_NUMBER`                             | Optional Twilio E.164 sender for platform-admin OAuth recovery alerts                                        | No                                    |
| `TWILIO_WEBHOOK_SIGNATURE_VALIDATION_ENABLED`        | Validate `X-Twilio-Signature` on voice callbacks; default `true`                                             | No                                    |
| `API_BASE_URL`                                       | Public backend URL used for Twilio voice and status callbacks                                                | **Yes for phone-number provisioning** |
| `PHONE_NUMBER_BILLING_CHECK_INTERVAL_HOURS`          | Deployment fallback cadence for rental billing checks; default `24`                                          | No                                    |
| `PHONE_NUMBER_BILLING_GRACE_PERIOD_DAYS`             | Deployment fallback grace period before unpaid release; default `7`                                          | No                                    |
| `PHONE_NUMBER_RELEASE_RETRY_INTERVAL_HOURS`          | Deployment fallback cadence for release-pending retries; default `24`                                        | No                                    |
| `VOICE_WS_PUBLIC_URL`                                | Browser WebSocket base — prod: `wss://voice.247ai.live`                                                      | No                                    |
| `VOICE_WS_TWILIO_URL`                                | Twilio Media Streams base — prod: `wss://voice.247ai.live`                                                   | No                                    |
| `VOICE_TRANSPORT`                                    | `pipecat` in production                                                                                      | No                                    |
| `JWT_SECRET_KEY`                                     | Voice session JWT (must match voice-ws)                                                                      | **Yes**                               |
| `RESEND_API_KEY`                                     | Resend email API key                                                                                         | **Yes**                               |
| `GOOGLE_OAUTH_TOOL_CLIENT_ID`                        | Google OAuth client ID (tools)                                                                               | No                                    |
| `GOOGLE_OAUTH_TOOL_CLIENT_SECRET`                    | Google OAuth client secret                                                                                   | **Yes**                               |
| `GOOGLE_OAUTH_TOOL_REDIRECT_URI`                     | Prod: `https://api.247ai.live/api/v1/tools/callback`                                                         | No                                    |
| `API_BASE_URL`                                       | Public backend origin for OAuth callbacks (e.g. `https://api.247ai.live`)                                    | No                                    |
| `APP_BASE_URL`                                       | Public frontend origin for post-OAuth redirect (e.g. `https://www.247ai.live`)                               | No                                    |
| `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID`            | Google OAuth client ID (backend redirect sign-in)                                                            | No                                    |
| `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET`        | Google OAuth client secret                                                                                   | **Yes**                               |
| `SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID`     | LinkedIn OAuth app client ID (backend redirect sign-in)                                                      | No                                    |
| `SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET` | LinkedIn OAuth app client secret                                                                             | **Yes**                               |
| `LINKEDIN_OAUTH_SCOPES`                              | Prod: `openid profile email`                                                                                 | No                                    |
| `CORS_ORIGINS`                                       | Prod: `["https://www.247ai.live"]`                                                                           | No                                    |
| `APP_BASE_URL`                                       | Prod: `https://www.247ai.live`                                                                               | No                                    |
| `ENVIRONMENT`                                        | `production`                                                                                                 | No                                    |
| `DEBUG`                                              | `false`                                                                                                      | No                                    |
| `MCP_ALLOW_LOCAL_URLS`                               | Keep `false` in production                                                                                   | No                                    |
| `TOKEN_REFRESH_*`                                    | OAuth refresh tuning; the lease must be at least 180 seconds and defaults to 180 (`.env.prod.example`)       | No                                    |
| `VOICE_RECORDING_ENABLED`                            | Platform safety gate for persisting mixed call audio; the agent-level recording setting must also be enabled | No                                    |
| `RECORDING_STORAGE_BACKEND`                          | `r2` for staging/production; `local` for local development                                                   | No                                    |
| `RECORDING_R2_ENDPOINT`                              | Shared account S3 endpoint: `https://<account-id>.r2.cloudflarestorage.com`                                  | No                                    |
| `RECORDING_R2_BUCKET`                                | Environment-specific private bucket name                                                                     | No                                    |
| `RECORDING_R2_ACCESS_KEY_ID`                         | Bucket-scoped R2 object read/write access key                                                                | Yes                                   |
| `RECORDING_R2_SECRET_ACCESS_KEY`                     | Bucket-scoped R2 object read/write secret                                                                    | Yes                                   |
| `RECORDING_R2_PRESIGN_TTL_SECONDS`                   | Reserved lifetime for optional direct playback; current playback streams through the backend                 | No                                    |
| `RECORDING_ENCRYPTION_MODE`                          | `provider_managed`                                                                                           | No                                    |
| `RECORDING_RETENTION_DAYS`                           | Recording retention window, default 90                                                                       | No                                    |

## Production observability

The application sends all three OTLP signals to the single authenticated
collector endpoint. Set these values in `.env.prod` only after the cloud
profile is provisioned. The GCP environment generator copies them to both
server runtimes and selects the service-specific name for each runtime.

| Variable                                            | Description                                                   | Secret? |
| --------------------------------------------------- | ------------------------------------------------------------- | ------- |
| `OTEL_ENABLED`                                      | `true` only for the provisioned production cloud profile      | No      |
| `OTEL_BACKEND_SERVICE_NAME`                         | Stable backend service identity, for example `247ai-backend`  | No      |
| `OTEL_VOICE_WS_SERVICE_NAME`                        | Stable voice runtime identity, for example `247ai-voice-ws`   | No      |
| `OTEL_SERVICE_VERSION`                              | Release SHA or other bounded release identifier               | No      |
| `OTEL_TRACES_SAMPLER_ARG`                           | Root trace sample ratio from `0.0` to `1.0`                   | No      |
| `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_ENDPOINT` | HTTPS collector paths `/v1/traces`, `/v1/metrics`, `/v1/logs` | No      |
| `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_PROTOCOL` | `http/protobuf`                                               | No      |
| `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_HEADERS`  | Basic auth for the collector service account                  | **Yes** |

Keep Grafana Cloud and Langfuse credentials in the private
`.env.observability` file on the collector host. They must never be sent to
Cloud Run, the voice VM, the browser, or committed to the repository. Local
and staging templates intentionally use `OTEL_ENABLED=false`; the isolated
worktree launcher enables its private local collector when needed.

---

## voice-ws (OCI VM)

| Variable                                                        | Description                                                                                                                    | Secret? |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------- |
| `SUPABASE_URL`                                                  | Same as backend                                                                                                                | No      |
| `SUPABASE_SERVICE_KEY`                                          | Same as backend                                                                                                                | **Yes** |
| `SUPABASE_ANON_KEY`                                             | Same as backend                                                                                                                | **Yes** |
| `JWT_SECRET_KEY`                                                | Must match backend                                                                                                             | **Yes** |
| `ENCRYPTION_KEY`                                                | Same current Fernet key as backend; required to decrypt organization credentials and OAuth connections                         | **Yes** |
| `ENCRYPTION_KEY_FALLBACKS`                                      | Same optional key-rotation fallbacks as backend                                                                                | **Yes** |
| `GEMINI_API_KEY`                                                | Gemini realtime fallback                                                                                                       | **Yes** |
| `DEEPGRAM_API_KEY`                                              | STT pipeline fallback                                                                                                          | **Yes** |
| `OPENAI_API_KEY`                                                | LLM pipeline fallback                                                                                                          | **Yes** |
| `CARTESIA_API_KEY`                                              | TTS pipeline fallback                                                                                                          | **Yes** |
| `CEREBRAS_API_KEY`                                              | LLM pipeline fallback                                                                                                          | **Yes** |
| `OPENROUTER_API_KEY`                                            | LLM gateway fallback                                                                                                           | **Yes** |
| `FISH_API_KEY`                                                  | TTS fallback                                                                                                                   | **Yes** |
| `AGENT_DEFAULT_TIMEZONE`                                        | IANA tz fallback for agent prompts                                                                                             | No      |
| `VOICE_RECORDING_ENABLED`                                       | Platform safety gate for persisting mixed call audio (`false` default); the agent-level recording setting must also be enabled | No      |
| `RECORDING_STORAGE_BACKEND`                                     | `local` or private Cloudflare `r2`                                                                                             | No      |
| `RECORDING_ENCRYPTION_MODE`                                     | `provider_managed` (customer-managed reserved)                                                                                 | No      |
| `RECORDING_R2_ENDPOINT` / `RECORDING_R2_BUCKET`                 | Environment-specific R2 object store                                                                                           | No      |
| `RECORDING_R2_ACCESS_KEY_ID` / `RECORDING_R2_SECRET_ACCESS_KEY` | Bucket-scoped R2 credentials                                                                                                   | Yes     |
| `RECORDING_R2_PRESIGN_TTL_SECONDS`                              | Reserved for optional direct playback; current playback streams through the backend                                            | No      |
| `RECORDING_RETENTION_DAYS`                                      | Recording retention window, default 90                                                                                         | No      |
| `TWILIO_ACCOUNT_SID`                                            | Optional — Media Streams hang-up                                                                                               | No      |
| `TWILIO_AUTH_TOKEN`                                             | Pairs with account SID                                                                                                         | **Yes** |
| `ENVIRONMENT`                                                   | `production`                                                                                                                   | No      |
| `DEBUG`                                                         | `false`                                                                                                                        | No      |

Per-org provider keys are stored encrypted in the database; env vars above are
**platform fallbacks**.

---

## Frontend (`frontend-247ai`)

`NEXT_PUBLIC_*` variables are baked into the Next.js bundle at **Docker build
time** via `gcp-deploy.sh` build args.

| Variable                             | Production value                                        | Secret? |
| ------------------------------------ | ------------------------------------------------------- | ------- |
| `NEXT_PUBLIC_API_URL`                | `https://api.247ai.live`                                | No      |
| `NEXT_PUBLIC_SUPABASE_URL`           | Supabase project URL                                    | No      |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`      | Supabase anon key                                       | **Yes** |
| `NEXT_PUBLIC_API_URL`                | Backend API URL used by frontend OAuth redirect buttons | No      |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key                                  | No      |
| `NEXT_PUBLIC_APP_NAME`               | App display name                                        | No      |
| `NEXT_PUBLIC_APP_DESCRIPTION`        | App tagline                                             | No      |
| `NODE_ENV`                           | `production`                                            | No      |

Browser voice calls receive `wsUrl` from the backend API — no separate public
WebSocket env var is required on the frontend.

---

## OCI SSH (not in `.env.prod`)

Set in the shell when deploying voice-ws:

| Variable       | Default               | Purpose                   |
| -------------- | --------------------- | ------------------------- |
| `OCI_SSH_HOST` | — (required)          | VM public IP              |
| `OCI_SSH_USER` | `ubuntu`              | SSH user                  |
| `OCI_SSH_KEY`  | `~/.ssh/oci_voice_ws` | Private key for VM access |

---

## Pre-deploy checklist

- [ ] `.env.prod` populated from `.env.prod.example`
- [ ] Supabase migrations applied: `./scripts/deploy.sh migrate`
- [ ] `JWT_SECRET_KEY` identical on backend and voice-ws
- [ ] `VOICE_WS_PUBLIC_URL` / `VOICE_WS_TWILIO_URL` point at production voice host
- [ ] R2 has two private buckets in the shared account: `247ai-call-recordings-staging` and `247ai-call-recordings-production`
- [ ] Staging and production each use separate bucket-scoped R2 object read/write credentials
- [ ] `VOICE_RECORDING_ENABLED=true`, `RECORDING_STORAGE_BACKEND=r2`, and the matching R2 endpoint/bucket/credentials are set in the selected environment file
- [ ] Production `.env.prod` has `OTEL_ENABLED=true` only after the authenticated cloud collector and Grafana Cloud/Langfuse projects are provisioned
- [ ] Production OTLP endpoints use HTTPS and all three signal headers are set; staging remains `OTEL_ENABLED=false`
- [ ] Grafana Cloud contact points and the observability alert thresholds have been tested for firing and recovery
- [ ] Stripe webhooks and OAuth redirect URIs use `https://api.247ai.live`
- [ ] Google Cloud redirect URI: `https://api.247ai.live/api/v1/auth/google/callback`
- [ ] LinkedIn Developer Portal redirect URI: `https://api.247ai.live/api/v1/auth/linkedin/callback`
- [ ] Backend has `SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID` and `_SECRET` from `.env.prod`
- [ ] All **Secret?=Yes** values stored in a team password manager

See [runbook.md](runbook.md) for full deployment steps.
