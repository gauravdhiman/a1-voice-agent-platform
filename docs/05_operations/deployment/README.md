# Deployment documentation

For the separate scheduled worker and its cutover safeguards, see
[maintenance service](maintenance-service.md).

Production infrastructure for **247ai.live**:

| Component                    | Platform                                                | URL                                                                                                |
| ---------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Frontend (`frontend-247ai`)  | GCP Cloud Run                                           | https://www.247ai.live                                                                             |
| Apex web alias               | Cloudflare edge redirect → canonical Cloud Run frontend | https://247ai.live                                                                                 |
| Backend (`backend-247ai`)    | GCP Cloud Run                                           | https://api.247ai.live                                                                             |
| voice-ws (Pipecat WebSocket) | Oracle Free Tier ARM VM + Caddy                         | wss://voice.247ai.live                                                                             |
| Database + Auth              | Supabase                                                | Production: `.env.prod` (`zymiyfilulmtrmyyhvzw`); staging: `.env.staging` (`gdzwiwukcwbqohfwxxrx`) |

**Deploy command:** `./scripts/deploy.sh` — see [Quick reference](quick-reference.md).

## Documentation map

| Document                                                                        | When to read it                                                                                     |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **[Quick reference](quick-reference.md)**                                       | Day-to-day deploy commands, prerequisites, smoke checks                                             |
| **[Runbook](runbook.md)**                                                       | Full architecture, first-time setup, DNS, webhooks, security                                        |
| **[Environment variables](environment-variables.md)**                           | Every env var by service and the non-secret deployment config contract                         |
| **[Local Docker](local-docker.md)**                                             | docker-compose and manual image builds for development                                              |
| **[CI / GitHub Actions](ci-github-actions.md)**                                 | Local staging validation, manual production promotion, and required secrets                         |
| **[Secret management](secret-management.md)**                                   | GCP Secret Manager, OCI Vault, GitHub OIDC, rotation, and credential migration                       |
| **[Current production secret map](production-secret-map.md)**                   | High-level ownership of secrets, runtime/deployment boundaries, and soft-production launch status   |
| **[Worktree isolation and release strategy](worktree-and-release-strategy.md)** | Per-worktree databases, local staging (shared cloud DB), and production promotion model             |

## Repo artifacts

| `scripts/deploy.sh` | Single entry point: `all`, `gcp`, `backend`, `frontend`, `voice-ws`, `migrate`, `domains` |
| `.env.prod.example` | Production env template (copy → `.env.prod`, gitignored) |
| `.env.staging.example` | Staging env template — local app + cloud DB (copy → `.env.staging`, gitignored) |
| `scripts/validate-staging.sh` | Local staging validator (migrate + release-data sync + `start.sh --env staging` + health checks) |
| `scripts/deploy/sync-release-fixtures.sh` | Explicit release bootstrap for system-pricing meters, native tools, and the three public demo agents; preserves existing usage rates |
| `scripts/bootstrap-staging-db.sh` | Legacy/repair staging migrations + approved credit-pack sync |
| `scripts/deploy/` | Lower-level GCP, OCI, Alembic scripts |
| `deploy/` | Docker compose, Caddyfile, Cloud Build stubs |
| `scripts/worktree-stack.sh` | Full isolated local Supabase + application stack per worktree |
| `.github/workflows/deploy-cloud.yml` | Manual staging recovery only (no longer auto on `main`) |
| `.github/workflows/promote-production.yml` | Manual protected production promotion |

Observability is a separate production service boundary. The application
exports to one authenticated OTLP endpoint; the minimal cloud profile runs
only Caddy and the OpenTelemetry Collector, while Grafana Cloud and Langfuse
Cloud provide hosted storage and exploration. Staging and regular local
examples keep telemetry disabled; the isolated worktree launcher enables its
private local stack when a developer needs to inspect a call.

| `docker-compose.observability.cloud.yml` | Minimal production collector + HTTPS ingress |
| `deploy/observability/collector.cloud.yml` | Grafana Cloud metrics/logs/traces plus content-free Langfuse trace fan-out |
| `deploy/observability/Caddyfile.cloud` | Authenticated OTLP paths and TLS ingress |
| `deploy/observability/alerts.cloud.yml` | Grafana Cloud-compatible application alert rules |
| `deploy/observability/grafana/dashboards/platform-cloud-import.json` | Grafana Cloud dashboard import with datasource selectors |

## Credentials

- **Application secrets:** GCP Secret Manager for Cloud Run and OCI Vault for
  voice-ws. `.env.prod` is a gitignored emergency/local deployment input only;
  never commit it.
- **Current ownership map:** read [Current production secret map](production-secret-map.md)
  first when you need to understand where a value lives. Cloud Run reads with
  its runtime service account, voice-ws reads through the OCI VM instance
  principal, and the GitHub deployment identity is separate from both.
- **Versioned release config:** `deploy/config/production.env` and
  `deploy/config/staging.env` contain non-secret values only. GitHub stores
  deployment identities and transport credentials, authenticates to GCP with
  OIDC/WIF, and does not store a complete production env file.
- **OCI VM SSH:** `~/.ssh/oci_voice_ws` (default). Set `OCI_SSH_HOST` when deploying voice-ws.
- **OCI API / GCP:** the VM uses OCI instance principals and CI uses GitHub
  OIDC/WIF — see [CI](ci-github-actions.md) and [Secret management](secret-management.md).

## Related docs outside this folder

- [Voice-ws architecture (ADR)](../../01_architecture/ADR_VOICE_WS_PIPECAT.md)
- [Environment configuration notes](../environment_configuration.md) — local dev and general config
- [Stripe management](../stripe_management.md)
- [deploy/README.md](../../../deploy/README.md) — script and artifact index

## Observability release gate

Follow [Operating observability](../observability.md#production-deployment) to
provision the single production Grafana Cloud and Langfuse Cloud projects,
configure authenticated collector ingress, set unique service/release
attributes, and create owned Grafana Cloud alert routes. Verify traces, logs,
metrics, dashboard queries and alert receipt alongside browser/PSTN release checks.

See the [October 19 remediation release guide](../production-readiness-remediation-2026-10-19.md) before customer launch. It separates prepared code from applied production changes and account-level acceptance gates.
