"""Operational telemetry privacy, errors and concurrency contracts."""

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from shared.observability import signals
from shared.observability.health import Readiness
from shared.observability.http import ObservabilityMiddleware
from shared.observability.privacy import TelemetryLogFilter, safe_attributes
from shared.observability.voice import (
    annotate_speech_configuration,
    observe_call,
    observe_tool,
)


@pytest.fixture
def telemetry(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(trace, "get_tracer", provider.get_tracer)
    instruments = {}
    monkeypatch.setattr(
        signals,
        "instrument",
        lambda n, k="counter": instruments.setdefault((n, k), Mock()),
    )
    yield exporter, instruments
    provider.shutdown()


def test_attribute_allowlist():
    assert safe_attributes(
        {
            "call_id": "abc-123",
            "tokens": 2,
            "bytes": 3.5,
            "outcome": True,
            "prompt": "private",
            "tool": ["x"],
            "model": "x" * 200,
            "session_id": "a@example.com",
            "duration_ms": float("nan"),
            "sequence": float("inf"),
        }
    ) == {"call_id": "abc-123", "tokens": 2, "bytes": 3.5, "outcome": True}
    assert safe_attributes(None) == {}


def test_speech_configuration_metadata_is_content_free(telemetry):
    """A call trace records the selected providers without model payloads."""
    with signals.operation("voice.setup"):
        annotate_speech_configuration(
            SimpleNamespace(
                stt=SimpleNamespace(provider="deepgram", model="nova-3"),
                llm=SimpleNamespace(provider="openai", model="gpt-4.1"),
                tts=SimpleNamespace(provider="cartesia", model="sonic-3"),
            )
        )

    span = telemetry[0].get_finished_spans()[0]
    configuration = [event for event in span.events if event.name == "ai.configuration"]
    assert [event.attributes["stage"] for event in configuration] == [
        "stt",
        "llm",
        "tts",
    ]
    assert configuration[0].attributes["provider"] == "deepgram"
    assert configuration[1].attributes["model"] == "gpt-4.1"
    assert all(
        "prompt" not in event.attributes
        and "arguments" not in event.attributes
        and "result" not in event.attributes
        for event in configuration
    )


def test_realtime_speech_configuration_uses_default_model(telemetry):
    """Realtime traces keep one bounded provider/model event."""
    with signals.operation("voice.setup"):
        annotate_speech_configuration(
            SimpleNamespace(provider="google", model=None, params={"secret": "x"})
        )
    span = telemetry[0].get_finished_spans()[0]
    configuration = [event for event in span.events if event.name == "ai.configuration"]
    assert len(configuration) == 1
    assert configuration[0].attributes["stage"] == "realtime"
    assert configuration[0].attributes["model"] == "default"


def test_legacy_log_payload_is_removed():
    rec = logging.LogRecord(
        "provider",
        logging.ERROR,
        "",
        1,
        "secret %s",
        ("token",),
        (ValueError, ValueError("PII"), None),
    )
    rec.authorization = "private"
    rec.__dict__["event.name"] = "tool.failed"
    rec.session_id = "session"
    assert TelemetryLogFilter().filter(rec)
    assert rec.getMessage() == "tool.failed"
    assert rec.exc_info is None
    assert rec.__dict__["error.type"] == "ValueError"
    assert "authorization" not in rec.__dict__
    assert rec.session_id == "session"
    assert not TelemetryLogFilter().filter(
        logging.LogRecord("opentelemetry.exporter", 40, "", 1, "failure", (), None)
    )


@pytest.mark.parametrize("failure", [None, ValueError, asyncio.CancelledError])
def test_operation_preserves_errors_and_records_outcome(telemetry, failure):
    if failure:
        with pytest.raises(failure):
            with signals.operation("test.operation", call_id="call", prompt="private"):
                raise failure("private")
    else:
        with signals.operation("test.operation"):
            pass
    span = telemetry[0].get_finished_spans()[-1]
    assert span.attributes["outcome"] == (
        "success"
        if failure is None
        else "cancelled" if failure is asyncio.CancelledError else "error"
    )
    assert "private" not in str(span.attributes)
    assert all(e.name != "exception" for e in span.events)
    assert ("platform.operation.duration", "histogram") in telemetry[1]


@pytest.mark.asyncio
async def test_http_route_template_and_server_request_id(telemetry):
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/items/{item_id}")
    async def item(item_id: str):
        return {"ok": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        result = await client.get(
            "/items/private?token=secret",
            headers={
                "x-request-id": "attacker",
                "traceparent": (
                    "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
                ),
            },
        )
        assert result.status_code == 200
        assert result.headers["x-request-id"] != "attacker"
        assert result.headers["x-trace-id"] == "0123456789abcdef0123456789abcdef"
        await client.get("/unknown-secret")
        await client.get("/health/live")
    spans = telemetry[0].get_finished_spans()
    assert [s.name for s in spans] == ["GET /items/{item_id}", "GET unmatched"]
    assert "private" not in str([dict(s.attributes) for s in spans])
    assert signals.correlation.get() == {}


@pytest.mark.asyncio
async def test_http_failure_does_not_export_exception_message(telemetry):
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/fail")
    async def fail():
        raise ValueError("secret")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/fail")
        assert response.status_code == 500
        assert response.headers["x-request-id"] == response.json()["requestId"]
    span = telemetry[0].get_finished_spans()[-1]
    assert span.attributes["error.type"] == "ValueError"
    assert span.attributes["http.response.status_code"] == 500
    assert signals.correlation.get() == {}


@pytest.mark.asyncio
async def test_stream_failure_preserves_started_response_and_marks_trace(telemetry):
    async def stream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("private stream content")

    send = AsyncMock()
    with pytest.raises(RuntimeError):
        await ObservabilityMiddleware(stream)(
            {"type": "http", "path": "/stream", "method": "CUSTOM"},
            AsyncMock(),
            send,
        )
    assert send.await_count == 1
    span = telemetry[0].get_finished_spans()[-1]
    assert span.status.status_code.name == "ERROR"
    assert span.attributes["http.request.method"] == "OTHER"
    assert span.attributes["http.response.status_code"] == 200
    assert signals.correlation.get() == {}


@pytest.mark.asyncio
async def test_disabled_tracing_still_returns_request_id(monkeypatch):
    monkeypatch.setattr(trace, "get_tracer", lambda *a, **k: trace.NoOpTracer())
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/missing")
    assert response.headers["x-request-id"]
    assert "x-trace-id" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, ValueError, asyncio.CancelledError])
