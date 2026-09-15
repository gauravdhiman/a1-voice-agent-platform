# Environment Configuration

This document explains how to configure environment variables for different development scenarios.

## Supabase projects

| Environment    | Project ref                   | Env file       | Notes                                                                        |
| -------------- | ----------------------------- | -------------- | ---------------------------------------------------------------------------- |
| **Local**      | Local CLI (`127.0.0.1:54321`) | `.env.local`   | Default dev; selected by `./start.sh start dev`                              |
| **Staging**    | `gdzwiwukcwbqohfwxxrx`        | `.env.staging` | Cloud DB for pre-prod validation — [staging guide](./staging_environment.md) |
| **Production** | `zymiyfilulmtrmyyhvzw`        | `.env.prod`    | 247ai.live — deploy/migrate only                                             |

> Do **not** use production Supabase for local feature testing. Use `.env.staging` instead.

## Environment Variable Files

The root files are the source of truth for Docker, direct backend commands, and
deployment:

1. `.env.local` — local Supabase and local application URLs.
2. `.env.staging` — cloud staging Supabase with the application still running locally.
3. `.env.prod` — production Supabase and production URLs; deployment defaults here.

Use `./start.sh start dev --env staging` to test staging. Do not copy any of
these files into `.env`. The service-specific `backend/.env` and
`frontend/.env.local` files are compatibility files for advanced
non-containerized workflows only; the supported development path is Docker.

## Design record: canonical environment-file model

**Status:** Adopted in August 2026

### Context

The project previously used a root `.env` as a mutable pointer to whichever
Supabase project was being tested. Switching between local and staging meant
copying one environment into `.env`, which made the active database ambiguous,
made container restarts easy to misconfigure, and left old `.env.*` files with
unclear ownership.

### Decisions

1. **Use exactly three canonical root runtime files.** `.env.local` selects the
   local Supabase instance, `.env.staging` selects cloud staging while the app
   still runs locally, and `.env.prod` selects the production Supabase project.
2. **Use `.env.prod`, not `.env.cloud`, for production.** The name describes the
   deployment lifecycle rather than the hosting provider and keeps the three
   environment names symmetrical.
3. **Select files at the command boundary.** `start.sh` defaults to `.env.local`
   for development and `.env.prod` for production mode. Use `--env staging`
   for staging or `--env-file PATH` for an explicit file. No file is copied into
   a root `.env` during normal operation.
4. **Keep Docker and direct processes on the same contract.** Compose receives
   the selected file through `--env-file` and the service `env_file` setting.
   Direct backend, worker, and Alembic commands use `ENV_FILE=...`.
5. **Keep shared provider credentials reusable for now.** Google, LinkedIn,
   Resend, Stripe, voice, and AI provider credentials are intentionally shared
   across environments until real production users require separate accounts.
   Database credentials, public URLs, runtime/debug settings, and telemetry
   endpoints remain environment-specific where the deployment requires it.
6. **Isolate Compose projects by environment.** The startup script uses
   `247ai-local`, `247ai-staging`, and `247ai-production` so changing the
   selected database cannot accidentally reuse containers from another
   environment.
7. **Keep real files private and templates complete.** The three runtime files
   are gitignored; the three `.example` files are committed documentation and
   must contain placeholders only. Their key sets are kept identical and are
   checked by `scripts/tests/test_environment_contract.sh`.
8. **Use `.env.prod` consistently in deployment automation.** The deploy script,
   production Compose file, migration helpers, GitHub Actions workflow, and
   deployment docs all use `.env.prod`. CI stores its contents in the
   `ENV_PROD` production-environment secret. The production PostHog project key
   is a separate protected secret injected into the frontend build.
9. **Keep worktree provider settings synchronized.** The full isolated
   worktree launcher reads non-placeholder voice-provider credentials from the
   worktree `.env.local` or the main checkout `.env.local`, refreshes them into
   `.worktree-state/app.env` on every setup, and fails fast when
   `GEMINI_API_KEY` is not configured.

Deployment helper names that contain `cloud` (for example,
`gcp-env-from-cloud.py` or `deploy-cloud.yml`) describe the cloud hosting
target, not a fourth environment file. They consume the selected
`.env.prod`/`ENV_FILE` contract.

### Operational consequences

- Start local development with `./start.sh start dev`.
- Test cloud staging locally with `./start.sh start dev --env staging`.
- Inspect the selected file and non-secret Supabase URL with
  `./start.sh config --env NAME`.
