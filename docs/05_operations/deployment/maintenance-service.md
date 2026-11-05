# Maintenance service

The maintenance service is a separate FastAPI process. It runs OAuth refresh,
recovery queues, free-plan renewals, plan migrations, and phone-rental lifecycle
checks. It starts no in-process timers. A scheduler sends authenticated POST
requests; no scheduler provider is required by the domain code.

The API defaults to `MAINTENANCE_MODE=external` in production and `in_process`
in development and staging. Provision the migration, separate worker,
scheduler, monitoring, and cutover checks before enabling a production API
deployment. Either default can be explicitly overridden. Never run both modes
concurrently: existing API loops do not share the worker's global job claims.

## Packaging and configuration

The backend Dockerfile has two targets: `backend` (the default) and
`maintenance`. The maintenance target runs `maintenance_main:app` on port 8000
as a non-root user. It needs the same database, encryption, provider, and
recording-storage settings as the relevant backend jobs, plus a separate,
high-entropy `MAINTENANCE_AUTH_TOKEN` of at least 32 ASCII characters. Inject
secrets from the deployment's secret store. Do not expose this token in logs,
source control, screenshots, or public scheduler definitions.

The maintenance service itself does not start API scheduler loops.
The worker also verifies the existing legacy OAuth-secret migration before
accepting work. Deploy the worker on a private network or equivalent ingress
control where available.

The backend GCP deploy script selects zero minimum instances and request-based
CPU allocation in production's default external mode. In-process mode keeps
one instance with CPU allocated between requests. Deploying external mode
without completing the cutover below stops recurring work.

## Triggers and cadence

`POST /v1/tick` checks all five jobs and runs each one only when its configured
interval is due. `POST /v1/jobs/{job}` checks a single named job. Requests need
the maintenance token either as a bearer token or in `X-Maintenance-Key`; the
latter permits a separate infrastructure identity in the Authorization header.
`GET /health` reports process liveness. `GET /v1/status` requires the same
authentication and returns expected job names and persisted timestamps, but no
claim tokens or customer data. It returns HTTP 503 for missing initial runs,
failed claims, a run lasting over 15 minutes, or a last success older than twice
the configured interval plus a minute (at least five minutes). Review these
thresholds against measured job durations before enabling alerts.

Jobs retain the existing OAuth, notification, renewal, migration, and phone
settings. The phone cadence is read from runtime administrator settings. Set
the scheduler interval no longer than the shortest configured job interval;
otherwise jobs can be delayed. A one-minute Cloud Scheduler tick is one possible
deployment configuration; it generates roughly 43,200 requests in a 30-day
month. Scheduler, compute, networking, and other service costs must all be
measured. A free allowance is not a spending guarantee.

Cloud Run IAM can restrict a maintenance service to a scheduler identity, but
the current application adapter also requires the maintenance token. If using
Cloud Scheduler, protect its configuration because HTTP headers are part of the
job configuration. QStash is an alternative HTTP scheduler; its reachable ingress,
authentication, retry limits, and pricing must be reviewed for the chosen plan.

