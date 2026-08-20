# Deployment documentation

Production infrastructure for **247ai.live**:

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend (`frontend-247ai`) | GCP Cloud Run | https://www.247ai.live |
| Backend (`backend-247ai`) | GCP Cloud Run | https://api.247ai.live |
| voice-ws (Pipecat WebSocket) | Oracle Free Tier ARM VM + Caddy | wss://voice.247ai.live |
| Database + Auth | Supabase | Production: `.env.prod` (`zymiyfilulmtrmyyhvzw`); staging: `.env.staging` (`gdzwiwukcwbqohfwxxrx`) |

**Deploy command:** `./scripts/deploy.sh` — see [Quick reference](quick-reference.md).

## Documentation map

| Document | When to read it |
|----------|-----------------|
| **[Quick reference](quick-reference.md)** | Day-to-day deploy commands, prerequisites, smoke checks |
| **[Runbook](runbook.md)** | Full architecture, first-time setup, DNS, webhooks, security |
| **[Environment variables](environment-variables.md)** | Every env var by service; `.env.prod` is the manual-deploy file and `ENV_PROD` is its CI equivalent |
| **[Local Docker](local-docker.md)** | docker-compose and manual image builds for development |
| **[CI / GitHub Actions](ci-github-actions.md)** | Staging auto-deploy, manual production promotion, and required secrets |
| **[Worktree isolation and release strategy](worktree-and-release-strategy.md)** | Per-worktree databases, shared staging, and production promotion model |

## Repo artifacts

| Path | Purpose |
|------|---------|
| `scripts/deploy.sh` | Single entry point: `all`, `gcp`, `backend`, `frontend`, `voice-ws`, `migrate`, `domains` |
| `.env.prod.example` | Production env template (copy → `.env.prod`, gitignored) |
| `.env.staging.example` | Staging env template (copy → `.env.staging`, gitignored) |
| `scripts/bootstrap-staging-db.sh` | Legacy/repair staging migrate + Stripe seed |
| `scripts/deploy/` | Lower-level GCP, OCI, Alembic scripts |
| `deploy/` | Docker compose, Caddyfile, Cloud Build stubs |
| `scripts/worktree-stack.sh` | Full isolated local Supabase + application stack per worktree |
| `.github/workflows/deploy-cloud.yml` | CI deploy to staging on `main` |
| `.github/workflows/promote-production.yml` | Manual protected production promotion |

## Credentials

- **Application secrets:** `.env.prod` for emergency/local deployment, or the protected GitHub `production` environment secret `ENV_PROD` for CI (never commit the file).
- **OCI VM SSH:** `~/.ssh/oci_voice_ws` (default). Set `OCI_SSH_HOST` when deploying voice-ws.
- **OCI API / GCP:** local CLI config; CI uses GitHub secrets — see [CI](ci-github-actions.md).

## Related docs outside this folder

- [Voice-ws architecture (ADR)](../../01_architecture/ADR_VOICE_WS_PIPECAT.md)
- [Environment configuration notes](../environment_configuration.md) — local dev and general config
- [Stripe management](../stripe_management.md)
- [deploy/README.md](../../../deploy/README.md) — script and artifact index
