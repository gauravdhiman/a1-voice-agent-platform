"""Pipecat's separate Loguru sinks must not expose conversation payloads."""

import io

from loguru import logger

from shared.observability import privacy


def test_provider_console_is_content_free_and_idempotent(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr(privacy.sys, "stderr", stream)
    try:
        privacy.protect_loguru_logs()
        privacy.protect_loguru_logs()
        logger.bind(transcript="private conversation", token="secret-value").info(
            "User user@example.test says private conversation /ws?token=secret-value"
        )
        try:
            raise ValueError("provider token=secret-value")
        except ValueError:
            logger.exception("Provider response contains private conversation")
        output = stream.getvalue()
        assert output.count(":INFO") == 1
        assert output.count(":ERROR") == 1
        for value in [
            "user@example",
            "secret-value",
            "private conversation",
            "Traceback",
        ]:
            assert value not in output
    finally:
        logger.remove()


def test_provider_console_preserves_only_allowlisted_event_fields(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr(privacy.sys, "stderr", stream)
    try:
        privacy.protect_loguru_logs()
        logger.bind(**{"event.name": "voice.provider.failed", "token": "secret"}).error(
            "private provider response"
        )
        output = stream.getvalue()
        assert "voice.provider.failed" in output
        assert "secret" not in output
        assert "private provider response" not in output
    finally:
        logger.remove()
