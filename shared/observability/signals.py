"""Low-cardinality metrics and correlated diagnostic events without payloads."""

import asyncio
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from .privacy import safe_attributes

correlation: ContextVar[dict] = ContextVar("telemetry_correlation", default={})
operation_state: ContextVar[dict | None] = ContextVar(
    "telemetry_operation_state", default=None
)

METRIC_FIELDS = {"operation", "outcome", "channel", "stage", "provider", "token.type"}
logger = logging.getLogger("platform.events")


@lru_cache(maxsize=64)
def instrument(name: str, kind: str = "counter"):
    """Cache instruments; callers use fixed names and bounded label vocabularies."""
    meter = metrics.get_meter("247ai.operations")
    if kind == "histogram":
        return meter.create_histogram(name, unit="s")
    if kind == "gauge":
        return meter.create_up_down_counter(name)
    return meter.create_counter(name)


def record(name: str, value: float = 1, *, kind: str = "counter", **labels) -> None:
    """Record a metric without tenant, call, route, model or arbitrary tool labels."""
    attributes = {
        k: v for k, v in safe_attributes(labels).items() if k in METRIC_FIELDS
    }
    metric = instrument(name, kind)
    if kind == "histogram":
        metric.record(value, attributes)
    else:
        metric.add(value, attributes)


def event(name: str, **fields) -> None:
    """Emit a correlated, content-free event as both log and span event."""
    attributes = safe_attributes({**correlation.get(), **fields, "event.name": name})
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        attributes.update(
            trace_id=f"{ctx.trace_id:032x}", span_id=f"{ctx.span_id:016x}"
        )
    span.add_event(name, attributes)
    logger.info(name, extra=attributes)


@contextmanager
def operation(name: str, **fields):
    """Measure an operation; propagate exceptions while exporting only their type."""
    started = time.monotonic()
    outcome = "success"
    state = {"failed": False}
    state_token = operation_state.set(state)
    attributes = safe_attributes({**correlation.get(), **fields, "operation": name})
    with trace.get_tracer("247ai.operations").start_as_current_span(
        name,
        attributes=attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except asyncio.CancelledError:
            outcome = "cancelled"
            span.set_attribute("outcome", outcome)
            raise
        except Exception as exc:
            outcome = "error"
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(Status(StatusCode.ERROR))
            raise
        finally:
            status = getattr(span, "status", None)
            if state["failed"] or (status and status.status_code == StatusCode.ERROR):
                outcome = "error"
            duration = time.monotonic() - started
            span.set_attribute("outcome", outcome)
            record("platform.operation.count", operation=name, outcome=outcome)
            record(
                "platform.operation.duration",
                duration,
                kind="histogram",
                operation=name,
                outcome=outcome,
            )
            event(
                "operation.finished",
                operation=name,
                outcome=outcome,
                duration_ms=duration * 1000,
            )
            operation_state.reset(state_token)


def observed(name: str):
    """Decorate an async service operation while preserving its signature."""
    from functools import wraps

    def decorate(function):
        @wraps(function)
        async def wrapped(*args, **kwargs):
            with operation(name):
                return await function(*args, **kwargs)

        return wrapped

    return decorate


def failure(code: str) -> None:
    """Mark a caught operational failure without changing business recovery behavior."""
    state = operation_state.get()
    if state is not None:
        state["failed"] = True
    span = trace.get_current_span()
    span.set_status(Status(StatusCode.ERROR))
    span.set_attribute("failure_code", code)
    event("operation.failed", failure_code=code, outcome="error")
