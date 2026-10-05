# CI / GitHub Actions deployment

The release path is split deliberately:

- **Staging** is validated **locally**: local Docker (frontend, backend, voice-ws)
  - cloud staging Supabase via `./start.sh start dev --env staging` and
    `./scripts/validate-staging.sh`. There is no automatic Cloud Run staging
    deployment on merge to `main`.
- [`.github/workflows/deploy-cloud.yml`](../../../.github/workflows/deploy-cloud.yml)
  is retained for **manual recovery only** (`workflow_dispatch`). It can still
  migrate staging and optionally deploy to Cloud Run, but it no longer runs
  on `push` to `main`.
- [`.github/workflows/promote-production.yml`](../../../.github/workflows/promote-production.yml)
  is manual-only and promotes the full commit SHA that has already passed
  **local** staging validation.

There is no permanent `staging` Git branch. Pull requests merge into protected
`main`; `main` is the source for staging, and production is an explicit
promotion decision.

## Staging validation (local)

Staging uses the **local application + cloud database** model:

```bash
# one-time: copy template and fill in staging Supabase keys
cp .env.staging.example .env.staging   # set SUPABASE_SERVICE_KEY, DATABASE_URL, etc.

# after every merge to main (or any release candidate):
./scripts/validate-staging.sh  # synchronizes usage meters, tools + public demos, then starts the app
# equivalent manual steps:
python3 scripts/deploy/check_alembic_compatibility.py --env-file .env.staging
./scripts/deploy.sh migrate --env-file .env.staging
python3 scripts/deploy/verify_phone_number_backfill.py --env-file .env.staging
# If using --migrate-only above, rerun the full validator before app startup.
```

Then run the mandatory browser + PSTN smoke tests against `http://localhost:3000`
with a release-test org that has active voice entitlements and prepaid credit
headroom. See `docs/05_operations/staging_environment.md` and
`docs/05_operations/deployment/runbook.md#mandatory-release-gate-ai-agent-calling`.

Why local? Worktree isolation (`scripts/worktree-stack.sh`) already gives each
worktree a dedicated local Supabase for concurrent feature work. The shared
staging Supabase is **not** isolated — Compose project names and port offsets
isolate containers but not a remote database. Validating staging locally
avoids adding a second cloud environment while still exercising the real
staging database and the full voice stack.

If the database contains a revision not present in the checked-out migration
graph, the compatibility check stops before Alembic can mutate it. The
repository must also have exactly one Alembic head; branch migrations must be
merged before release validation. An empty or older staging database is
allowed and is upgraded normally. The direct `start.sh` path runs the same
idempotent upgrade inside the backend container and refuses to start if it
fails.

The `Migration graph` workflow also runs on pull requests and checks the
repository without a database. This catches parallel-worktree migration
branches at integration time. If it reports multiple heads, add and review an
Alembic merge revision on the integration branch before merging or releasing.

## Staging workflow (GitHub Actions — manual recovery only)

