"""Deterministic checks for model-generated tool-call traces.

Trace evaluation is intentionally separate from live model execution.  A
provider adapter can emit this small JSON contract, after which the same rules
can be applied in CI, offline replay, and production incident analysis.
"""

from __future__ import annotations

import json
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
                f"schema violation for {tool_name}: "
                f"missing required argument '{required}'"
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


def _validate_assistant_expectations(
    evaluation: TraceEvaluation,
    events: list[Any],
    expectations: Any,
) -> None:
    """Check deterministic response assertions supplied by a trace scenario.

    These assertions intentionally use explicit phrases rather than trying to
    infer semantic safety from arbitrary prose.  They are useful for replaying
    curated adversarial traces; model-backed evaluation remains responsible for
    paraphrases and broader language-quality judgments.
    """
    if not isinstance(expectations, Mapping):
        evaluation.failures.append("assistant_expectations must be an object")
        return

    assistant_texts = [
        str(event.get("text") or "").strip()
        for event in events
        if isinstance(event, Mapping) and event.get("type") == "assistant"
    ]
    assistant_text = "\n".join(
        assistant_text.casefold() for assistant_text in assistant_texts
    )

    for key, failure_message, check_message in (
        (
            "required_phrases",
            "assistant response is missing a required phrase",
            "assistant required phrase present",
        ),
        (
            "forbidden_phrases",
            "assistant response contains a forbidden phrase",
            "assistant forbidden-phrase check passed",
        ),
    ):
        phrases = expectations.get(key, [])
        if not isinstance(phrases, list) or any(
            not isinstance(phrase, str) or not phrase.strip() for phrase in phrases
        ):
            evaluation.failures.append(
                f"assistant expectations {key} must be a list of non-empty strings"
            )
            continue
        for phrase in phrases:
            phrase_found = phrase.casefold() in assistant_text
            if (key == "required_phrases" and phrase_found) or (
                key == "forbidden_phrases" and not phrase_found
            ):
                evaluation.checks.append(check_message)
            else:
                evaluation.failures.append(failure_message)

    duplicate_expectation = expectations.get(
        "forbid_duplicate_assistant_messages", False
    )
    if not isinstance(duplicate_expectation, bool):
        evaluation.failures.append(
            "assistant expectations forbid_duplicate_assistant_messages must be boolean"
        )
    elif duplicate_expectation:
        normalized_messages = [
            " ".join(text.casefold().split()) for text in assistant_texts if text
        ]
        if len(normalized_messages) != len(set(normalized_messages)):
            evaluation.failures.append(
                "assistant response repeats an earlier assistant message"
            )
        else:
            evaluation.checks.append("assistant duplicate-message check passed")


def _normalize_delegated_events(events: list[Any]) -> list[Any]:
    """Project nested Responses function calls into the generic trace contract."""
    normalized: list[Any] = []
    call_names: dict[str, str] = {}
    for event in events:
        if not isinstance(event, Mapping) or event.get("type") not in {
            "response_event",
            "response.event",
        }:
            normalized.append(event)
            continue

        nested = event.get("event")
        if not isinstance(nested, Mapping):
            normalized.append(event)
            continue
        if nested.get("type") != "response.output_item.done":
            continue
        item = nested.get("item")
        if not isinstance(item, Mapping):
            continue
        item_type = item.get("type")
        call_id = item.get("call_id")
        if item_type == "function_call":
            name = str(item.get("name") or "")
            if isinstance(call_id, str) and call_id:
                call_names[call_id] = name
            arguments = item.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass
            normalized.append(
                {
                    "type": "tool_call",
                    "name": name,
                    "call_id": call_id,
                    "arguments": arguments,
                }
            )
        elif item_type == "function_call_output":
            output = item.get("output")
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    pass
            normalized.append(
                {
                    "type": "tool_result",
                    "name": call_names.get(str(call_id), ""),
                    "call_id": call_id,
                    "result": output,
                }
            )
    return normalized


