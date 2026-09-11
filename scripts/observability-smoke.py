#!/usr/bin/env python3
"""Send synthetic telemetry and verify all three stores through Grafana."""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    """Verify local OTLP ingestion and authenticated operator queries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--otlp", default="http://localhost:4318")
    parser.add_argument("--grafana", default="http://localhost:3300")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    password = os.environ.get("GRAFANA_ADMIN_PASSWORD")
    if not password:
        parser.error("Set GRAFANA_ADMIN_PASSWORD in the environment")
    os.environ["ENVIRONMENT"] = "test"
    os.environ["OTEL_ENABLED"] = "true"
    os.environ["OTEL_SERVICE_NAME"] = "247ai-smoke"
    for signal in ("TRACES", "METRICS", "LOGS"):
        os.environ[f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT"] = (
            f"{args.otlp}/v1/{signal.lower()}"
        )
        os.environ[f"OTEL_EXPORTER_OTLP_{signal}_PROTOCOL"] = "http/protobuf"
    from opentelemetry import trace

    from shared.config import opentelemetry as sdk
    from shared.observability.signals import correlation, event, operation, record

    logging.getLogger().setLevel(logging.INFO)
    sdk.setup_opentelemetry("247ai-smoke")
    session = "smoke-" + str(time.time_ns())
    token = correlation.set({"session_id": session, "channel": "test_call"})
    try:
        with operation("voice.call"):
            trace_id = f"{trace.get_current_span().get_span_context().trace_id:032x}"
            event("call.started")
            with operation("tool.execute", tool="synthetic_no_side_effect"):
                record("platform.tool.results", outcome="success")
                event("tool.result", outcome="success")
            record("platform.voice.calls", channel="test_call", outcome="success")
            event("call.finished", outcome="success")
        sdk.tracer_provider.force_flush(timeout_millis=5000)
        sdk.logger_provider.force_flush(timeout_millis=5000)
        sdk.meter_provider.force_flush(timeout_millis=5000)
    finally:
        correlation.reset(token)
        sdk.shutdown_opentelemetry()
    http = requests.Session()
    http.auth = ("admin", password)

    def get(path, **params):
        response = http.get(args.grafana.rstrip("/") + path, params=params, timeout=5)
        response.raise_for_status()
        return response.json()

    pending = {"metrics", "logs", "traces", "dashboard"}
    deadline = time.monotonic() + args.timeout
    while pending and time.monotonic() < deadline:
        for signal in list(pending):
            try:
                if signal == "metrics":
                    data = get(
                        "/api/datasources/proxy/uid/prometheus/api/v1/query",
                        query='platform_voice_calls_total{service_name="247ai-smoke"}',
                    )
                    ok = bool(data["data"]["result"])
                elif signal == "logs":
                    data = get(
                        "/api/datasources/proxy/uid/loki/loki/api/v1/query_range",
                        query=(
                            '{service_name="247ai-smoke"} ' f'| session_id="{session}"'
                        ),
                        limit=20,
                    )
                    ok = bool(data["data"]["result"])
                elif signal == "traces":
                    data = get(
                        "/api/datasources/proxy/uid/tempo/api/traces/" + trace_id
                    )
                    ok = bool(data.get("batches") or data.get("resourceSpans"))
                else:
                    ok = (
                        get("/api/dashboards/uid/247ai-operations")["dashboard"]["uid"]
                        == "247ai-operations"
                    )
                if ok:
                    pending.remove(signal)
                    print(signal + ": verified", flush=True)
            except (requests.RequestException, ValueError, KeyError):
                pass
        if pending:
            time.sleep(2)
    if pending:
        raise SystemExit("Not verified: " + ", ".join(sorted(pending)))
    print(
        f"Session: {session}\nTrace: {trace_id}\n"
        f"Dashboard: {args.grafana}/d/247ai-operations"
    )


if __name__ == "__main__":
    main()
