"""Deterministic checks for model-generated tool-call traces.

Trace evaluation is intentionally separate from live model execution.  A
provider adapter can emit this small JSON contract, after which the same rules
can be applied in CI, offline replay, and production incident analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


_DATETIME_ARGUMENT_NAMES = {
    "start_time",
    "new_start_time",
    "window_start",
    "window_end",
}
_SUCCESS_WORDS = (
    "booked",
    "scheduled",
    "updated",
    "rescheduled",
    "cancelled",
    "canceled",
    "available",
)


@dataclass
class TraceEvaluation:
    """Outcome of evaluating one model/tool trace."""

    scenario_id: str
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return whether no trace rule was violated."""
        return not self.failures

    @property
    def score(self) -> float:
        """Return a simple rule score for trend reporting."""
        total = len(self.checks) + len(self.failures)
        return 1.0 if total == 0 else len(self.checks) / total

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trace outcome."""
        return {
            "scenario_id": self.scenario_id,
            "passed": self.passed,
            "score": self.score,
            "checks": list(self.checks),
            "failures": list(self.failures),
        }


def _is_timezone_aware(value: Any) -> bool:
    """Return whether a value is an ISO datetime with an explicit offset."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _walk_datetime_arguments(value: Any, path: str = "") -> list[tuple[str, Any]]:
    """Find scheduling datetime arguments in nested model payloads."""
    found: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            if key in _DATETIME_ARGUMENT_NAMES:
                found.append((item_path, item))
            found.extend(_walk_datetime_arguments(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_datetime_arguments(item, f"{path}[{index}]"))
    return found


def _matches_json_type(value: Any, expected_type: str) -> bool:
    """Check the primitive JSON Schema types used by function arguments."""
    return {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, Mapping),
        "null": value is None,
    }.get(expected_type, True)


def _validate_schema_arguments(
    tool_name: str, arguments: Any, schema: Mapping[str, Any]
) -> list[str]:
    """Return argument-schema violations for one model tool call."""
    if not isinstance(arguments, Mapping):
        return [f"schema violation for {tool_name}: arguments must be an object"]
    schema = schema.get("input_schema", schema)
    if not isinstance(schema, Mapping):
        return [f"schema violation for {tool_name}: schema must be an object"]
    violations: list[str] = []
    properties = schema.get("properties")
    properties = properties if isinstance(properties, Mapping) else {}
    for required in schema.get("required", []) or []:
        if required not in arguments:
            violations.append(
                f"schema violation for {tool_name}: missing required argument '{required}'"
            )
    for name, value in arguments.items():
        property_schema = properties.get(name)
        if not isinstance(property_schema, Mapping):
            continue
        expected_type = property_schema.get("type")
        if isinstance(expected_type, str) and not _matches_json_type(
            value, expected_type
        ):
            violations.append(
                f"schema violation for {tool_name}: argument '{name}' "
                f"must be {expected_type}"
            )
    return violations


