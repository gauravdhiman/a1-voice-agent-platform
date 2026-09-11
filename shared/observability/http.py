"""ASGI request correlation and safe RED telemetry, without URL/query capture."""

import time
import uuid

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.responses import JSONResponse

from .signals import correlation, event, instrument


class ObservabilityMiddleware:
    """Trace HTTP requests with route templates and server-generated request IDs.

    Incoming trace context is correlation only, never an authorization input.
    WebSocket query strings and HTTP bodies/headers are never recorded.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith("/health"):
            return await self.app(scope, receive, send)
        request_id = str(uuid.uuid4())
        token = correlation.set({"request_id": request_id})
        carrier = {
            k.decode(): v.decode("ascii", errors="ignore")
            for k, v in scope.get("headers", [])
            if k == b"traceparent" and len(v) == 55
        }
        parent = TraceContextTextMapPropagator().extract(carrier)
        started = time.monotonic()
        status = 500
        response_started = False
        with trace.get_tracer("247ai.http").start_as_current_span(
            "http.request",
            context=parent,
            kind=SpanKind.SERVER,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:

            async def response(message):
                nonlocal status, response_started
                if message["type"] == "http.response.start":
                    response_started = True
                    status = message["status"]
                    headers = list(message.get("headers", []))
                    headers.append((b"x-request-id", request_id.encode()))
                    ctx = span.get_span_context()
                    if ctx.is_valid:
                        headers.append((b"x-trace-id", f"{ctx.trace_id:032x}".encode()))
                    message = {**message, "headers": headers}
                await send(message)

            try:
                await self.app(scope, receive, response)
            except Exception as exc:
                span.set_attribute("error.type", type(exc).__name__)
                span.set_status(Status(StatusCode.ERROR))
                if not response_started:
                    await JSONResponse(
                        {"detail": "Internal server error", "requestId": request_id},
                        status_code=500,
                    )(scope, receive, response)
                raise
            finally:
                route = getattr(scope.get("route"), "path", "unmatched")
                method = scope.get("method", "OTHER")
                if method not in {
                    "GET",
                    "POST",
                    "PUT",
                    "PATCH",
                    "DELETE",
                    "HEAD",
                    "OPTIONS",
                }:
                    method = "OTHER"
                attributes = {
                    "http.route": route,
                    "http.request.method": method,
                    "http.response.status_code": status,
                }
                span.update_name(f"{method} {route}")
                span.set_attributes({**attributes, "request_id": request_id})
                if status >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                instrument("platform.http.requests").add(1, attributes)
                instrument("platform.http.duration", "histogram").record(
                    time.monotonic() - started, attributes
                )
                event("http.finished", **attributes)
                correlation.reset(token)