- Deploy with `./scripts/deploy.sh`, which defaults to `.env.prod`; use
  `--env-file PATH` only for an explicit override.
- Do not use `.env.prod` for local feature testing. Use `.env.staging` instead.
- If the repository still has a GitHub secret named `ENV_CLOUD`, rename it to
  `ENV_PROD` before running the deployment workflow.

### Environment selection commands

| Task                          | Command                                                               | Selected file  |
| ----------------------------- | --------------------------------------------------------------------- | -------------- |
| Local Docker development      | `./start.sh start dev`                                                | `.env.local`   |
| Cloud staging validation      | `./start.sh start dev --env staging`                                  | `.env.staging` |
| Production-like local Compose | `./start.sh start prod`                                               | `.env.prod`    |
| Safe selection check          | `./start.sh config --env staging`                                     | `.env.staging` |
| Direct backend process        | `ENV_FILE=.env.staging python backend/main.py`                        | `.env.staging` |
| Alembic migration             | `ENV_FILE=.env.staging REVISION=head ./scripts/deploy/run-alembic.sh` | `.env.staging` |
| Production deployment         | `./scripts/deploy.sh`                                                 | `.env.prod`    |

## PostHog Analytics

PostHog is optional frontend analytics. Set `NEXT_PUBLIC_POSTHOG_KEY` to the
project token and `NEXT_PUBLIC_POSTHOG_HOST` to the matching ingestion host
(US Cloud: `https://us.i.posthog.com`). An empty key disables capture. The key
is intended for browser use and is included in the built frontend.

The root `.env.local.example`, `.env.staging.example`, and `.env.prod.example`
templates contain both variables; the advanced standalone frontend template
`frontend/.env.local.example` does too. Use a separate PostHog project for
local or staging events, or leave those keys empty, so non-production activity
does not mix with production analytics.

For a direct production build, set both variables in `.env.prod`. The protected
production workflow injects `NEXT_PUBLIC_POSTHOG_KEY` from its matching GitHub
environment secret and uses the US Cloud host. Next.js embeds `NEXT_PUBLIC_`
values into its client bundle at build time, so changing the production
environment after the image is built requires rebuilding and redeploying it.
The Docker Compose and GCP deployment paths pass both values into that build.

`docker compose -f docker-compose.dev.yml` defaults to `.env.local`, while
`docker compose -f docker-compose.yml` defaults to `.env.prod`. The `start.sh`
workflow is preferred because it validates the file, passes it explicitly, and
selects an isolated Compose project name.

Run the environment contract checks after changing templates, startup defaults,
or deployment references:

```bash
bash scripts/tests/test_environment_contract.sh
bash scripts/tests/test_environment_selection.sh
```

## Supabase Configuration

### Required Keys

The Supabase configuration requires different environment variables for frontend and backend:

1. **SUPABASE_SERVICE_KEY**: Used only by the backend for administrative operations (service role key)
2. **SUPABASE_ANON_KEY**: Used by the backend for certain operations (anon key)
3. **NEXT_PUBLIC_SUPABASE_URL**: Used by the frontend (must be prefixed with NEXT*PUBLIC* to be accessible in browser)
4. **NEXT_PUBLIC_SUPABASE_ANON_KEY**: Used by the frontend (must be prefixed with NEXT*PUBLIC* to be accessible in browser)
5. **API_BASE_URL** / **APP_BASE_URL**: Backend OAuth redirect targets (see
   [Backend redirect OAuth](../02_features/authentication_rbac/backend-redirect-oauth.md))

For local backend redirect OAuth, add these to the selected root file (normally
`.env.local`):

```bash
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000

SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID=...
SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET=...

SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID=...
SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_SECRET=...
LINKEDIN_OAUTH_SCOPES=openid profile email

JWT_SECRET_KEY=...
```

Register **backend** callback URLs in Google Cloud and LinkedIn Developer Portal:

```text
{API_BASE_URL}/api/v1/auth/google/callback
{API_BASE_URL}/api/v1/auth/linkedin/callback
```

See [Social OAuth architecture](../02_features/authentication_rbac/social-oauth-architecture.md)
and [Backend redirect OAuth](../02_features/authentication_rbac/backend-redirect-oauth.md).

### Getting Your Supabase Database Password

To configure the DATABASE_URL environment variable for Alembic migrations, you'll need your Supabase database password:

