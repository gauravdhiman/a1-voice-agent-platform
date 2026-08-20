# CI / GitHub Actions deployment

The release path is split deliberately:

- [`.github/workflows/deploy-cloud.yml`](../../../.github/workflows/deploy-cloud.yml)
  runs on merges to `main` and deploys only to shared cloud staging.
- [`.github/workflows/promote-production.yml`](../../../.github/workflows/promote-production.yml)
  is manual-only and promotes the full commit SHA that has already passed
  staging.

There is no permanent `staging` Git branch. Pull requests merge into protected
`main`; `main` is the source for staging, and production is an explicit
promotion decision.

## Staging workflow

`deploy-cloud.yml` runs on a push to `main` or a manual dispatch. Its order is:

1. Materialize the protected `staging` environment's `ENV_STAGING` secret.
2. Run the read-only Alembic compatibility check.
3. Run `./scripts/deploy.sh migrate --env-file .env.staging`.
4. Verify the phone-number data migration.
5. Deploy the configured staging Cloud Run services.
6. Deploy staging voice-ws when its optional OCI host/key are configured.

The workflow uses a non-canceling concurrency group, so two pushes cannot run
staging migrations and deployments against the shared release database at the
same time. A later run waits for the earlier run to finish.

Cloud Run images are tagged with the checked-out commit SHA. The production
workflow uses the selected ref's SHA as its image tag, so the application image
is not selected through the mutable `latest` tag during CI promotion. The
current deploy script rebuilds that exact ref in the target registry; a future
cross-project artifact-copy step can promote a staging digest bit-for-bit if
the registries are separated.

If the database contains a revision not present in the checked-out migration
graph, the workflow stops before Alembic can mutate it. An empty or older
staging database is allowed and is upgraded normally.

### Staging environment secrets

Configure these under **Repository Settings → Environments → staging**:

| Secret | Required | Purpose |
| --- | --- | --- |
| `ENV_STAGING` | Yes | Complete `.env.staging` contents |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Yes | Google Workload Identity Federation provider |
| `GCP_SERVICE_ACCOUNT` | Yes | Service account allowed to deploy staging |
| `STAGING_OCI_SSH_KEY` | Optional | SSH key for a dedicated staging voice-ws VM |

Configure these as **staging environment variables**. They are required for
Cloud Run deployment so a missing value cannot silently fall back to a
production service name:

| Variable | Purpose |
| --- | --- |
| `STAGING_GCP_PROJECT_ID` | GCP project used by staging |
| `STAGING_GCP_REGION` | Cloud Run/Artifact Registry region |
| `STAGING_GCP_BACKEND_SERVICE` | Staging backend Cloud Run service |
| `STAGING_GCP_FRONTEND_SERVICE` | Staging frontend Cloud Run service |
| `STAGING_OCI_SSH_HOST` | Optional dedicated staging voice-ws host |
| `STAGING_OCI_SSH_USER` | Optional staging SSH user; defaults to `ubuntu` |

The staging service names must not be the production service names. If the
organization does not yet have a dedicated staging voice-ws VM, the workflow
skips that optional job; it does not deploy staging voice-ws to the production
VM.

## Manual production promotion

Run **Actions → Promote to production → Run workflow**, enter the full
40-character commit SHA that passed staging, and submit it. The workflow
validates the SHA before requesting the protected production environment. Do
not promote a branch or tag: even a well-named tag can be moved unless the
repository enforces immutable tags. It then:

1. Checks out that ref in the protected `production` environment.
2. Runs the same migration compatibility check and migration verification
   against production.
3. Deploys the checked-out ref to the production Cloud Run services.
4. Deploys the checked-out ref to the production voice-ws VM when configured.

Production promotion also has a non-canceling concurrency group, preventing
two manual approvals from racing production migrations or service updates.

Configure required reviewers on the GitHub `production` environment. Store
these there:

| Secret | Required | Purpose |
| --- | --- | --- |
| `ENV_PROD` | Yes | Complete `.env.prod` contents |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Yes | Google Workload Identity Federation provider |
| `GCP_SERVICE_ACCOUNT` | Yes | Production deployment service account |
| `OCI_SSH_KEY` | Optional | Production voice-ws VM private key |

Optional production environment variables can override the defaults used by the
deployment scripts: `PRODUCTION_GCP_PROJECT_ID`, `PRODUCTION_GCP_REGION`,
`PRODUCTION_GCP_BACKEND_SERVICE`, `PRODUCTION_GCP_FRONTEND_SERVICE`,
`PRODUCTION_OCI_SSH_HOST`, and `PRODUCTION_OCI_SSH_USER`.

Production migration is intentionally in the same protected workflow as the
application deployment. A migration failure prevents the application jobs from
running. The compatibility check is read-only and is not a replacement for
backups, rollback planning, or reviewing a migration's data-safety behavior.

## Local versus CI

| Concern | Local worktree | Shared staging CI | Production promotion |
| --- | --- | --- | --- |
| Application state | Dedicated Docker Compose project | Staging Cloud Run services | Production Cloud Run/OCI |
| Database | Dedicated local Supabase project | Cloud staging Supabase | Cloud production Supabase |
| Auth | Seeded email/password user | Staging accounts | Production accounts |
| Env source | Generated ignored `.worktree-state/app.env` | `ENV_STAGING` | `ENV_PROD` |
| Trigger | `scripts/worktree-stack.sh up` | Merge to `main` | Manual workflow dispatch |
| Approval | Developer | PR/release checks | Protected environment reviewers |

For local worktree setup see
[Worktree Isolation and Release Promotion Strategy](worktree-and-release-strategy.md).
For migration and smoke-test recovery see [the runbook](runbook.md).
