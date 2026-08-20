"""Tests for the deterministic agent-evaluation runner."""

from __future__ import annotations

import pytest

from evals.core import (
    EvalScenario,
    EvalStep,
    ScenarioEvaluationError,
    resolve_references,
    run_scenario,
)


class _Adapter:
    """Small adapter used to exercise runner behavior without a provider."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.provider_write_count = 0

    async def invoke(
        self, tool_name: str, arguments: dict[str, object]
    ) -> dict[str, object]:
        """Return a predictable result for the scenario runner."""
        self.calls.append((tool_name, arguments))
        if tool_name == "create":
            self.provider_write_count += 1
            return {
                "status": "created",
                "appointment": {"id": "event-123", "duration_minutes": 60},
            }
        return {"status": "ok"}


def test_resolve_references_reads_nested_captured_values() -> None:
    """Later steps can use identifiers returned by earlier tool calls."""
    captures = {"booking": {"appointment": {"id": "event-123"}}}

    assert resolve_references(
        {"appointment_id": "${booking.appointment.id}"}, captures
    ) == {"appointment_id": "event-123"}


@pytest.mark.asyncio
async def test_runner_captures_results_and_checks_expected_status() -> None:
    """A passing scenario records both tool calls and deterministic checks."""
    adapter = _Adapter()
    scenario = EvalScenario(
        scenario_id="capture-id",
        description="Create and reuse an appointment id.",
        steps=(
            EvalStep(
                step_id="booking",
                tool_name="create",
                arguments={},
                expected_status="created",
                capture="booking",
            ),
            EvalStep(
                step_id="lookup",
                tool_name="find",
                arguments={"appointment_id": "${booking.appointment.id}"},
                expected_status="ok",
            ),
        ),
    )

    result = await run_scenario(scenario, lambda: adapter)

    assert result.passed is True
    assert result.score == 1.0
    assert adapter.calls[1][1] == {"appointment_id": "event-123"}


@pytest.mark.asyncio
async def test_runner_fails_when_a_write_happens_during_no_write_step() -> None:
    """Safety scenarios fail if a confirmation gate performs a provider write."""
    adapter = _Adapter()
    scenario = EvalScenario(
        scenario_id="no-write",
        description="A confirmation gate must not write.",
        steps=(
            EvalStep(
                step_id="confirmation",
                tool_name="create",
                arguments={},
                expected_status="confirmation_required",
                assert_no_provider_write=True,
            ),
        ),
    )

    result = await run_scenario(scenario, lambda: adapter)

    assert result.passed is False
    assert any("expected status" in failure.lower() for failure in result.failures)


def test_invalid_reference_is_reported_as_configuration_error() -> None:
    """A typo in a scenario must be visible instead of silently passing."""
    with pytest.raises(ScenarioEvaluationError, match="unknown capture"):
        resolve_references("${missing.id}", {})
