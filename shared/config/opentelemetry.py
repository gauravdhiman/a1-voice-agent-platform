"""Process-scoped OTLP lifecycle with bounded queues and content-free exports."""

import copy
import logging
import os
from functools import lru_cache
from threading import Lock
from urllib.parse import unquote

from opentelemetry import metrics, trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Status

from shared.observability.privacy import (
    TelemetryLogFilter,
    protect_console_logs,
    safe_attributes,
)

from . import settings

logging_level = logging.INFO
tracer_provider = None
logger_provider = None
meter_provider = None
_handler = None
_lock = Lock()
_started = False


class SafeSpanExporter(SpanExporter):
    """Apply an export boundary to legacy spans, dropping arbitrary exception text."""

    def __init__(self, exporter):
        self.exporter = exporter

    def export(self, spans):
        clean = []
        for span in spans:
            item = copy.copy(span)
            item._name = safe_attributes({"operation": span.name}).get(
                "operation", "redacted.operation"
            )
            item._attributes = safe_attributes(span.attributes)
            item._events = tuple(
                Event(
                    safe_attributes({"event.name": event.name}).get(
                        "event.name", "redacted.event"
                    ),
                    attributes=safe_attributes(event.attributes),
                    timestamp=event.timestamp,
                )
                for event in span.events
                if event.name != "exception"
            )
            item._status = Status(span.status.status_code)
            clean.append(item)
        return self.exporter.export(clean)

    def shutdown(self):
        self.exporter.shutdown()

    def force_flush(self, timeout_millis=30000):
        return self.exporter.force_flush(timeout_millis)


class SafeLoggingHandler(LoggingHandler):
    """Sanitize a copy so unrelated console handlers retain their own record."""

    def emit(self, record):
        clean = copy.copy(record)
        if TelemetryLogFilter().filter(clean):
            super().emit(clean)


def get_resource(app_name: str = "247ai-backend"):
    """Identify service, release and environment without host/user detection."""
    return Resource(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", app_name),
            "service.version": os.getenv("OTEL_SERVICE_VERSION", settings.app_version),
            "deployment.environment.name": settings.environment,
        }
    )


def _exporter(signal):
    """Build the explicitly configured HTTP/protobuf or gRPC signal exporter."""
    from importlib import import_module

    protocol = getattr(settings, f"otel_exporter_otlp_{signal}_protocol")
    if protocol not in {"grpc", "http/protobuf"}:
        raise ValueError("Unsupported OTLP protocol")
    suffix = {
        "traces": "trace_exporter",
        "metrics": "metric_exporter",
        "logs": "_log_exporter",
    }[signal]
    class_name = {
        "traces": "OTLPSpanExporter",
        "metrics": "OTLPMetricExporter",
        "logs": "OTLPLogExporter",
    }[signal]
    module = import_module(
        "opentelemetry.exporter.otlp.proto."
        f"{'grpc' if protocol == 'grpc' else 'http'}.{suffix}"
    )
    kwargs = {"timeout": 3}
    endpoint = getattr(settings, f"otel_exporter_otlp_{signal}_endpoint")
    if endpoint:
        kwargs["endpoint"] = endpoint
    headers = _parse_headers(getattr(settings, f"otel_exporter_otlp_{signal}_headers"))
    if headers:
        kwargs["headers"] = headers
    if protocol == "grpc":
        kwargs["insecure"] = getattr(settings, f"otel_exporter_otlp_{signal}_insecure")
    return getattr(module, class_name)(**kwargs)


def _parse_headers(value: str | None) -> dict[str, str]:
    """Parse the OTEL ``name=value,name2=value2`` header format.

    HTTP exporters require a mapping while the environment variable is a
    string. Split only on the first equals sign so base64 credentials with
    padding remain intact, and accept the URL-encoded form from the OTel spec.
    Invalid entries are ignored rather than becoming an accidental header.
    """
    headers: dict[str, str] = {}
    for item in (value or "").split(","):
        name, separator, header_value = item.partition("=")
        name = unquote(name).strip().lower()
        if not separator or not name:
            continue
        headers[name] = unquote(header_value).strip()
    return headers


def setup_opentelemetry(app_name: str = "247ai-backend"):
    """Initialize once per process. Invalid enabled configuration fails startup."""
    global tracer_provider, logger_provider, meter_provider, _handler, _started
    protect_console_logs()
    if not settings.otel_enabled:
        return
    with _lock:
        if _started:
            return
        ratio = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))
        if not 0 <= ratio <= 1:
            raise ValueError("OTEL_TRACES_SAMPLER_ARG must be between 0 and 1")
        resource = get_resource(app_name)
        # Validate exporters before registering any irreversible global providers.
        exporters = []
        try:
            for signal in ("traces", "logs", "metrics"):
                exporters.append(_exporter(signal))
        except Exception:
            for exporter in exporters:
                exporter.shutdown()
            raise
        tracer_provider = TracerProvider(
            resource=resource, sampler=ParentBased(TraceIdRatioBased(ratio))
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                SafeSpanExporter(exporters[0]),
                max_queue_size=2048,
                max_export_batch_size=256,
                schedule_delay_millis=1000,
            )
        )
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                exporters[1],
                max_queue_size=2048,
                max_export_batch_size=256,
                schedule_delay_millis=1000,
            )
        )
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    exporters[2],
                    export_interval_millis=15000,
                    export_timeout_millis=3000,
                )
            ],
        )
        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(meter_provider)
        _handler = SafeLoggingHandler(
            level=logging_level, logger_provider=logger_provider
        )
        logging.getLogger().addHandler(_handler)
        _started = True


def setup_manual_opentelemetry(app_name: str = "247ai-backend"):
    """Backward-compatible entry point for manual SDK setup."""
    setup_opentelemetry(app_name)


def shutdown_opentelemetry():
    """Flush on service shutdown, outside request/audio processing threads."""
    if _handler is not None:
        logging.getLogger().removeHandler(_handler)
    for provider in (meter_provider, logger_provider, tracer_provider):
        if provider is not None:
            provider.shutdown()


def instrument_fastapi(app):
    """Install safe HTTP instrumentation once, excluding health and WS payloads."""
    from shared.observability.http import ObservabilityMiddleware

    if not getattr(app.state, "observability_installed", False):
        app.add_middleware(ObservabilityMiddleware)
        app.state.observability_installed = True


def emit_log(message: str, level: str = "INFO", attributes: dict = None):
    """Legacy log helper preserving severity; export filters suppress raw messages."""
    logging.log(
        getattr(logging, level.upper(), logging.INFO),
        message,
        extra=safe_attributes(attributes),
    )


@lru_cache(maxsize=128)
def _counter(name):
    return metrics.get_meter("247ai.legacy").create_counter(name)


def emit_metric(name: str, value: float, attributes: dict = None):
    """Legacy counter helper; exclude identity and unbounded attribute values."""
    from shared.observability.signals import METRIC_FIELDS

    _counter(name).add(
        value,
        {k: v for k, v in safe_attributes(attributes).items() if k in METRIC_FIELDS},
    )
