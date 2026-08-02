# Cloud deployment (GCP Cloud Run + OCI worker)

> **Branch status (2026-08-02):** Work on this LiveKit-based deploy path is **parked** on `deploy/branch-to-deploy`. Steps **0–5 complete** (through DB migrations); **steps 6–7 pending** (worker + webhooks). Full context: **[DEPLOY_BRANCH_PARKED.md](05_operations/DEPLOY_BRANCH_PARKED.md)**.

Production URLs (target):

| Service | Domain |
|---------|--------|
| Frontend | https://ai-studio.cognients.com |
| Backend API | https://ai-studio-api.cognients.com |

Env file: **`.env.cloud`** (never commit; copy to GitHub secret `ENV_CLOUD`).

## One-time: deploy from your machine

```bash
# GCP (backend + frontend)
./scripts/deploy/gcp-deploy.sh

# OCI worker (after VM exists and Docker installed)
./scripts/deploy/oci-deploy-worker.sh
```

## Live URLs (before custom DNS)

After `./scripts/deploy/gcp-deploy.sh`:

- Backend: `gcloud run services describe cognients-backend --region us-central1 --format='value(status.url)'`
- Frontend: `gcloud run services describe cognients-frontend --region us-central1 --format='value(status.url)'`

**Currently deployed (2026-08-02):**

- Backend: https://cognients-backend-lrn7jnolsa-uc.a.run.app (also https://ai-studio-api.cognients.com)
- Frontend: https://cognients-frontend-lrn7jnolsa-uc.a.run.app (also https://ai-studio.cognients.com)

## Custom domains (Cloudflare + GCP)

1. Verify domain in Google Cloud: `gcloud domains verify cognients.com` *(done for cognients.com)*
2. Add the TXT record Cloudflare shows you.
3. Map domains:
   ```bash
   ./scripts/deploy/gcp-map-domains.sh
   ```
4. Add the CNAME records from `gcloud beta run domain-mappings describe` in Cloudflare DNS.

## GitHub Actions (auto-deploy on `main`)

Add repository secrets:

| Secret | Value |
|--------|--------|
| `ENV_CLOUD` | Full contents of `.env.cloud` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | e.g. `github-deploy@....iam.gserviceaccount.com` |
| `OCI_SSH_HOST` | OCI VM public IP (optional) |
| `OCI_SSH_USER` | e.g. `ubuntu` |
| `OCI_SSH_KEY` | Private SSH key PEM |

Workflow: `.github/workflows/deploy-cloud.yml`

## OCI CLI auth (local)

```bash
oci session authenticate --region us-ashburn-1
source scripts/oci-env.sh
oci iam region list
```

## Database migrations

**Status: completed (step 5).** Re-run only if new migrations land on the branch:

```bash
./scripts/deploy/run-alembic-cloud.sh
```

Verify current revision:

```bash
cd backend
export DATABASE_URL='...from .env.cloud...'
export PYTHONPATH=..
alembic current
```

## Worker (step 6 — not deployed)

**Blocked:** OCI A1 Flex VM out of capacity. See [DEPLOY_BRANCH_PARKED.md — Step 6](05_operations/DEPLOY_BRANCH_PARKED.md#step-6--livekit-worker-p0--required-for-voice-calls) and [Worker deployment options](05_operations/DEPLOY_BRANCH_PARKED.md#worker-deployment-options).

## Post-deploy webhooks (step 7 — not done)

Update vendor dashboards to use production URLs:

- Stripe → `https://ai-studio-api.cognients.com/billing/webhook`
- Twilio voice → `https://ai-studio-api.cognients.com/api/v1/voice/twilio/incoming`
- Google OAuth tools → `https://ai-studio-api.cognients.com/api/v1/tools/callback`
- Supabase Auth → Site URL `https://ai-studio.cognients.com`

## Deploy folder index

See [deploy/README.md](../deploy/README.md) for script and artifact layout.
