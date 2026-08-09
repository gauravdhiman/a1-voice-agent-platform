"""Regression tests for voice-worker OpenTelemetry instrumentation dependencies."""


def test_requests_instrumentor_dependency_is_available():
    """The worker image includes the instrumentation imported at startup."""
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    assert RequestsInstrumentor is not None
