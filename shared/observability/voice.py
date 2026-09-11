"""Session and tool instrumentation independent of any speech vendor."""

import asyncio
import copy
import json
import time
from functools import wraps

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .signals import correlation, event, failure, operation, operation_state, record


def annotate_speech_configuration(config) -> None:
    """Attach safe provider/model metadata to the active call trace.

    The metadata makes a call trace useful in an AI-observability backend while
    keeping prompts, provider parameters, credentials, and conversation text
    out of telemetry. Pipeline configurations produce one event per stage;
    realtime configurations produce one event for the end-to-end provider.

    Args:
        config: A resolved realtime or pipeline speech configuration.
    """

    stages = ("stt", "llm", "tts")
    if all(getattr(config, stage, None) is not None for stage in stages):
        for stage in stages:
            stage_config = getattr(config, stage)
            event(
                "ai.configuration",
                stage=stage,
                provider=getattr(stage_config, "provider", "unknown"),
                model=getattr(stage_config, "model", None) or "default",
            )
        return

    event(
        "ai.configuration",
        stage="realtime",
        provider=getattr(config, "provider", "unknown"),
        model=getattr(config, "model", None) or "default",
    )


def observe_call(function):
    """Keep one trace and correlation context through setup, audio and cleanup."""

    @wraps(function)
    async def wrapped(websocket, claims, **kwargs):
        channel = (
            claims.purpose
            if claims.purpose in {"test_call", "embed", "public", "phone"}
            else "unknown"
        )
        token = correlation.set(
            {
                "session_id": claims.session_id,
                # Langfuse maps the standard session.id attribute to its
                # session filter. Keep the legacy dashboard field as well.
                "session.id": claims.session_id,
                "agent_id": claims.agent_id,
                "channel": channel,
            }
        )
        parent = TraceContextTextMapPropagator().extract(
            {"traceparent": getattr(claims, "traceparent", None) or ""}
        )
        started = time.monotonic()
        outcome = "success"
        state = {"failed": False}
        state_token = operation_state.set(state)
        record("platform.voice.active", 1, kind="gauge", channel=channel)
        try:
            with trace.get_tracer("247ai.voice").start_as_current_span(
                "voice.call",
                context=parent,
                attributes=correlation.get(),
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                event("call.started")
                try:
                    return await function(websocket, claims, **kwargs)
                except asyncio.CancelledError:
                    outcome = "cancelled"
                    raise
                except Exception as exc:
                    outcome = "error"
                    span.set_status(Status(StatusCode.ERROR))
                    event("call.failed", **{"error.type": type(exc).__name__})
                    raise
                finally:
                    status = getattr(span, "status", None)
                    if state["failed"] or (
                        status and status.status_code == StatusCode.ERROR
                    ):
                        outcome = "error"
                    span.set_attribute("outcome", outcome)
                    event("call.finished", outcome=outcome)
        finally:
            record("platform.voice.active", -1, kind="gauge", channel=channel)
            record("platform.voice.calls", channel=channel, outcome=outcome)
            record(
                "platform.voice.duration",
                time.monotonic() - started,
                kind="histogram",
                channel=channel,
                outcome=outcome,
            )
            correlation.reset(token)
            operation_state.reset(state_token)

    return wrapped


def observe_tool(name, handler):
    """Trace handlers and caught errors without retaining tool arguments/results."""

    @wraps(handler)
    async def wrapped(params):
        with operation("tool.execute", tool=name):

            async def result_callback(result, *args, **kwargs):
                value = result
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (ValueError, TypeError):
                        value = (
                            {"error": True}
                            if value.startswith("MCP tool error:")
                            else {}
                        )
                failed = isinstance(value, dict) and (
                    bool(value.get("error"))
                    or value.get("success") is False
                    or value.get("status") in ("error", "failed")
                )
                outcome = "error" if failed else "success"
                if failed:
                    failure("TOOL_EXECUTION_FAILED")
                record("platform.tool.results", outcome=outcome)
                event("tool.result", tool=name, outcome=outcome)
                await params.result_callback(result, *args, **kwargs)

            forwarded = copy.copy(params)
            forwarded.result_callback = result_callback
            await handler(forwarded)

    return wrapped
