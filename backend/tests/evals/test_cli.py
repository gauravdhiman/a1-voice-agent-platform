"""Tests for the agent evaluation command-line reporting."""

from evals.cli import compare_reports, format_suite_summary


def test_summary_reports_pass_rate_and_failures() -> None:
    """CI output should make the gate result obvious in a short log."""
    summary = format_suite_summary(
        {
            "passed": False,
            "score": 0.75,
            "scenario_count": 4,
            "passed_count": 3,
            "critical_failures": ["calendar.timezone"],
        }
    )

    assert "3/4" in summary
    assert "75.0%" in summary
    assert "calendar.timezone" in summary


def test_compare_reports_identifies_regressions_and_improvements() -> None:
    """A report comparison makes directional change visible to CI and reviewers."""
    comparison = compare_reports(
        {
            "suites": {
                "calendar": {
                    "score": 0.5,
                    "results": [
                        {"scenario_id": "a", "passed": False, "score": 0.0},
                        {"scenario_id": "b", "passed": True, "score": 1.0},
                    ],
                }
            }
        },
        {
            "suites": {
                "calendar": {
                    "score": 1.0,
                    "results": [
                        {"scenario_id": "a", "passed": True, "score": 1.0},
                        {"scenario_id": "b", "passed": False, "score": 0.0},
                    ],
                }
            }
        },
    )

    assert comparison["regressions"] == ["calendar:a"]
    assert comparison["improvements"] == ["calendar:b"]
    assert comparison["score_deltas"]["calendar"] == -0.5
