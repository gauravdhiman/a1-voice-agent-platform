"""Deterministic workflow evaluations for human-callback soft escalation."""

import pytest

from evals.callback import build_callback_scenarios, run_callback_suite


@pytest.mark.asyncio
async def test_callback_suite_covers_notify_and_failure_paths() -> None:
    """The callback workflow notifies owners once and rejects bad input."""
    suite = await run_callback_suite()

    assert suite.passed is True
    assert suite.score == 1.0
    assert len(suite.results) == 8
    assert {"escalation", "safety", "mutation", "sms"}.issubset(
        {tag for scenario in build_callback_scenarios() for tag in scenario.tags}
    )
