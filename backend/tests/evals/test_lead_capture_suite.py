"""Deterministic workflow evaluations for Google Sheets lead capture."""

import pytest

from evals.lead_capture import build_lead_capture_scenarios, run_lead_capture_suite


@pytest.mark.asyncio
async def test_lead_capture_suite_covers_success_and_failure_paths() -> None:
    """The lead workflow protects confirmation context, dedupe, and outages."""
    suite = await run_lead_capture_suite()

    assert suite.passed is True
    assert suite.score == 1.0
    assert len(suite.results) == 4
    assert {"lead", "safety", "mutation"}.issubset(
        {tag for scenario in build_lead_capture_scenarios() for tag in scenario.tags}
    )
