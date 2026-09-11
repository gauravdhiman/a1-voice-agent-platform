"""SDK exporter configuration, bounded lifecycle and legacy privacy contracts."""

import logging
from unittest.mock import Mock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

from shared.config import opentelemetry as sdk
from shared.observability import signals


@pytest.mark.parametrize("signal", ["traces", "metrics", "logs"])
@pytest.mark.parametrize("protocol", ["grpc", "http/protobuf"])
def test_exporter_honors_endpoint_protocol_and_credentials(
    monkeypatch, signal, protocol
):
    import importlib

    module = Mock()
    monkeypatch.setattr(importlib, "import_module", lambda name: module)
    monkeypatch.setattr(sdk.settings, f"otel_exporter_otlp_{signal}_protocol", protocol)
    monkeypatch.setattr(
        sdk.settings,
        f"otel_exporter_otlp_{signal}_endpoint",
        "http://collector:4318/v1/" + signal,
    )
    monkeypatch.setattr(
        sdk.settings,
        f"otel_exporter_otlp_{signal}_headers",
        "authorization=placeholder",
    )
    monkeypatch.setattr(sdk.settings, f"otel_exporter_otlp_{signal}_insecure", True)
    sdk._exporter(signal)
    factory = getattr(
        module,
        {
            "traces": "OTLPSpanExporter",
            "metrics": "OTLPMetricExporter",
            "logs": "OTLPLogExporter",
        }[signal],
    )
    options = factory.call_args.kwargs
    assert options["endpoint"] == "http://collector:4318/v1/" + signal
    assert options["headers"] == {"authorization": "placeholder"}
    assert options["timeout"] == 3
    assert ("insecure" in options) == (protocol == "grpc")


def test_exporter_rejects_invalid_protocol(monkeypatch):
    monkeypatch.setattr(sdk.settings, "otel_exporter_otlp_traces_protocol", "json")
    with pytest.raises(ValueError, match="protocol"):
        sdk._exporter("traces")


def test_parse_headers_preserves_base64_padding_and_decodes_names():
    assert sdk._parse_headers("Authorization=Basic dGVzdD0=,x%2Dscope%2Did=tenant") == {
        "authorization": "Basic dGVzdD0=",
        "x-scope-id": "tenant",
    }


def test_safe_span_export_drops_exceptions_and_payloads():
    target = InMemorySpanExporter()
    wrapper = sdk.SafeSpanExporter(target)
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(wrapper))
    with provider.get_tracer("test").start_as_current_span(
        "private@example.com"
    ) as span:
        span.set_attributes({"call_id": "call", "prompt": "private"})
        span.add_event("tool.result", {"outcome": "error", "result": "private"})
        span.add_event("private@example.com")
        span.record_exception(ValueError("private"))
        span.set_status(Status(StatusCode.ERROR, "private"))
    result = target.get_finished_spans()[0]
    assert result.name == "redacted.operation"
    assert dict(result.attributes) == {"call_id": "call"}
    assert result.status.description is None
    assert len(result.events) == 2
    assert result.events[1].name == "redacted.event"
    assert dict(result.events[0].attributes) == {"outcome": "error"}
    assert wrapper.force_flush()
    provider.shutdown()


def test_safe_logging_copies_original_record(monkeypatch):
    emit = Mock()
    monkeypatch.setattr(sdk.LoggingHandler, "emit", emit)
    handler = sdk.SafeLoggingHandler()
    record = logging.LogRecord(
        "application", 20, "", 1, "private %s", ("secret",), None
    )
    handler.emit(record)
    assert record.getMessage() == "private secret"
    exported = emit.call_args.args[0]
    assert exported.getMessage() == "application:INFO"
    emit.reset_mock()
    handler.emit(logging.LogRecord("opentelemetry.sdk", 40, "", 1, "private", (), None))
    emit.assert_not_called()


