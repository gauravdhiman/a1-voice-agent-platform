# Deploy artifacts

Deployment scripts and configs for cloud environments. **Status: parked** on branch `deploy/branch-to-deploy` — steps 0–5 complete, steps 6–7 pending. See [DEPLOY_BRANCH_PARKED.md](../docs/05_operations/DEPLOY_BRANCH_PARKED.md).

## Layout

| Path | Description |
|------|-------------|
| `cloudbuild-backend.yaml` | Cloud Build stub for backend image (local Docker build used in practice) |
| `cloudbuild-frontend.yaml` | Cloud Build stub for frontend image |
| `oci/docker-compose.worker.yml` | LiveKit worker on a always-on VM (OCI, GCP e2-micro, or local) |

## Scripts (repo root)

| Script | Description |
|--------|-------------|
| `scripts/deploy/gcp-deploy.sh` | Deploy backend + frontend to GCP Cloud Run |
| `scripts/deploy/gcp-map-domains.sh` | Map custom domains to Cloud Run |
| `scripts/deploy/run-alembic-cloud.sh` | Run production DB migrations |
| `scripts/deploy/oci-deploy-worker.sh` | Deploy worker to OCI VM via SSH |

## Primary runbook

[docs/DEPLOY_GCP_OCI.md](../docs/DEPLOY_GCP_OCI.md)