1. Go to your Supabase project dashboard
2. Navigate to "Settings" → "Database"
3. Under "Connection Info", you'll see:
   - **Host**: Your project reference followed by `.supabase.co`
   - **Port**: 5432
   - **User**: postgres
   - **Password**: This is your database password (different from your Supabase project password)
4. Use this information to construct your DATABASE_URL:
   ```
   postgresql://postgres:[DATABASE-PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres
   ```

### OAuth Providers

For hosted Supabase, enable Google under Authentication → Providers and enter
the Web Client ID and Client Secret there. For local Supabase, the Google
provider is enabled in `supabase/config.toml`:

```toml
[auth.external.google]
enabled = true
client_id = "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID)"
secret = "env(SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET)"
skip_nonce_check = false
```

If you also retain redirect-based OAuth providers, you additionally need to:

1. Configure the OAuth provider in your Supabase project dashboard:

   - Go to Authentication → Providers
   - Enable the desired provider (e.g., Google)
   - Configure the provider settings with your OAuth credentials

2. Set the redirect URLs in your OAuth provider's dashboard:
   - Use the Supabase callback URL: `https://YOUR_SUPABASE_PROJECT_ID.supabase.co/auth/v1/callback`
   - You can find this URL in your Supabase dashboard under Authentication → Settings

For backend redirect OAuth (Google and LinkedIn), the backend mints Supabase
sessions via the admin API. Provider credentials live in the selected root
environment file; the
frontend only needs `NEXT_PUBLIC_API_URL` to build authorize links.

Local Supabase can keep Google/LinkedIn providers enabled in `supabase/config.toml`
for compatibility. Restart local Supabase after changing provider credentials:

```bash
supabase stop
supabase start
```

See [Backend redirect OAuth](../02_features/authentication_rbac/backend-redirect-oauth.md)
for redirect URIs and the handoff flow.

## OpenTelemetry Configuration

OpenTelemetry is configured as a process-scoped, content-free export boundary.
See the [observability operator guide](observability.md) for signal definitions,
privacy rules, local verification, and the production rollout.

- `.env.local.example` and `.env.staging.example` keep `OTEL_ENABLED=false`.
- `scripts/worktree-stack.sh` opts an isolated worktree into its private local
  collector when trace inspection is needed.
- `.env.prod.example` remains disabled until the authenticated cloud collector,
  Grafana Cloud project and Langfuse project are provisioned.
- Production uses `http/protobuf` over HTTPS for traces, metrics and logs, with
  a separate Basic auth header for each signal. The GCP environment generator
  copies the values to backend and voice-ws and assigns distinct service names.
- The frontend stays disabled. Its API client propagates a W3C `traceparent` and
  exposes the server-generated request ID for support correlation; no browser
  collector credential is shipped.

Only bounded identifiers, operation outcomes, provider/model metadata, timing,
token counts and tool status are exported. Prompts, completions, transcripts,
audio, tool arguments/results and credentials are excluded.

## Direct service development (advanced)

The supported Docker workflow uses the root canonical files described above.
For a non-containerized process, select the same root file explicitly with
`ENV_FILE=.env.local` or `ENV_FILE=.env.staging`; do not create a root `.env`.

The nested `frontend/.env.local` and `backend/.env` compatibility files exist
only for service-local tooling that cannot read the root file. They are not
environment selectors and must not be used to switch databases. Keep their
public values aligned with the selected root file when using that advanced
workflow.

## Docker Configuration

The project includes optimized Docker configurations:

- **Production**: Multi-stage build with minimal image size
- **Development**: Volume mounting for hot reloading
- **Standalone**: Next.js standalone output for optimal Docker performance

Both [docker-compose.yml](../../docker-compose.yml) and [docker-compose.dev.yml](../../docker-compose.dev.yml) use the `env_file` directive with the selected root file. `start.sh` passes the selection explicitly; direct Compose commands default to `.env.prod` for production Compose and `.env.local` for development Compose.

## Next Steps

1. Copy the appropriate example file to create `.env.local`, `.env.staging`, or `.env.prod`
2. Update the values with your actual configuration
3. For OAuth providers, configure them in your Supabase dashboard
4. For database migrations, get your Supabase database password and update the DATABASE_URL
5. For detailed OAuth setup instructions, see [OAUTH_SETUP.md](OAUTH_SETUP.md)
6. For OpenTelemetry setup, follow the [observability operator guide](observability.md); local and staging remain disabled by default
