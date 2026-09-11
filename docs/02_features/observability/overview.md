# Observability

24x7 AI correlates backend HTTP requests, signed voice sessions, Pipecat call
lifecycle events, tools, recording persistence and billing operations using
OpenTelemetry. Grafana Cloud is the production dashboard, storage and alerting
plane; Langfuse Cloud receives the same content-free traces for AI call
navigation. The pinned Prometheus/Loki/Tempo/Grafana/Alertmanager stack remains
available for isolated local development and a future self-hosted deployment.

Use the [operator guide](../../05_operations/observability.md) for setup,
demo-call walkthroughs, signal definitions, alerts, privacy and production
rollout. The isolated worktree launcher starts the monitoring stack with the
application and prints its URLs. The synthetic smoke command verifies actual
signal ingestion and queries, without an AI call or business mutation.

Metrics exclude customer/call identifiers. Diagnostic logs and traces carry safe
correlation IDs but no prompts, conversation content or raw tool payloads.
Existing authorized call logs/artifacts and credit transactions remain the
business source of truth. Monitoring access is reserved for platform operators.
