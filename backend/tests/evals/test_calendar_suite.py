"""Deterministic workflow evaluations for Google Calendar appointments."""

from __future__ import annotations

import pytest

from evals.calendar import build_calendar_scenarios, run_calendar_suite


@pytest.mark.asyncio
async def test_calendar_suite_covers_critical_booking_workflows() -> None:
    """The default suite exercises booking, mutation, timezone, and failure paths."""
    suite = await run_calendar_suite()

    assert suite.passed is True
    assert suite.score == 1.0
    assert len(suite.results) >= 10
    assert {
        "timezone",
        "safety",
        "conflict",
        "mutation",
    }.issubset(
        {tag for scenario in build_calendar_scenarios() for tag in scenario.tags}
    )


@pytest.mark.asyncio
async def test_calendar_scenario_captures_created_appointment_for_follow_up() -> None:
    """A booking result can feed a later lookup/update step in one scenario."""
    scenarios = build_calendar_scenarios()
    scenario = next(
        item for item in scenarios if item.scenario_id == "calendar.create_then_update"
    )

    suite = await run_calendar_suite([scenario])

    assert suite.passed is True
    assert suite.results[0].calls[-1]["tool"] == "update_appointment"
    assert suite.results[0].calls[-1]["arguments"]["appointment_id"].startswith("a1")