async def test_call_cleanup_and_parent_trace(telemetry, failure):
    @observe_call
    async def call(ws, claims):
        assert signals.correlation.get()["session_id"] == "session"
        assert signals.correlation.get()["session.id"] == "session"
        if failure:
            raise failure("secret")
        return 42

    claims = SimpleNamespace(
        purpose="public",
        session_id="session",
        agent_id="agent",
        traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
    )
    if failure:
        with pytest.raises(failure):
            await call(None, claims)
    else:
        assert await call(None, claims) == 42
    assert signals.correlation.get() == {}
    active = telemetry[1][("platform.voice.active", "gauge")]
    assert [c.args[0] for c in active.add.call_args_list] == [1, -1]
    span = telemetry[0].get_finished_spans()[-1]
    assert f"{span.context.trace_id:032x}" == "0123456789abcdef0123456789abcdef"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result,failed",
    [
        ("ok", False),
        ('{"success":true}', False),
        ('{"error":"private"}', True),
        ("MCP tool error: private", True),
        ({"status": "failed"}, True),
        ({"success": False}, True),
        (["private"], False),
        ({"status": ["unexpected"]}, False),
        ({"status": {"unexpected": True}}, False),
    ],
)
async def test_tool_caught_failure_and_callback_preserved(telemetry, result, failed):
    callback = AsyncMock()
    params = SimpleNamespace(arguments={"secret": "private"}, result_callback=callback)

    async def handler(forwarded):
        assert forwarded.arguments is params.arguments
        await forwarded.result_callback(result)

    await observe_tool("test_tool", handler)(params)
    callback.assert_awaited_once_with(result)
    assert params.result_callback is callback
    span = telemetry[0].get_finished_spans()[-1]
    assert span.attributes["outcome"] == ("error" if failed else "success")
    assert "private" not in str(span.attributes)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 401, 503, "timeout"])