def evaluate_trace(trace: Mapping[str, Any]) -> TraceEvaluation:
    """Evaluate a model/tool trace against generic safety contracts.

    The accepted trace shape is a mapping with ``scenario_id`` and an ordered
    ``events`` list.  Events have ``type`` values ``tool_call``, ``tool_result``,
    ``assistant``, or ``user``.  Optional scenario keys are
    ``expected_tool_sequence`` and ``forbidden_tools``.

    The evaluator checks that scheduling datetimes include offsets, expected
    tools appear in order, forbidden tools are absent, and an assistant does not
    claim a mutation succeeded after the matching tool returned an error or no
    result.
    """
    scenario_id = str(trace.get("scenario_id") or "unnamed-trace")
    evaluation = TraceEvaluation(scenario_id=scenario_id)
    events = trace.get("events")
    if not isinstance(events, list):
        evaluation.failures.append("trace events must be a list")
        return evaluation

    tool_calls = [
        event
        for event in events
        if isinstance(event, Mapping) and event.get("type") == "tool_call"
    ]
    tool_names = [str(event.get("name") or "") for event in tool_calls]
    forbidden = {str(name) for name in trace.get("forbidden_tools", []) or []}
    for tool_name in tool_names:
        if tool_name in forbidden:
            evaluation.failures.append(f"forbidden tool was called: {tool_name}")
        else:
            evaluation.checks.append(f"tool allowed: {tool_name}")

    expected_sequence = [
        str(name) for name in trace.get("expected_tool_sequence", []) or []
    ]
    cursor = 0
    for expected_name in expected_sequence:
        try:
            cursor = tool_names.index(expected_name, cursor) + 1
        except ValueError:
            evaluation.failures.append(
                f"expected tool '{expected_name}' was not called in order"
            )
            break
            evaluation.checks.append(f"expected tool called: {expected_name}")

    tool_schemas = trace.get("tool_schemas")
    if tool_schemas is not None and not isinstance(tool_schemas, Mapping):
        evaluation.failures.append("tool_schemas must be an object")

    pending_tools: list[str] = []
    last_tool_result: Mapping[str, Any] | None = None
    last_tool_name = ""
    for event in events:
        if not isinstance(event, Mapping):
            evaluation.failures.append("trace contains a non-object event")
            continue
        event_type = event.get("type")
        if event_type == "tool_call":
            name = str(event.get("name") or "")
            arguments = event.get("arguments", {})
            if isinstance(tool_schemas, Mapping):
                schema = tool_schemas.get(name)
                if isinstance(schema, Mapping):
                    schema_failures = _validate_schema_arguments(
                        name, arguments, schema
                    )
                    evaluation.failures.extend(schema_failures)
                    if not schema_failures:
                        evaluation.checks.append(f"schema arguments valid: {name}")
            for path, value in _walk_datetime_arguments(arguments):
                if _is_timezone_aware(value):
                    evaluation.checks.append(f"timezone-aware datetime: {path}")
                else:
                    evaluation.failures.append(
                        f"datetime argument '{path}' must include a timezone offset"
                    )
            pending_tools.append(name)
            last_tool_name = name
            last_tool_result = None
        elif event_type == "tool_result":
            name = str(event.get("name") or "")
            result = event.get("result")
            if name not in pending_tools:
                evaluation.failures.append(f"tool result has no matching call: {name}")
            else:
                pending_tools.remove(name)
            last_tool_name = name
            last_tool_result = result if isinstance(result, Mapping) else None
            if isinstance(result, Mapping) and result.get("status") == "error":
                details = result.get("error")
                if not isinstance(details, Mapping):
                    evaluation.failures.append(
                        f"error result is not actionable: {name} is missing error details"
                    )
                else:
                    required_fields = {"code", "message", "next_action"}
                    missing_fields = required_fields - set(details)
                    if missing_fields:
                        evaluation.failures.append(
                            "error result is not actionable: "
                            f"{name} is missing {', '.join(sorted(missing_fields))}"
                        )
                    else:
                        evaluation.checks.append(f"actionable error result: {name}")
            if isinstance(result, Mapping) and result.get("status") in {
                "ok",
                "created",
                "updated",
                "cancelled",
                "available",
            }:
                evaluation.checks.append(f"successful tool result: {event.get('name')}")
        elif event_type == "assistant":
            text = str(event.get("text") or "").lower()
            if any(word in text for word in _SUCCESS_WORDS):
                status = last_tool_result.get("status") if last_tool_result else None
                if status not in {"ok", "created", "updated", "cancelled", "available"}:
                    evaluation.failures.append(
                        "assistant claimed success without a successful tool result"
                        + (f" ({last_tool_name})" if last_tool_name else "")
                    )
                else:
                    evaluation.checks.append("assistant success claim verified")

    for name in pending_tools:
        evaluation.failures.append(f"tool call has no result: {name}")

    return evaluation