def evaluate_trace(trace: Mapping[str, Any]) -> TraceEvaluation:
    """Evaluate a model/tool trace against generic safety contracts.

    The accepted trace shape is a mapping with ``scenario_id`` and an ordered
    ``events`` list. Events may also contain ``response_event`` entries from a
    delegated Responses stream; completed function-call items are normalized to
    the same tool-call/result contract before validation. Optional scenario keys are
    ``expected_tool_sequence``, ``forbidden_tools``, ``max_tool_calls``, and
    ``assistant_expectations``.

    The evaluator checks that scheduling datetimes include offsets, expected
    tools appear in order, forbidden tools are absent, unknown tools are
    rejected when a tool map is supplied, assistant response expectations hold,
    and an assistant does not claim a mutation succeeded after the matching
    tool returned an error or no result.
    """
    scenario_id = str(trace.get("scenario_id") or "unnamed-trace")
    evaluation = TraceEvaluation(scenario_id=scenario_id)
    events = trace.get("events")
    if not isinstance(events, list):
        evaluation.failures.append("trace events must be a list")
        return evaluation
    events = _normalize_delegated_events(events)

    tool_calls = [
        event
        for event in events
        if isinstance(event, Mapping) and event.get("type") == "tool_call"
    ]
    tool_names = [str(event.get("name") or "") for event in tool_calls]
    tool_schemas = trace.get("tool_schemas")
    if tool_schemas is not None and not isinstance(tool_schemas, Mapping):
        evaluation.failures.append("tool_schemas must be an object")

    forbidden = {str(name) for name in trace.get("forbidden_tools", []) or []}
    for tool_name in tool_names:
        if tool_name in forbidden:
            evaluation.failures.append(f"forbidden tool was called: {tool_name}")
        elif isinstance(tool_schemas, Mapping) and tool_name not in tool_schemas:
            evaluation.failures.append(f"unknown tool was called: {tool_name}")
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

    pending_tools: list[tuple[str, str | None]] = []
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
            if isinstance(tool_schemas, Mapping) and name in tool_schemas:
                schema = tool_schemas.get(name)
                if isinstance(schema, Mapping):
                    schema_failures = _validate_schema_arguments(
                        name, arguments, schema
                    )
                    evaluation.failures.extend(schema_failures)
                    if not schema_failures:
                        evaluation.checks.append(f"schema arguments valid: {name}")
                else:
                    evaluation.failures.append(
                        f"schema for tool {name} must be an object"
                    )
            for path, value in _walk_datetime_arguments(arguments):
                if _is_timezone_aware(value):
                    evaluation.checks.append(f"timezone-aware datetime: {path}")
                else:
                    evaluation.failures.append(
                        f"datetime argument '{path}' must include a timezone offset"
                    )
            call_id = event.get("call_id")
            pending_tools.append((name, call_id if isinstance(call_id, str) else None))
            last_tool_name = name
            last_tool_result = None
        elif event_type == "tool_result":
            name = str(event.get("name") or "")
            result = event.get("result")
            call_id = event.get("call_id")
            call_id = call_id if isinstance(call_id, str) else None
            match_index = next(
                (
                    index
                    for index, (pending_name, pending_call_id) in enumerate(
                        pending_tools
                    )
                    if (call_id and pending_call_id == call_id)
                    or (not call_id and pending_name == name)
                ),
                None,
            )
            if match_index is None:
                evaluation.failures.append(f"tool result has no matching call: {name}")
            else:
                pending_tools.pop(match_index)
            last_tool_name = name
            last_tool_result = result if isinstance(result, Mapping) else None
            if isinstance(result, Mapping) and result.get("status") == "error":
                details = result.get("error")
                if not isinstance(details, Mapping):
                    evaluation.failures.append(
                        f"error result is not actionable: {name} is missing "
                        "error details"
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

    for name, _call_id in pending_tools:
        evaluation.failures.append(f"tool call has no result: {name}")

    max_tool_calls = trace.get("max_tool_calls")
    if max_tool_calls is not None:
        if (
            isinstance(max_tool_calls, bool)
            or not isinstance(max_tool_calls, int)
            or max_tool_calls < 0
        ):
            evaluation.failures.append("max_tool_calls must be a non-negative integer")
        elif len(tool_calls) > max_tool_calls:
            evaluation.failures.append(
                f"trace exceeded max_tool_calls ({max_tool_calls})"
            )
        else:
            evaluation.checks.append("trace tool-call count within limit")

    if "assistant_expectations" in trace:
        _validate_assistant_expectations(
            evaluation,
            events,
            trace.get("assistant_expectations"),
        )

    return evaluation