async def test_readiness_cache_and_safe_status(monkeypatch, status):
    requests = []

    async def get(self, *args, **kwargs):
        requests.append(args)
        await asyncio.sleep(0)
        if status == "timeout":
            raise httpx.ReadTimeout("private")
        return httpx.Response(status)

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    readiness = Readiness(
        SimpleNamespace(supabase_url="https://db.test", supabase_service_key="secret")
    )
    results = await asyncio.gather(*(readiness.response() for _ in range(10)))
    assert len(requests) == 1
    assert all(r.status_code == (200 if status == 200 else 503) for r in results)
    assert all(b"secret" not in r.body for r in results)


@pytest.mark.asyncio
async def test_tool_raised_failure_is_counted_and_propagated(telemetry):
    async def handler(params):
        raise TimeoutError("private provider response")

    with pytest.raises(TimeoutError):
        await observe_tool("test_tool", handler)(
            SimpleNamespace(result_callback=AsyncMock())
        )
    attributes = telemetry[1][
        ("platform.operation.count", "counter")
    ].add.call_args.args[1]
    assert attributes == {"operation": "tool.execute", "outcome": "error"}
    assert "private" not in str(telemetry[0].get_finished_spans()[-1].attributes)


@pytest.mark.asyncio
async def test_readiness_missing_configuration():
    readiness = Readiness(SimpleNamespace(supabase_url=None, supabase_service_key=None))
    assert (await readiness.response()).status_code == 503


@pytest.mark.asyncio
async def test_caught_failure_metrics_when_tracing_disabled(monkeypatch):
    monkeypatch.setattr(trace, "get_tracer", lambda *args, **kwargs: trace.NoOpTracer())
    instruments = {}
    monkeypatch.setattr(
        signals,
        "instrument",
        lambda n, k="counter": instruments.setdefault((n, k), Mock()),
    )

    @signals.observed("billing.settle")
    async def settle():
        signals.failure("BILLING_DEBIT_FAILED")

    await settle()
    assert (
        instruments[("platform.operation.count", "counter")].add.call_args.args[1][
            "outcome"
        ]
        == "error"
    )
    assert signals.operation_state.get() is None
    callback = AsyncMock()

    async def handler(params):
        await params.result_callback({"error": "private"})

    await observe_tool("example", handler)(SimpleNamespace(result_callback=callback))
    assert (
        instruments[("platform.operation.count", "counter")].add.call_args.args[1][
            "outcome"
        ]
        == "error"
    )


@pytest.mark.asyncio
async def test_concurrent_calls_do_not_share_correlation(telemetry):
    @observe_call
    async def call(ws, claims):
        await asyncio.sleep(0)
        signals.event("concurrent.event")

    await asyncio.gather(
        *(
            call(
                None,
                SimpleNamespace(purpose="public", session_id=str(i), agent_id="agent"),
            )
            for i in range(10)
        )
    )
    spans = telemetry[0].get_finished_spans()
    assert len(spans) == 10
    for span in spans:
        assert all(
            e.attributes["session_id"] == span.attributes["session_id"]
            for e in span.events
        )
        assert span.attributes["session.id"] == span.attributes["session_id"]
    assert signals.correlation.get() == {}
