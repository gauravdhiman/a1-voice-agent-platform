"""Core primitives for repeatable, provider-independent agent evaluations.

The runner deliberately evaluates a tool adapter rather than reimplementing a
tool.  Scenarios describe the calls an agent should make and the safety
properties those calls must satisfy.  A model-backed adapter can be added later
without changing the scenario format.
"""

from __future__ import annotations

import copy
import inspect
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


class ScenarioEvaluationError(ValueError):
    """Raised when a scenario is malformed or references missing state."""


class EvalAdapter(Protocol):
    """Minimal interface required by the scenario runner.

    Attributes:
        provider_write_count: Number of external mutations performed so far.
            Adapters should increment this only for provider-side writes such as
            create, patch, or delete.  It makes confirmation and conflict
            scenarios testable without inspecting provider-specific internals.
    """

    provider_write_count: int

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one model-facing tool and return its JSON-safe result."""


@dataclass(frozen=True)
class EvalStep:
    """One expected model-facing tool invocation in a scenario.

    Args:
        step_id: Stable name used in reports and as a capture key.
        tool_name: Public function name the model is expected to invoke.
        arguments: JSON-safe arguments.  A value such as
            ``"${booking.appointment.id}"`` reads a value captured by an
            earlier step.
        expected_status: Optional result status that must be returned.
        expected_code: Optional error code that must be returned.
        expected_fields: Result paths and expected values, for example
            ``{"appointment.duration_minutes": 90}``.
        capture: Optional key under which to retain the entire result.
        assert_no_provider_write: Require this step to leave the provider write
            counter unchanged.
    """

    step_id: str
    tool_name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    expected_status: str | None = None
    expected_code: str | None = None
    expected_fields: Mapping[str, Any] = field(default_factory=dict)
    capture: str | None = None
    assert_no_provider_write: bool = False


@dataclass(frozen=True)
class EvalScenario:
    """A deterministic workflow contract for one agent use case.

    Attributes:
        scenario_id: Stable identifier used for trend comparisons.
        description: Human-readable purpose of the scenario.
        steps: Ordered tool calls and assertions.
        tags: Classification labels such as ``timezone`` or ``safety``.
        critical: Whether a failure should fail the default suite exit code.
    """

    scenario_id: str
    description: str
    steps: tuple[EvalStep, ...]
    tags: tuple[str, ...] = ()
    critical: bool = True


@dataclass
class EvalCheck:
    """Outcome of one step-level evaluation check."""

    step_id: str
    passed: bool
    message: str


@dataclass
class ScenarioResult:
    """Collected result for one scenario execution."""

    scenario_id: str
    description: str
    critical: bool
    checks: list[EvalCheck] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return whether every check in the scenario passed."""
        return not self.failures and all(check.passed for check in self.checks)

    @property
    def score(self) -> float:
        """Return the fraction of completed checks that passed."""
        if not self.checks:
            return 1.0 if self.passed else 0.0
        return sum(check.passed for check in self.checks) / len(self.checks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for CI artifacts and trend storage."""
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "critical": self.critical,
            "passed": self.passed,
            "score": self.score,
            "checks": [asdict(check) for check in self.checks],
            "failures": list(self.failures),
            "calls": copy.deepcopy(self.calls),
        }


@dataclass
class SuiteResult:
    """Aggregate result for a suite of scenarios."""

    results: list[ScenarioResult]

    @property
    def passed(self) -> bool:
        """Return whether all critical scenarios passed."""
        return all(result.passed for result in self.results if result.critical)

    @property
    def score(self) -> float:
        """Return the average scenario score, or one for an empty suite."""
        if not self.results:
            return 1.0
        return sum(result.score for result in self.results) / len(self.results)

    @property
    def passed_count(self) -> int:
        """Return the number of scenarios with no failures."""
        return sum(result.passed for result in self.results)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the aggregate result for a machine-readable report."""
        return {
            "passed": self.passed,
            "score": self.score,
            "scenario_count": len(self.results),
            "passed_count": self.passed_count,
            "critical_failures": [
                result.scenario_id
                for result in self.results
                if result.critical and not result.passed
            ],
            "results": [result.to_dict() for result in self.results],
        }


_REFERENCE_PATTERN = re.compile(r"^\$\{([A-Za-z0-9_-]+)((?:\.[A-Za-z0-9_-]+)*)\}$")


def _lookup_path(value: Any, path: str) -> Any:
    """Read a dotted path from mappings or objects used by a scenario."""
    current = value
    for part in path.split(".") if path else []:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            raise ScenarioEvaluationError(f"captured value has no path '{path}'")
    return current


def resolve_references(value: Any, captures: Mapping[str, Any]) -> Any:
    """Resolve captured-result references recursively in scenario arguments.

    Args:
        value: A JSON-compatible value or nested list/dict.  Exact strings in
            the form ``${capture.path.to.value}`` are replaced with the
            referenced value while preserving its type.
        captures: Results saved by prior scenario steps.

    Returns:
        A deep-copied value with all references resolved.

    Raises:
        ScenarioEvaluationError: If a referenced capture or path is missing.
    """
    if isinstance(value, str):
        match = _REFERENCE_PATTERN.match(value)
        if not match:
            return value
        capture_name, path = match.groups()
        if capture_name not in captures:
            raise ScenarioEvaluationError(f"unknown capture '{capture_name}'")
        return copy.deepcopy(_lookup_path(captures[capture_name], path.lstrip(".")))
    if isinstance(value, list):
        return [resolve_references(item, captures) for item in value]
    if isinstance(value, tuple):
        return tuple(resolve_references(item, captures) for item in value)
    if isinstance(value, Mapping):
        return {key: resolve_references(item, captures) for key, item in value.items()}
    return value


def _record_check(
    result: ScenarioResult, step_id: str, passed: bool, message: str
) -> None:
    """Append one check and retain a compact failure list."""
    result.checks.append(EvalCheck(step_id=step_id, passed=passed, message=message))
    if not passed:
        result.failures.append(f"{step_id}: {message}")


async def run_scenario(
    scenario: EvalScenario,
    adapter_factory: Callable[[], EvalAdapter | Awaitable[EvalAdapter]],
) -> ScenarioResult:
    """Execute one scenario against a fresh adapter instance.

    Args:
        scenario: Ordered calls and assertions to execute.
        adapter_factory: Factory that creates isolated state for the scenario.
            It may return an adapter directly or an awaitable adapter.

    Returns:
        ScenarioResult containing every assertion and model-facing call.

    Raises:
        ScenarioEvaluationError: If the scenario itself contains an invalid
            reference.  Configuration errors are intentionally loud so a
            broken evaluation cannot look like a passing run.
    """
    adapter = adapter_factory()
    if inspect.isawaitable(adapter):
        adapter = await adapter
    result = ScenarioResult(
        scenario_id=scenario.scenario_id,
        description=scenario.description,
        critical=scenario.critical,
    )
    captures: dict[str, Any] = {}

    for step in scenario.steps:
        arguments = resolve_references(dict(step.arguments), captures)
        writes_before = adapter.provider_write_count
        try:
            tool_result = await adapter.invoke(step.tool_name, arguments)
        except Exception as exc:  # noqa: BLE001 - report adapter failure per step
            _record_check(result, step.step_id, False, f"adapter raised {exc!r}")
            continue

        result.calls.append(
            {"step_id": step.step_id, "tool": step.tool_name, "arguments": arguments}
        )
        is_mapping = isinstance(tool_result, Mapping)
        if not is_mapping:
            _record_check(
                result,
                step.step_id,
                False,
                "tool result was not a JSON object",
            )
            continue

        step_passed = True
        status = tool_result.get("status")
        if step.expected_status is not None and status != step.expected_status:
            _record_check(
                result,
                step.step_id,
                False,
                f"expected status {step.expected_status!r}, got {status!r}",
            )
            step_passed = False
        if (
            step.expected_code is not None
            and tool_result.get("code") != step.expected_code
        ):
            _record_check(
                result,
                step.step_id,
                False,
                f"expected code {step.expected_code!r}, got {tool_result.get('code')!r}",
            )
            step_passed = False
        for path, expected in step.expected_fields.items():
            expected_value = resolve_references(expected, captures)
            try:
                actual_value = _lookup_path(tool_result, path)
            except ScenarioEvaluationError as exc:
                _record_check(result, step.step_id, False, str(exc))
                step_passed = False
                continue
            if actual_value != expected_value:
                _record_check(
                    result,
                    step.step_id,
                    False,
                    f"field {path!r} expected {expected_value!r}, got {actual_value!r}",
                )
                step_passed = False
        if (
            step.assert_no_provider_write
            and adapter.provider_write_count != writes_before
        ):
            _record_check(
                result,
                step.step_id,
                False,
                "provider write occurred during a no-write step",
            )
            step_passed = False
        if step_passed:
            _record_check(result, step.step_id, True, "step passed")
        if step.capture:
            captures[step.capture] = copy.deepcopy(dict(tool_result))

    return result


async def run_suite(
    scenarios: list[EvalScenario],
    adapter_factory: Callable[[EvalScenario], EvalAdapter | Awaitable[EvalAdapter]],
) -> SuiteResult:
    """Run scenarios sequentially with isolated state and aggregate results.

    Scenarios run sequentially by design.  This keeps provider fakes and future
    replay adapters deterministic, while an adapter may still measure its own
    latency and concurrency behavior explicitly.
    """
    results: list[ScenarioResult] = []
    for scenario in scenarios:
        result = await run_scenario(
            scenario,
            lambda scenario=scenario: adapter_factory(scenario),
        )
        results.append(result)
    return SuiteResult(results=results)
