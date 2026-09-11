# OpenTelemetry implementation

The current implementation and operating contract are documented in the
[observability operator guide](../05_operations/observability.md).

- `shared/config/opentelemetry.py`: idempotent process lifecycle, explicit OTLP
  HTTP/gRPC configuration, bounded background exporters and safe export filtering.
- `shared/observability/`: safe fields, events, operation metrics, HTTP middleware,
  readiness and voice/tool wrappers.
- `voice-ws/src/telemetry.py`: pinned Pipecat control-frame and native metric observer.
- `frontend/src/lib/api/correlation.ts`: content-free W3C API context and validated
  support request IDs; no browser collector credentials.
- `deploy/observability/`: pinned local stack, dashboard provisioning,
  alert rules/tests, and the minimal cloud collector plus authenticated HTTPS
  ingress.
- `scripts/observability-smoke.py`: synthetic end-to-end ingestion/query verification.

The older New Relic-only setup instructions and public `/test-otel` endpoint are
superseded. Use the isolated worktree stack and synthetic smoke script. Health
semantics, sampling limits, retention and production enablement are explicit in
the operator guide; a configured SDK alone does not prove signals are delivered.
