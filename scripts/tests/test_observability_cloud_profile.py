"""Contracts for the minimal production cloud observability profile."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLOUD_COMPOSE = ROOT / "docker-compose.observability.cloud.yml"
COLLECTOR_CONFIG = ROOT / "deploy" / "observability" / "collector.cloud.yml"
CADDYFILE = ROOT / "deploy" / "observability" / "Caddyfile.cloud"
CLOUD_ALERTS = ROOT / "deploy" / "observability" / "alerts.cloud.yml"
CLOUD_DASHBOARD = (
    ROOT
    / "deploy"
    / "observability"
    / "grafana"
    / "dashboards"
    / "platform-cloud-import.json"
)


def test_cloud_compose_has_only_the_minimal_runtime_services():
    """Cloud storage replaces the local Grafana/Loki/Tempo containers."""
    compose = CLOUD_COMPOSE.read_text()
    assert "  otel-collector:" in compose
    assert "  ingress:" in compose
    assert "  telemetry-volume-init:" in compose
    for service in ("grafana:", "prometheus:", "loki:", "tempo:", "alertmanager:"):
        assert f"  {service}" not in compose
    assert "GRAFANA_CLOUD_OTLP_ENDPOINT" in compose
    assert "LANGFUSE_OTLP_ENDPOINT" in compose
    assert "127.0.0.1:${HOST_OTEL_HEALTH_PORT:-13133}:13133" in compose


def test_cloud_collector_fanout_keeps_langfuse_metadata_only():
    """Only traces fan out to Langfuse; metrics and logs stay in Grafana."""
    config = COLLECTOR_CONFIG.read_text()
    assert "otlphttp/grafana:" in config
    assert "otlphttp/langfuse:" in config
    assert "prometheus/self:" in config
    pipelines = config.split("  pipelines:\n", 1)[1]
    traces = pipelines.split("    traces:\n", 1)[1].split("    metrics:\n", 1)[0]
    metrics = pipelines.split("    metrics:\n", 1)[1].split("    logs:\n", 1)[0]
    logs = pipelines.split("    logs:\n", 1)[1]
    assert "otlphttp/grafana" in traces
    assert "otlphttp/langfuse" in traces
    assert "otlphttp/langfuse" not in metrics
    assert "otlphttp/langfuse" not in logs
    assert "prometheus/self" in metrics
    assert 'x-langfuse-ingestion-version: "4"' in config


def test_cloud_ingress_accepts_only_authenticated_otlp_paths():
    """The collector is never exposed as an unauthenticated catch-all."""
    caddy = CADDYFILE.read_text()
    assert "@health path /health" in caddy
    assert "reverse_proxy otel-collector:13133" in caddy
    assert "@otlp path /v1/traces /v1/metrics /v1/logs" in caddy
    assert "basic_auth" in caddy
    assert "request_body" in caddy and "max_size 4MB" in caddy
    assert "reverse_proxy otel-collector:4318" in caddy
    assert "respond 404" in caddy


def test_cloud_dashboard_can_be_imported_with_hosted_data_sources():
    """The production dashboard does not assume local datasource UIDs."""
    dashboard_text = CLOUD_DASHBOARD.read_text()
    dashboard = json.loads(dashboard_text)
    inputs = {item["name"]: item for item in dashboard["__inputs"]}
    assert inputs["DS_PROMETHEUS"]["pluginId"] == "prometheus"
    assert inputs["DS_LOKI"]["pluginId"] == "loki"
    datasources = [
        panel.get("datasource", {})
        for panel in dashboard["panels"]
        if isinstance(panel.get("datasource"), dict)
    ]
    assert {source["uid"] for source in datasources} <= {
        "${DS_PROMETHEUS}",
        "${DS_LOKI}",
    }
    assert "platform_readiness_checks_total" in dashboard_text
    assert "Collector export failures" in dashboard_text
    assert "Collector queue utilization" in dashboard_text
    assert "probe_success" not in dashboard_text


def test_cloud_alerts_use_application_metrics_only():
    """Hosted alerting must not depend on local scrape or stateful containers."""
    rules = CLOUD_ALERTS.read_text()
    for alert in (
        "ServiceNotReady",
        "APIErrorBudgetBurn",
        "VoiceFailures",
        "ToolFailures",
        "PersistenceFailure",
        "SlowAIResponse",
        "CollectorExportFailure",
        "CollectorQueuePressure",
        "CollectorRefusedTelemetry",
    ):
        assert f"alert: {alert}" in rules
    for local_only_metric in ("probe_success", "up{", "loki_"):
        assert local_only_metric not in rules
    assert "otelcol_exporter_send_failed_" in rules
    assert "otelcol_exporter_queue_size" in rules
    assert "otelcol_receiver_refused_" in rules


def test_canonical_app_examples_keep_cloud_observability_opt_in():
    """Only a provisioned production deployment should enable exporters."""
    assert "OTEL_ENABLED=false" in (ROOT / ".env.local.example").read_text()
    assert "OTEL_ENABLED=false" in (ROOT / ".env.staging.example").read_text()
    production = (ROOT / ".env.prod.example").read_text()
    assert "OTEL_ENABLED=false" in production
    assert "https://telemetry.yourdomain.com/v1/traces" in production
