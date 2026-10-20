"""Console logs must have the same privacy boundary even when OTLP is off."""

import io
import logging

from shared.observability.privacy import protect_console_logs


def test_console_suppresses_pii_tokens_and_exception_payloads(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr("shared.observability.privacy.sys.stderr", stream)
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("readiness.privacy.test")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        protect_console_logs()
        protect_console_logs()
        assert len(handler.filters) == 1
        try:
            raise ValueError("provider token=secret-value")
        except ValueError:
            logger.exception(
                "Email user@example.test from +15555550100 /ws?token=secret-value"
            )
        output = stream.getvalue()
        assert "readiness.privacy.test:ERROR" in output
        for value in ["user@example", "+1555", "secret-value", "Traceback"]:
            assert value not in output
    finally:
        logger.removeHandler(handler)


def test_uvicorn_access_formatter_remains_usable_after_redaction(monkeypatch):
    from uvicorn.logging import AccessFormatter

    stream = io.StringIO()
    monkeypatch.setattr("shared.observability.privacy.sys.stderr", stream)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(AccessFormatter())
    logger = logging.getLogger("uvicorn.access")
    old_handlers, old_propagate, old_level = (
        logger.handlers,
        logger.propagate,
        logger.level,
    )
    logger.handlers, logger.propagate = [handler], False
    logger.setLevel(logging.INFO)
    try:
        protect_console_logs()
        logger.info(
            '%s - "%s %s HTTP/%s" %d',
            "127.0.0.1",
            "GET",
            "/ws?token=secret",
            "1.1",
            101,
        )
        assert "uvicorn.access:INFO" in stream.getvalue()
        assert "secret" not in stream.getvalue()
    finally:
        logger.handlers, logger.propagate, logger.level = (
            old_handlers,
            old_propagate,
            old_level,
        )
