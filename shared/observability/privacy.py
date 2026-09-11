"""Allowlisted telemetry fields; never export conversation or provider payloads."""

import logging
import math
import re
from collections.abc import Mapping
from pathlib import Path

SAFE_FIELDS = frozenset(
    {
        "service.name",
        "service.version",
        "deployment.environment.name",
        "request_id",
        "session_id",
        "session.id",
        "call_id",
        "agent_id",
        "organization_id",
        "channel",
        "operation",
        "outcome",
        "failure_code",
        "error.type",
        "http.request.method",
        "http.response.status_code",
        "http.route",
        "provider",
        "model",
        "tool",
        "stage",
        "token.type",
        "event.name",
        "duration_ms",
        "bytes",
        "tokens",
        "sequence",
        "trace_id",
        "span_id",
    }
)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:/{} -]{1,160}$")


def safe_attributes(attributes: Mapping | None) -> dict:
    """Keep bounded operational scalars only; unknown fields fail closed."""
    result = {}
    for key, value in (attributes or {}).items():
        if key not in SAFE_FIELDS:
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if isinstance(value, (bool, int, float)):
            result[key] = value
        elif isinstance(value, str) and _IDENTIFIER.fullmatch(value):
            result[key] = value
    return result


class TelemetryLogFilter(logging.Filter):
    """Export safe event names or log templates, never arguments or exceptions.

    Legacy free-form messages are replaced by logger + level. New diagnostic
    events use the explicitly allowlisted ``event.name`` and scalar fields.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith(("opentelemetry", "grpc", "urllib3")):
            return False  # Avoid exporter feedback loops.
        fields = safe_attributes(record.__dict__)
        if record.exc_info:
            fields["error.type"] = record.exc_info[0].__name__
        standard = logging.LogRecord("", 0, "", 0, "", (), None).__dict__
        for key in list(record.__dict__):
            if key not in standard:
                del record.__dict__[key]
        record.__dict__.update(fields)
        record.msg = fields.get("event.name", f"{record.name}:{record.levelname}")
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        record.pathname = Path(record.pathname).name
        return True