Cloud Scheduler is the initial production choice: one scheduler job drives all
five independent cadences, and its service identity can invoke a private Cloud
Run service. QStash remains an alternative for another hosting provider, but
its current free allowance of 1,000 delivery attempts per day cannot sustain
the selected one-minute tick (1,440 attempts per day before retries). Review
[Cloud Scheduler pricing](https://cloud.google.com/scheduler/pricing) and
[QStash pricing](https://upstash.com/pricing/qstash) when provisioning.
The database is the coordination boundary; a separate message queue is not
needed for these periodic passes and would add another provider and failure mode.

## Coordination and recovery

The `maintenance_runs` database table permits only one claim per job. Success
records a timestamp and releases the claim. A classified retry-safe failure
records a failure timestamp and releases the claim; uncertain failures and
interruptions retain the claim. A retained claim does not expire automatically:
an external provider might have accepted a request even if the worker did not
record the response.

Notification providers have at-least-once delivery semantics: if a provider
accepts a message and the database acknowledgement is lost, a later retry can
duplicate delivery. OAuth has additional per-connection leases and credential
generation fencing. Phone rental and plan migration claims remain held on
unclassified failure because their provider mutations require reconciliation.

Alert independently on scheduler failure, unreachable status, any `failed`
job, a `running` job exceeding its reviewed maximum run duration, a missing
initial job, or an overdue `last_succeeded_at`. Monitoring must remain capable
of alerting if the Google project or its billing account is unavailable.
The status response also reports a failed or long-running phone guard without
exposing the organization ID. A configured `MAINTENANCE_HEARTBEAT_URL` sends
an HTTPS POST only after a tick and the persisted status are healthy. Configure
an independent dead-man monitor, such as Healthchecks.io, with a one-minute
period, a reviewed grace period (start with 20 minutes), and email alerts.
Grafana Cloud IRM's webhook heartbeat is another compatible option; configure
an escalation chain and the recipient's notification rules, not just the
heartbeat interval. The currently configured production check uses a 30-minute
interval and an email escalation to the account owner. Verify the recipient and
delivery whenever changing the integration.
Treat the ping URL as a secret. Test the alert by pausing a staging scheduler;
test separately that an unhealthy job prevents a success signal. This monitors
maintenance, not the public website or voice service: use separate external
uptime checks for those endpoints and exercise real calls in release testing.
Production Google Cloud uptime checks for the backend and website run every
15 minutes from three US regions. Each region checks independently, so each
endpoint receives at least 12 checks per hour. This reduces monitoring requests
at the cost of slower outage detection; it does not guarantee that instances
stay warm or scale to zero. Review alert timing when changing the check period.

## Prepared Google Cloud deployment

These commands are release operations: use the exact staging-validated commit,
complete the repository release approval, and apply the migration first. Create
the worker auth token and the heartbeat URL as separate Secret Manager secrets;
give the worker runtime identity access. Both must have numeric secret versions.
Use an existing artifact repository and deploy the worker without switching the
API or enabling the scheduler:

```bash
export GCP_PROJECT_ID=YOUR_PROJECT GCP_REGION=us-central1
export GCP_BACKEND_RUNTIME_SERVICE_ACCOUNT=WORKER_SERVICE_ACCOUNT
export GCP_SECRET_NAME_PREFIX=YOUR_SECRET_PREFIX
export MAINTENANCE_AUTH_SECRET_REF=AUTH_SECRET_ID:VERSION
export MAINTENANCE_HEARTBEAT_SECRET_REF=HEARTBEAT_SECRET_ID:VERSION
export RELEASE_TAG=REVIEWED_40_CHARACTER_COMMIT_SHA
bash scripts/deploy/gcp-maintenance.sh
```

Create a dedicated scheduler identity, but do not grant it worker invocation
permission yet. Permit the Cloud Scheduler service agent to mint its identity
tokens. Restrict
who can read scheduler job configuration: the application authentication header
is stored there, even though the setup script does not print its value. Create
the scheduler once (it fails if the job already exists):

```bash
export MAINTENANCE_SERVICE_URL=YOUR_WORKER_RUN_APP_URL
export MAINTENANCE_SCHEDULER_SERVICE_ACCOUNT=SCHEDULER_SERVICE_ACCOUNT
python3 scripts/deploy/gcp-create-maintenance-scheduler.py
```

Immediately pause the scheduler and verify it is `PAUSED` before granting its
identity `roles/run.invoker` on the worker. Until that grant, scheduled requests
cannot invoke the private service. The backend deployer refuses to deploy in
external mode unless the worker exists and the scheduler is paused. Deploy the
API, wait for every old in-process revision to stop, and then resume the
scheduler. For later backend deployments, pause and resume it around the deploy
as well, and verify the independent heartbeat resumes. A paused scheduler is
not a substitute for checking that old worker executions have finished.

The scheduler sends one request per minute with OIDC and the separate secret
header. `MAINTENANCE_AUTH_SECRET_REF` must match the worker's version. Rotate
both together with a controlled transition. The worker, scheduler, IAM grants,
secret versions, independent check, and alert recipient all require actual
provisioning and verification; these scripts do not create accounts or grant
permissions. The Cloud Run service limit bounds instances, not monthly spending.
The current production project has a $5 monthly Cloud Run spend cap and
automatic Google alerts at 50%, 80%, and 100%. Google bases enforcement on
estimated gross usage before credits and free-tier savings, so the cap can pause
the site even when the eventual bill is below $5 or zero. Enforcement is delayed
and may overshoot; it covers only Cloud Run in this project, not other Google
services or other providers. Ordinary budget alerts are not a spending cap.
Review the threshold after observing the new configuration's usage, balancing
the user's cost preference with availability.

To recover a held claim, first identify the exact job and claim from the
service-role-only `maintenance_runs` table. Verify the old worker is stopped,
and inspect and reconcile the corresponding provider and database outcome. Only
then, from a trusted environment with the service-role configuration, run:

```bash
cd backend
PYTHONPATH=.. python -m src.maintenance.reconcile --job JOB --claim CLAIM \
  --worker-stopped --provider-outcome-verified
```

The command requires the exact held claim. Never clear a running or failed
claim just to suppress an alert. A running container may still be performing
an external mutation even if its HTTP request timed out.

## Required cutover validation

Before production, verify the migration in an isolated environment and staging,
and prove authenticated triggers, missed schedules, stale or failed claims,
provider failures, overlapping requests, job cadence changes, and monitoring
alerts. Exercise both browser and PSTN voice flows plus billing and notification
recovery. Ensure the old API schedulers are fully stopped before starting the
external scheduler, and provide a rollback that also avoids overlap. Shared
staging migrations and production deployment require the documented release
approval and ownership.

Before production, provision and verify the prepared scheduler, independent
alert integration, and cutover in staging. In external mode, phone mutation
routes and the rental worker additionally serialize per organization; busy organizations are retried
on a later tick without blocking other organizations. Worker rows are re-read
under that guard. In-process mode retains the legacy scheduling behavior.
