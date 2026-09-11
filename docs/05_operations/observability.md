# Operating observability

24x7 AI uses OpenTelemetry for backend and voice runtime signals. The launch
profile sends metrics, logs and traces through one authenticated collector to
Grafana Cloud, and sends the same content-free traces to Langfuse Cloud for an
AI-focused call view. Grafana Cloud supplies dashboards, storage and alerting;
Langfuse Cloud supplies optional AI trace exploration. The complete
Prometheus/Loki/Tempo/Grafana/Alertmanager stack remains available for local
development and a future self-hosted deployment, but it is not part of the
minimal production footprint.

## Start and use locally

From the feature worktree root:

```bash
./scripts/worktree-stack.sh config
./scripts/worktree-stack.sh up
```

The launcher creates an isolated application, Supabase, and monitoring stack.
Use the printed URLs, not the default ports. Grafana uses username `admin` and
a randomly generated password in `.worktree-state/app.env` under
`GRAFANA_ADMIN_PASSWORD`. Open that file locally to retrieve it; do not paste it
into tickets or logs. Grafana persists its password in its volume; changing the
environment variable after first startup does not reset an existing account.

Open **Dashboards → 24x7 AI → 24x7 AI — Operations and calls**. Start with
readiness, API errors, active calls and firing alerts. Select a recent time
range and refresh after a call. Metrics export every 15 seconds; allow about
30 seconds for collection and scraping. An empty panel means **no data**, not
zero errors. Rate/increase panels need at least two scrapes; very short-lived
synthetic emitters may show a counter but not a meaningful rate.

### Try a demo call

1. Use an appointment or lead-capture demo URL printed by `config`, or sign in
   with the printed local organization-admin account and start an agent test call.
2. Ask a normal question; then use a configured tool, such as checking available
   appointments. Only confirm real tool side effects if you intend them. The
   telemetry smoke command below uses no provider calls or business mutations.
3. End the call. In browser Developer Tools → Network, locate the session-creation
   response and copy `sessionId`. Alternatively use the call-log ID in Call Logs.
4. Paste that ID into the Grafana **Session or call ID** filter. Scroll to **Call
   events**. Expand an event and use **Links → TraceID / Tempo** to inspect spans.
5. Look for `call.started`, `call.tracking_started`, `call.answered`, turn events,
   `tool.result`, `operation.finished`, and `call.finished`. Recording events
   occur only when recording is enabled. Billing settlement has its own outcome;
   demo calls normally consume no credits.