The independent `Observability contracts` workflow runs on pull requests and
main. It enforces at least 90% statement coverage and 90% branch coverage for the new
telemetry modules and validates alert firing/recovery using pinned Prometheus.
It does not deploy monitoring or send notifications. See the
[observability guide](../observability.md#validation-commands) for full local
suite and live ingestion checks.

`deploy-cloud.yml` now runs **only** on manual dispatch. When dispatched it:

1. Validates the version-controlled `deploy/config/staging.env` file and
   renders secret values from GCP Secret Manager.
2. Runs the read-only Alembic compatibility check.
3. Runs `./scripts/deploy.sh migrate --env-file .env.staging`; the GCP deployer
   repeats this idempotent gate before publishing Cloud Run. The managed OCI
   job passes an explicit skip only after this migration job succeeds; a
   manual/local voice-ws deployment runs its own gate.
4. The GCP deployment's migration-gated bootstrap synchronizes code-owned
   native tools and the three public demo agents before publishing images.
5. Verifies the phone-number data migration.
6. Optionally deploys configured staging Cloud Run services (if staging GCP vars are set).
7. Optionally deploys staging voice-ws (if `STAGING_OCI_SSH_HOST`/`STAGING_OCI_SSH_KEY` are set).

It retains a non-canceling concurrency group so concurrent manual runs cannot
race staging migrations. Cloud Run images are tagged with the commit SHA.

### Staging environment secrets (only needed for manual Cloud Run recovery)

Configure these under **Repository Settings → Environments → staging** if you
use the manual Cloud Run path:

| Secret                           | Required              | Purpose                                      |
| -------------------------------- | --------------------- | -------------------------------------------- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Only for Cloud Run    | Google Workload Identity Federation provider |
| `GCP_SERVICE_ACCOUNT`            | Only for Cloud Run    | WIF service account allowed to deploy and read managed secrets |
| `STAGING_OCI_SSH_KEY`            | Optional              | SSH key for a dedicated staging voice-ws VM  |

Configure these as **staging environment variables** only if deploying to
Cloud Run:

| Variable                       | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `STAGING_GCP_PROJECT_ID`       | GCP project used by staging                     |
| `STAGING_GCP_REGION`           | Cloud Run/Artifact Registry region              |
| `STAGING_GCP_BACKEND_SERVICE`  | Staging backend Cloud Run service               |
| `STAGING_GCP_FRONTEND_SERVICE` | Staging frontend Cloud Run service              |
| `STAGING_OCI_SSH_HOST`         | Optional dedicated staging voice-ws host        |
| `STAGING_OCI_SSH_USER`         | Optional staging SSH user; defaults to `ubuntu` |

The version-controlled `deploy/config/staging.env` file contains
`GCP_SECRET_NAME_PREFIX`, `GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT`, `OCI_VAULT_ID`,
`OCI_SECRET_NAME_PREFIX`, and non-secret application settings. It must never
contain secret values. Empty secret-key declarations opt optional managed
secrets into the release; omitted optional keys are not fetched even if an old
version remains in the manager. The normal local staging path does not use
these managed-cloud fields.

The staging service names must not be the production service names. For the
normal **local** staging flow, no GCP/OCI secrets are needed — only a local
`.env.staging` with the staging Supabase project `gdzwiwukcwbqohfwxxrx`.

## Manual production promotion

Run **Actions → Promote to production → Run workflow**, enter the full
40-character commit SHA that passed **local** staging validation, and submit
it. The workflow validates the SHA before requesting the protected production
environment. Do not promote a branch or tag: even a well-named tag can be moved
unless the repository enforces immutable tags. It then:

1. Checks out that ref in the protected `production` environment.
2. Checks out and validates the version-controlled
   `deploy/config/production.env`, authenticates to GCP with GitHub OIDC/WIF,
   and renders migration values from GCP Secret Manager. It then runs the same
   migration compatibility check and migration verification against
   production. The GCP deployer repeats the idempotent gate; the managed OCI
   job skips its duplicate gate only after the protected migration job
   succeeds.
3. The GCP deployment's migration-gated bootstrap synchronizes code-owned
   native tools and the three public demo agents before publishing images.
4. Deploys the checked-out ref to the production Cloud Run services.
5. Deploys the checked-out ref to the production voice-ws VM when configured.

Production promotion also has a non-canceling concurrency group, preventing
two manual approvals from racing production migrations or service updates.

Configure required reviewers on the GitHub `production` environment. Store
these there:

| Secret                           | Required | Purpose                                                        |
| -------------------------------- | -------- | -------------------------------------------------------------- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Yes      | Google Workload Identity Federation provider                   |
| `GCP_SERVICE_ACCOUNT`            | Yes      | WIF service account allowed to deploy and read managed secrets |
| `OCI_SSH_KEY`                    | Optional | Production voice-ws VM private key                             |

`NEXT_PUBLIC_POSTHOG_KEY` is no longer required in GitHub. Put the public
PostHog project token in `deploy/config/production.env`; the workflow keeps a
temporary fallback to the old GitHub environment secret during migration.

Optional production environment variables can override the defaults used by the
deployment scripts: `PRODUCTION_GCP_PROJECT_ID`, `PRODUCTION_GCP_REGION`,
`PRODUCTION_GCP_BACKEND_SERVICE`, `PRODUCTION_GCP_FRONTEND_SERVICE`,
`PRODUCTION_OCI_SSH_HOST`, and `PRODUCTION_OCI_SSH_USER`.

Production migration is intentionally in the same protected workflow as the
application deployment. A migration failure prevents the application jobs from
running. The GCP and manual OCI deploy scripts also run the same
compatibility-gated, idempotent migration step, so manual component
redeployments cannot publish code ahead of the database. The managed OCI job
receives an explicit skip only after that protected migration succeeds.
Successful cloud migrations request a PostgREST schema-cache reload. The
compatibility check is read-only and is not a replacement for backups, rollback
planning, or reviewing a migration's data-safety behavior.

Each GitHub Actions job runs on a fresh runner. The GCP promotion job therefore
installs the small migration requirements bundle before invoking the deploy
script's repeated compatibility gate; the migration job's Python environment is
not shared with the deployment job. The OCI voice-ws job transfers only
non-secret config and a value-free manifest; the VM's OCI instance principal
fetches current secret versions locally. It does not install a migration bundle
or receive a complete production env file.

The version-controlled `deploy/config/production.env` file contains
`GCP_SECRET_NAME_PREFIX`, `GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT`, `OCI_VAULT_ID`,
`OCI_SECRET_NAME_PREFIX`, and non-secret application settings. The release
validator rejects secret values and visible placeholders before any cloud
operation starts. Empty secret-key declarations opt optional managed secrets
into the release; omitted optional keys are not fetched even if an old version
remains in the manager.

## Managed secret flow and IAM

The complete design is documented in [secret management](secret-management.md),
and the current ownership map is in
[Current production secret map](production-secret-map.md).
The operational boundary is:

- GCP Secret Manager stores Cloud Run backend, migration, and shared runtime
  values. `render-gcp-env.py` is used only on an ephemeral runner for the
  migration gate. Cloud Run receives pinned `KEY=secret:version` references
  and resolves them with `GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT`.
- OCI Vault stores voice-ws values. The VM's dynamic-group instance principal
  reads only the secrets in the manifest. The SSH key transports source and
  configuration; it is not used to call OCI APIs.
- GitHub stores no long-lived GCP service-account key and no complete
  production environment file. Workload Identity Federation gives the runner
  short-lived GCP credentials.
- The GitHub WIF deployment identity is not the application runtime identity:
  it has per-secret `roles/secretmanager.secretAccessor` only where the
  migration/release path must read payloads, plus per-secret
  `roles/secretmanager.viewer` to list enabled versions for Cloud Run
  references. Cloud Run uses its own runtime service account.
- `JWT_SECRET_KEY` and `ENCRYPTION_KEY` must be synchronized in both managers
  because backend and voice-ws share the JWT/encryption trust boundary.

## Local versus CI

| Concern           | Local worktree                              | Local staging (shared DB)                             | Production promotion            |
| ----------------- | ------------------------------------------- | ----------------------------------------------------- | ------------------------------- |
| Application state | Dedicated Docker Compose project            | Local Docker Compose project (`--env staging`)        | Production Cloud Run/OCI        |
| Database          | Dedicated local Supabase project            | Cloud staging Supabase (`gdzwiwukcwbqohfwxxrx`)       | Cloud production Supabase       |
| Auth              | Seeded email/password user                  | Staging accounts (cloud)                              | Production accounts             |
| Env source        | Generated ignored `.worktree-state/app.env` | `.env.staging` (gitignored)                           | `deploy/config/production.env` + managed secret stores |
| Trigger           | `scripts/worktree-stack.sh up`              | `./scripts/validate-staging.sh` after merge to `main` | Manual workflow dispatch        |
| Approval          | Developer                                   | Release operator (local)                              | Protected environment reviewers |

For local worktree setup see
[Worktree Isolation and Release Promotion Strategy](worktree-and-release-strategy.md).
For local staging setup see `docs/05_operations/staging_environment.md`.
For migration and smoke-test recovery see [the runbook](runbook.md).
