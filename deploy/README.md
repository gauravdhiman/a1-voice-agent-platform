# Deploy artifacts

Deployment scripts and configs for the **247ai.live** production stack:
backend + frontend on GCP Cloud Run, voice-ws (Pipecat WebSocket) on an Oracle
Free Tier ARM VM behind Caddy, Supabase DB.

**Documentation:** [docs/05_operations/deployment/](../docs/05_operations/deployment/README.md)

## Single deploy command

```bash
./scripts/deploy.sh [all|gcp|backend|frontend|voice-ws|migrate|domains]
```

Credentials: **`.env.prod`** only (gitignored). Template: **`.env.prod.example`**.

## Layout

| Path | Description |
|------|-------------|
| `cloudbuild-backend.yaml` | Cloud Build stub for the backend image |
| `cloudbuild-frontend.yaml` | Cloud Build stub for the frontend image |
| `oci/docker-compose.voice-ws.yml` | voice-ws + Caddy on the OCI VM |
| `oci/Caddyfile` | TLS reverse proxy for `voice.247ai.live` |

## Scripts

| Script | Description |
|--------|-------------|
| **`scripts/deploy.sh`** | Single entry point for all production deploys |
| `.env.prod.example` | Production env template (copy → `.env.prod`) |
| `scripts/deploy/gcp-deploy.sh` | Migration-gated build + deploy of backend and/or frontend |
| `scripts/deploy/gcp-map-domains.sh` | Map `api`, canonical `www`, and apex domains to Cloud Run |
| `scripts/deploy/run-alembic-cloud.sh` | Compatibility-gated Alembic migrations + PostgREST schema reload |
| `scripts/deploy/oci-deploy-voice-ws.sh` | Migration-gated sync + build of voice-ws on OCI VM |
| `scripts/deploy/gcp-env-from-cloud.py` | Filter `.env.prod` per service |
| `scripts/deploy/rotate-legacy-encrypted-data.py` | One-time guarded rotation for ciphertext created by the removed development fallback |

## Related docs

- [Deployment index](../docs/05_operations/deployment/README.md)
- [Quick reference](../docs/05_operations/deployment/quick-reference.md)
- [Runbook](../docs/05_operations/deployment/runbook.md)
- [Environment variables](../docs/05_operations/deployment/environment-variables.md)
