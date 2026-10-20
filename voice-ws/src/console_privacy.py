"""Content-free console logging for Pipecat's separate Loguru runtime."""

import sys

from loguru import logger

from shared.observability.privacy import safe_attributes


def protect_loguru_logs() -> None:
    """Replace voice-provider sinks with a content-free console boundary.

    Pipecat uses Loguru independently of standard logging. Call at voice-worker
    startup, before accepting sessions; repeated initialization replaces the
    sink without duplicate output. Loguru is owned by the voice runtime.
    """

    def redact(record: dict) -> bool:
        fields = safe_attributes(record["extra"])
        exception = record["exception"]
        if exception is not None:
            fields["error.type"] = exception.type.__name__
        record["extra"] = fields
        record["message"] = fields.get(
            "event.name", f"{record['name']}:{record['level'].name}"
        )
        record["exception"] = None
        return True

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} {level} [{name}] {message}",
        filter=redact,
        backtrace=False,
        diagnose=False,
    )
