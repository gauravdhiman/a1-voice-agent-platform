# Deploy artifacts

Deployment scripts and configs for the **247ai.live** production stack:
backend + frontend on GCP Cloud Run, voice-ws (Pipecat WebSocket) on an Oracle
Free Tier ARM VM behind Caddy, Supabase DB.

**Documentation:** [docs/05_operations/deployment/](../docs/05_operations/deployment/README.md)

## Single deploy command

```bash
./scripts/deploy.sh [all|gcp|backend|frontend|voice-ws|migrate|domains]
```

Local/manual credentials may be read from **`.env.prod`** (gitignored), but
cloud releases use the version-controlled files under **`deploy/config/`** for
non-secret configuration and GCP Secret Manager / OCI Vault for private values.
The checked-in config is the release source of truth; `.env.prod` is only a
generated or emergency local runtime file. Templates: **`.env.prod.example`**
and `deploy/config/production.env`.

## Layout

| Path | Description |
|------|-------------|
| `cloudbuild-backend.yaml` | Cloud Build stub for the backend image |
| `cloudbuild-frontend.yaml` | Cloud Build stub for the frontend image |
| `oci/docker-compose.voice-ws.yml` | voice-ws + Caddy on the OCI VM |
| `oci/Caddyfile` | TLS reverse proxy for `voice.247ai.live` |
| `config/local.env` | Versioned local non-secret configuration |
| `config/staging.env` | Versioned staging deployment configuration |
| `config/production.env` | Versioned production non-secret configuration |
| `config/secrets.example` | Empty-key template for an ignored local secret overlay |

## Scripts

| Script | Description |
|--------|-------------|
| **`scripts/deploy.sh`** | Single entry point for all production deploys |
| `scripts/deploy/build-env-file.py` | Build a private runtime env file from versioned config + ignored secret overlay |
| `scripts/deploy/validate-versioned-config.py` | Reject secret values and placeholders in versioned cloud config |
| `.env.prod.example` | Production env template (copy → `.env.prod`) |
| `scripts/deploy/gcp-deploy.sh` | Migration-gated build + deploy of backend and/or frontend |
| `scripts/deploy/gcp-map-domains.sh` | Map `api`, canonical `www`, and apex domains to Cloud Run |
| `scripts/deploy/run-alembic-cloud.sh` | Compatibility-gated Alembic migrations + PostgREST schema reload |
| `scripts/deploy/oci-deploy-voice-ws.sh` | Migration-gated sync + build of voice-ws on OCI VM |
| `scripts/deploy/gcp-env-from-cloud.py` | Filter/render non-secret service config and OCI secret manifests |
| `scripts/deploy/render-gcp-env.py` | Materialize a short-lived migration env from GCP Secret Manager |
| `scripts/deploy/sync-gcp-secrets.py` | Preview or explicitly import versions into GCP Secret Manager |
| `scripts/deploy/sync-oci-secrets.py` | Preview or explicitly import voice-ws versions into OCI Vault |
| `scripts/deploy/oci-fetch-vault-env.sh` | Resolve OCI Vault secrets with VM instance principals |
| `scripts/deploy/verify_org_credential_migration.py` | Read-only postcondition check for credential hardening |
| `scripts/deploy/rotate-encrypted-data.py` | Dry-run or guarded K1-to-K2 re-encryption of application ciphertext |
| `scripts/deploy/rotate-legacy-encrypted-data.py` | One-time guarded rotation for ciphertext created by the removed development fallback |

## Related docs

- [Deployment index](../docs/05_operations/deployment/README.md)
- [Quick reference](../docs/05_operations/deployment/quick-reference.md)
- [Runbook](../docs/05_operations/deployment/runbook.md)
- [Environment variables](../docs/05_operations/deployment/environment-variables.md)