If the production Langfuse project is enabled, open its **Traces** view and
search by the session/call identifier or trace ID shown in Grafana. The
`voice.call` trace contains the setup, provider stage, tool and persistence
spans; use Grafana for metrics, logs and alert response. Langfuse receives
metadata-only OTLP traces through the collector, following its [OpenTelemetry
ingestion contract](https://langfuse.com/integrations/native/opentelemetry).

The event records expose timestamps, call/session IDs, safe operation names,
status, duration and trace IDs. They do **not** contain what a person said,
prompts, audio, tool arguments/results, email addresses, credentials or URLs.
Existing authorized recordings and call logs remain the place to inspect
conversation artifacts. Loki is an operator-only diagnostic store across tenants;
do not expose it as a customer query API.

### Synthetic end-to-end check

Set `GRAFANA_ADMIN_PASSWORD` in your shell from your private app environment,
then substitute the collector HTTP and Grafana ports printed by the launcher:

```bash
.venv/bin/python scripts/observability-smoke.py --otlp http://localhost:4318 --grafana http://localhost:3300
```

This sends a synthetic call/tool trace, content-free events and metrics, then
queries Tempo, Loki, Prometheus and the provisioned dashboard through authenticated
Grafana. Success prints four `verified` messages and correlation IDs. It does
not call an AI provider, place a phone call, or create business records. It
requires the backend development dependencies plus the HTTP OTLP exporter now
included in the backend requirements.

For a standalone local telemetry stack without the application, set the
Grafana password in a private environment file and run:

```bash
docker compose -p observability -f docker-compose.observability.yml up -d
```

The default readiness targets refer to app services, so `ServiceNotReady` is
expected in this standalone mode. Do not silence this alert in an app deployment.

The regular `.env.local` and `.env.staging` examples keep application
telemetry disabled. `scripts/worktree-stack.sh` deliberately opts its isolated
test environment into the private local stack so a developer can verify a
trace without creating a hosted account. Staging never sends data to the
production Grafana or Langfuse projects.

## What is measured

| Signal                                | Meaning                                                   | Dimensions                                      |
| ------------------------------------- | --------------------------------------------------------- | ----------------------------------------------- |
| `platform_http_requests_total`        | API request count and status                              | route template, method, status, service/release |
| `platform_http_duration_seconds`      | API duration histogram                                    | same bounded route/status dimensions            |
| `platform_voice_active`               | Admitted calls currently running                          | channel                                         |
| `platform_voice_calls_total`          | Calls that finished, failed or were cancelled             | outcome, channel                                |
| `platform_voice_duration_seconds`     | Setup-through-cleanup call duration                       | outcome, channel                                |
| `platform_operation_count_total`      | Setup, tool, recording, tracking and billing outcomes     | fixed operation, outcome                        |
| `platform_operation_duration_seconds` | Operation latency distribution                            | fixed operation, outcome                        |
| `platform_tool_results_total`         | Model-visible tool success/error, including caught errors | outcome                                         |
| `platform_ai_ttfb_seconds`            | Provider time to first byte reported by Pipecat           | stage                                           |
| `platform_ai_processing_seconds`      | Provider processing durations                             | stage                                           |
| `platform_ai_tokens_total`            | Reported input/output LLM tokens                          | token type                                      |
| `platform_ai_tts_characters_total`    | Reported TTS character usage                              | service                                         |
| `platform_voice_interruptions_total`  | Interruption control frames                               | service                                         |
| `platform_readiness_checks_total`     | Cached dependency probe outcomes                          | outcome                                         |
| `otelcol_exporter_send_failed_*`      | Collector export failures                                 | exporter                                        |
| `otelcol_exporter_queue_size`         | Buffered batches waiting for a destination                | exporter                                        |
| `otelcol_receiver_refused_*`          | Telemetry rejected by the collector                       | receiver                                        |

Histograms expose `_bucket`, `_sum` and `_count` series. OTel names use dots;
the Prometheus exporter normalizes dots to underscores and adds units/suffixes.
Identifiers, raw tool/model names and customer data are not metric labels.
Native Pipecat metrics vary by provider: absence of a timing or token metric is
not a zero value. Token usage is not a price quote or billing ledger. The stack
does not invent dollar costs for provider-reported tokens or audio billing.

Browser API requests generate a W3C `traceparent`; the backend returns
`x-request-id` and `x-trace-id`. The shared API client's `ApiRequestError` exposes
`requestId` for support diagnostics. Backend session issuance signs its current
trace context into the voice JWT, allowing browser and Twilio calls to continue
the trace. Only verified session claims authorize a call; correlation is never
an authorization mechanism. Legacy tokens without trace context still work.

## Health and failure semantics

Backend `/health` and `/health/ready` return 503 when the bounded Supabase REST
probe fails or configuration is missing. `/health/live` only checks the running
process. Voice `/health` remains a liveness alias; voice `/health/ready` checks
Supabase and `/health/live` checks the process. Probes use a five-second cache,
a single in-flight request and a two-second network timeout. They request zero
organization rows. AI providers are not called by health checks; their failures
are diagnosed from actual calls, avoiding paid probes and restart storms.

Operation exceptions are re-raised normally. Caught billing/finalization/tool
errors still mark telemetry as failures. Metrics and diagnostic event logs are
independent of trace sampling. Call cancellation decrements active-call counts.
Telemetry exports run in background SDK workers; audio frames are not copied.

## Alerts and response

The production-compatible rules in `deploy/observability/alerts.cloud.yml`
use application metrics delivered over OTLP and have deterministic tests in
`alerts.cloud.test.yml`. The full local/self-hosted rules in
`deploy/observability/alerts.yml` additionally cover blackbox probes, local
collector metrics and disk pressure; those expressions are not available in
the cloud-only profile. Create the cloud rules in Grafana Cloud, attach an
owned contact point, and verify firing, notification receipt and resolution
with the on-call owner during release.

### ServiceNotReady

After two minutes of failed application readiness checks, inspect the target
service and Supabase connectivity/credentials. Compare `/health/live` with
`/health/ready`. Do not restart healthy processes repeatedly during a shared
database outage.

### TelemetryUnavailable (self-hosted fallback)

The full local/self-hosted Prometheus stack has a scrape target unavailable for
two minutes. Inspect collector/store containers and networking first. In the
cloud profile, use the protected collector `/health` endpoint with a Grafana
Cloud Synthetic Monitoring or equivalent HTTPS uptime check; a healthy
application cannot prove telemetry is flowing. Run the synthetic smoke check
after recovery.

### APIErrorBudgetBurn

The initial availability objective is 99.9% successful HTTP requests, treating
5xx as failures. The page requires both five-minute and one-hour error ratios
over 1.44% (14.4 times the error budget), with at least 20 requests in five minutes.
Inspect routes, release version and correlated errors. Low-traffic platform
availability is also protected by application readiness checks. This is an initial operational
objective, not a contractual SLA; review thresholds against real traffic.

### VoiceFailures

Three failed calls in ten minutes trigger a critical alert. Filter recent
`call.pipeline_failed` / `call.failed` events, then examine their trace. Check
provider configuration, entitlement failures and transport logs. A pipeline
failure differs from a later recording or billing failure.

### ToolFailures

Both returned tool errors and raised exceptions count toward this alert and the
Tool outcomes panel. A recovered tool failure does not automatically fail the call.

Three model-visible tool errors in ten minutes trigger a warning. Use `tool.result`
and the tool span to identify the integration. Check permissions/configuration
before retrying a mutation; observability never automatically retries tools.

### PersistenceFailure

A failed recording persistence, call finalization or billing settlement triggers
a warning. Inspect the operation and failure code. Check call logs, recording
artifacts and the credit ledger before repair. Do not blindly repeat a debit.
A missing ledger row is a reconciliation problem even when the call sounded fine.

### LogStorageDiskPressure (self-hosted fallback)

Loki reports the disk usage of its WAL filesystem. At 85% this alert gives
headroom before Loki's 90% protection stops writes. Increase the dedicated
disk or reclaim verified disposable artifacts; never prune database volumes.
After restoring free space, restart only Loki if its ingester remains stopped,
and run the synthetic smoke check to verify logs are arriving again. Collector
queues buffer a bounded outage, but telemetry can be lost when they fill.

### CollectorExportFailure (cloud and self-hosted)

Export failures indicate that Grafana Cloud or Langfuse cannot be reached or is
rejecting data. Check the collector logs, credentials, destination status and
network reachability. The cloud profile self-scrapes collector metrics, so this
alert remains visible in Grafana Cloud even when application telemetry is
backing up. SDK queues hold 2,048 records. The cloud profile keeps 512 batches
per exporter on persistent disk and retries for up to 120 seconds; the
local/self-hosted profile keeps 1,000 batches and retries for up to five
minutes. Prolonged overload can lose telemetry. Restore the destination before
increasing queue sizes.

### CollectorQueuePressure (cloud and self-hosted)

The collector's persistent queue is above 70% for five minutes. Check outbound
network access, Grafana/Langfuse status and the host disk before restarting the
collector. A restart with the named queue volume preserves buffered data.

### CollectorRefusedTelemetry (cloud and self-hosted)

The collector refused incoming spans, metrics or logs, usually because it is
overloaded or its memory limiter is active. Check queue pressure and collector
memory, then reduce unnecessary trace sampling only after the destination is
healthy.

### SlowAIResponse

A stage p95 time to first byte above three seconds for ten minutes raises a
warning. Compare STT/LLM/TTS stages and operation latency. A provider may not
report every metric; missing data requires a trace/call check.

## Production deployment

The minimal production profile is `docker-compose.observability.cloud.yml`.
It runs two long-lived containers plus a one-shot volume initializer on a
small dedicated host:

- Caddy terminates HTTPS and protects the OTLP endpoint with a service account.
- The OpenTelemetry Collector batches, queues and forwards telemetry to
  Grafana Cloud and metadata-only traces to Langfuse Cloud.

Grafana, Prometheus, Loki, Tempo and Alertmanager are not deployed in this
profile. They are hosted by Grafana Cloud. The full local stack remains in
`docker-compose.observability.yml` for development and self-hosted fallback.

Before an authorized production deployment:

1. Create one Grafana Cloud stack and one Langfuse project. Keep both projects
   production-only. Generate a Grafana Cloud OTLP token and a Langfuse public/
   secret key pair; store only their Basic authorization values in the private
   collector environment file. Choose the Langfuse region that matches the
   approved data policy.
2. Provision a small host, a DNS name such as `telemetry.example.com`, and
   firewall access for ports 80/443. This host may be separate from the voice
   VM; do not expose the collector's internal port publicly.
3. Copy `.env.observability.example` to the ignored `.env.observability` and
   set `GRAFANA_CLOUD_OTLP_ENDPOINT`, `GRAFANA_CLOUD_OTLP_AUTH`,
   `LANGFUSE_OTLP_ENDPOINT`, `LANGFUSE_OTLP_AUTH`, `OBSERVABILITY_DOMAIN`,
   `OTLP_USERNAME`, and the bcrypt `OTLP_PASSWORD_HASH`. Generate the bcrypt
   hash interactively with Caddy; do not store a plaintext password:

   ```bash
   docker run --rm -it caddy:2.11.4 caddy hash-password --plaintext
   ```

   Copy the Grafana Cloud OTLP gateway URL shown in the stack's **Send
   telemetry** instructions and keep the `/otlp` base path. Langfuse Cloud's
   OTLP URL is the selected regional `/api/public/otel` endpoint.

4. Validate the minimal profile before starting it:

   ```bash
   docker compose --env-file .env.observability \
     -p observability-cloud \
     -f docker-compose.observability.cloud.yml config --quiet
   ```

5. Set the production app environment to `OTEL_ENABLED=true`, use
   `https://<observability-domain>/v1/traces`, `/v1/metrics` and `/v1/logs`,
   use protocol `http/protobuf`, and set the matching OTLP Basic header through
   the deployment secret manager. The GCP environment generator emits distinct
   service names for backend and voice-ws. Langfuse credentials remain on the
   collector and are never copied into application containers.
6. Keep `NEXT_PUBLIC_OTEL_ENABLED=false`. Browser requests still carry a W3C
   trace context so an operator can correlate the UI request with the backend
   and voice call without exposing an ingestion credential.
7. Run the synthetic smoke check, an authorized browser call, and the PSTN
   release gate. Import `deploy/observability/grafana/dashboards/platform-cloud-import.json`
   into Grafana Cloud and select its Prometheus and Loki data sources. Create
   contact points and import the cloud-compatible thresholds from
   `deploy/observability/alerts.cloud.yml`; then fire one test alert and verify
   both notification and resolution. Create an HTTPS uptime check for
   `https://<observability-domain>/health` using the OTLP service account so a
   collector outage is visible even when no application call is running. Keep
   GCP/OCI uptime, host/disk, provider-quota and budget alerts as independent
   backstops.

Production is enabled only after the collector, cloud credentials and alert
route exist. Local and staging examples remain disabled and never use the
production cloud projects.

## Privacy, overhead and scope

The export boundary uses an explicit scalar allowlist and strips legacy exception
messages, arbitrary attributes and payloads. Safe events carry stable error types
and codes. The standard `session.id` attribute is propagated through every call
span so Langfuse can filter a trace by session; the dashboard-compatible
`session_id` field is retained in diagnostic events. Legacy unstructured log
bodies become logger/level summaries in OTLP; existing console logging is a
separate boundary and should not be forwarded wholesale without a separate
redaction policy. New tool/MCP logging avoids raw arguments/results. Privacy
tests cover sentinel payloads and credentials.

The production cloud profile fans out the existing content-free trace to
Langfuse for call lifecycle, provider/model, timing, token, tool status and
error navigation. It does not capture prompts, completions, transcripts, audio,
tool arguments/results, or a new database event ledger. Existing call
logs/artifacts/credit transactions remain the durable business source of truth;
Grafana and Langfuse explain operations but are not transactional or compliance
audit ledgers. SDK/process crashes can lose unexported records. Prompt capture,
evaluations or a dedicated audited event ledger can be added later when their
retention and access requirements are specified.

The observer inspects only control and metrics frames, with at most 1,024 recent
frame IDs retained per call. Metrics use cached instruments, bounded labels and
batched exports. Synchronous call-tracking database requests now run outside the
audio event loop. Root tracing defaults to 100% for initial low traffic;
`OTEL_TRACES_SAMPLER_ARG` tunes the root ratio. Metrics and logs remain unsampled.
Do not treat a synthetic latency benchmark as proof of live provider latency.

## Validation commands

```bash
.venv/bin/pytest -c pytest.ini -o 'pythonpath=. voice-ws shared' shared/tests/observability voice-ws/tests/test_telemetry.py --cov=shared.observability --cov=shared.config.opentelemetry --cov=src.telemetry --cov-branch --cov-fail-under=90
.venv/bin/pytest -c pytest.ini -o 'pythonpath=. voice-ws shared' voice-ws/tests
.venv/bin/pytest -c pytest.ini backend/tests shared/tests -o 'pythonpath=backend shared .'
.venv/bin/python scripts/run-agent-evals.py
cd frontend
npm run test:run
npx tsc --noEmit
```

Backend and voice each have a `src` package, so run their suites separately with
the shown path configuration. Supply isolated test credentials as required by
the existing test harness. Do not use shared staging for these tests.

```bash
docker run --rm --network none -v "$PWD/deploy/observability:/rules:ro" --entrypoint promtool prom/prometheus:v3.14.0 test rules /rules/alerts.test.yml
docker run --rm --network none -v "$PWD/deploy/observability:/rules:ro" --entrypoint promtool prom/prometheus:v3.14.0 test rules /rules/alerts.cloud.test.yml
```

## Upstream references

- [OTel collector queue sizing and scaling](https://opentelemetry.io/docs/collector/scaling/)
- [Loki native OTLP ingestion](https://grafana.com/docs/loki/latest/send-data/otel/)
- [Tempo monolithic deployment and storage](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/deploy/locally/linux/)
- [Prometheus alert rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager routing](https://prometheus.io/docs/alerting/latest/configuration/)
