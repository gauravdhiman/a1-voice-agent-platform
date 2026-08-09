# CI / GitHub Actions deployment

Workflow: [`.github/workflows/deploy-cloud.yml`](../../../.github/workflows/deploy-cloud.yml)

Triggers on **push to `main`** (auto-deploy) and manual **`workflow_dispatch`**.

## Jobs

| Job | What it does |
|-----|----------------|
| `deploy-gcp` | Writes `.env.prod` from secret, runs `./scripts/deploy.sh gcp` |
| `deploy-voice-ws` | Runs `./scripts/deploy.sh voice-ws` on the OCI VM (after GCP job) |

## GitHub secrets (repository settings)

| Secret | Required | Notes |
|--------|----------|-------|
| `ENV_PROD` | Yes | Full contents of `.env.prod` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Yes | Workload Identity Federation provider |
| `GCP_SERVICE_ACCOUNT` | Yes | e.g. `github-deploy@....iam.gserviceaccount.com` |
| `OCI_SSH_KEY` | Yes (voice-ws) | Private SSH key PEM — must match VM `authorized_keys` |

If the repository previously used the secret name `ENV_CLOUD`, rename it to
`ENV_PROD` before running this workflow. The workflow now writes `.env.prod`.

## OCI VM connection (in workflow, not secrets)

These are set in the workflow file (public infrastructure):

| Variable | Value |
|----------|-------|
| `OCI_SSH_HOST` | `132.145.130.61` (`voice.247ai.live`) |
| `OCI_SSH_USER` | `ubuntu` |

The voice-ws job is **skipped** if `OCI_SSH_KEY` is empty.

### One-time: set `OCI_SSH_KEY` secret

From your machine (key must match the VM — default local path `~/.ssh/oci_voice_ws`):

```bash
gh secret set OCI_SSH_KEY < ~/.ssh/oci_voice_ws
```

Verify:

```bash
gh secret list   # shows OCI_SSH_KEY (values are hidden)
```

## Manual trigger

GitHub → **Actions** → **Deploy Cloud (main)** → **Run workflow**.

## Local vs CI

| Concern | Local | CI |
|---------|-------|-----|
| App credentials | `.env.prod` | `ENV_PROD` secret |
| GCP auth | `gcloud auth login` | Workload Identity |
| OCI VM host | `export OCI_SSH_HOST=132.145.130.61` or rely on workflow default | Hardcoded in workflow |
| OCI VM SSH key | `~/.ssh/oci_voice_ws` | `OCI_SSH_KEY` secret |

See also [Quick reference](quick-reference.md) and [Runbook](runbook.md).