def test_setup_once_and_shutdown_all_providers(monkeypatch):
    monkeypatch.setattr(sdk, "_started", False)
    monkeypatch.setattr(sdk.settings, "otel_enabled", True)
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")
    exporters = [Mock(), Mock(), Mock()]
    monkeypatch.setattr(sdk, "_exporter", Mock(side_effect=exporters))
    for attr in [
        "TracerProvider",
        "LoggerProvider",
        "MeterProvider",
        "BatchSpanProcessor",
        "BatchLogRecordProcessor",
        "PeriodicExportingMetricReader",
        "SafeLoggingHandler",
    ]:
        monkeypatch.setattr(sdk, attr, Mock())
    monkeypatch.setattr(sdk.trace, "set_tracer_provider", Mock())
    monkeypatch.setattr(sdk.metrics, "set_meter_provider", Mock())
    root = Mock()
    monkeypatch.setattr(logging, "getLogger", lambda *args: root)
    for attr in ["tracer_provider", "logger_provider", "meter_provider", "_handler"]:
        monkeypatch.setattr(sdk, attr, None)
    sdk.setup_manual_opentelemetry("voice-ws")
    sdk.setup_opentelemetry()
    assert sdk._exporter.call_count == 3
    root.addHandler.assert_called_once()
    sdk.shutdown_opentelemetry()
    root.removeHandler.assert_called_once()
    for provider in [sdk.tracer_provider, sdk.logger_provider, sdk.meter_provider]:
        provider.shutdown.assert_called_once()


def test_setup_disabled_and_invalid_sampling(monkeypatch):
    monkeypatch.setattr(sdk, "_started", False)
    monkeypatch.setattr(sdk.settings, "otel_enabled", False)
    exporter = Mock()
    monkeypatch.setattr(sdk, "_exporter", exporter)
    sdk.setup_opentelemetry()
    exporter.assert_not_called()
    monkeypatch.setattr(sdk.settings, "otel_enabled", True)
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "2")
    with pytest.raises(ValueError):
        sdk.setup_opentelemetry()


def test_shutdown_without_initialization_is_safe(monkeypatch):
    for attr in ["tracer_provider", "logger_provider", "meter_provider", "_handler"]:
        monkeypatch.setattr(sdk, attr, None)
    sdk.shutdown_opentelemetry()


def test_partial_exporter_setup_is_cleaned(monkeypatch):
    monkeypatch.setattr(sdk, "_started", False)
    monkeypatch.setattr(sdk.settings, "otel_enabled", True)
    first = Mock()
    monkeypatch.setattr(
        sdk, "_exporter", Mock(side_effect=[first, ValueError("invalid")])
    )
    with pytest.raises(ValueError):
        sdk.setup_opentelemetry()
    first.shutdown.assert_called_once()


def test_legacy_helpers_and_instrument_cache(monkeypatch):
    from fastapi import FastAPI

    app = FastAPI()
    sdk.instrument_fastapi(app)
    sdk.instrument_fastapi(app)
    assert len(app.user_middleware) == 1
    log = Mock()
    monkeypatch.setattr(logging, "log", log)
    sdk.emit_log("failure", "ERROR", {"prompt": "private", "outcome": "error"})
    assert log.call_args.args[0] == logging.ERROR
    assert log.call_args.kwargs["extra"] == {"outcome": "error"}
    meter = Mock()
    monkeypatch.setattr(signals.metrics, "get_meter", lambda *args: meter)
    signals.instrument.cache_clear()
    for kind in ["counter", "histogram", "gauge"]:
        signals.record("test." + kind, kind=kind, call_id="secret", outcome="success")
        signals.record("test." + kind, kind=kind, outcome="error")
    meter.create_counter.assert_called_once()
    meter.create_histogram.assert_called_once()
    meter.create_up_down_counter.assert_called_once()
    sdk._counter.cache_clear()
    sdk.emit_metric("legacy", 1, {"call_id": "private", "outcome": "error"})
    assert meter.create_counter.return_value.add.call_args.args[1] == {
        "outcome": "error"
    }
    signals.instrument.cache_clear()
    sdk._counter.cache_clear()
