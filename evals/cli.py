"""Command-line orchestration for deterministic and trace evaluations."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .calendar import build_calendar_scenarios, run_calendar_suite
from .callback import build_callback_scenarios, run_callback_suite
from .lead_capture import build_lead_capture_scenarios, run_lead_capture_suite
from .resend import build_resend_scenarios, run_resend_suite
from .trace import evaluate_trace


def _git_revision() -> str | None:
    """Return the evaluated revision from CI or the local checkout."""
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def format_suite_summary(summary: dict[str, Any]) -> str:
    """Render a concise CI summary from a serialized suite result."""
    passed_count = int(summary.get("passed_count", 0))
    scenario_count = int(summary.get("scenario_count", 0))
    score = float(summary.get("score", 0.0))
    lines = [
        f"Agent evaluation suite: {passed_count}/{scenario_count} scenarios passed ({score:.1%})",
        f"Gate: {'PASS' if summary.get('passed') else 'FAIL'}",
    ]
    failures = summary.get("critical_failures") or []
    if failures:
        lines.append("Critical failures: " + ", ".join(str(item) for item in failures))
    return "\n".join(lines)


def compare_reports(
    current: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    """Compare scenario outcomes and suite scores between two reports.

    A pass-to-fail transition is a regression.  A fail-to-pass transition is an
    improvement.  Score deltas are retained separately so a non-binary quality
    change remains visible even when both reports have the same gate result.
    """
    regressions: list[str] = []
    improvements: list[str] = []
    score_deltas: dict[str, float] = {}
    current_suites = current.get("suites") or {}
    baseline_suites = baseline.get("suites") or {}
    for suite_name in sorted(set(current_suites) | set(baseline_suites)):
        current_suite = current_suites.get(suite_name) or {}
        baseline_suite = baseline_suites.get(suite_name) or {}
        current_score = float(current_suite.get("score", 0.0))
        baseline_score = float(baseline_suite.get("score", 0.0))
        score_deltas[suite_name] = current_score - baseline_score
        current_results = {
            str(item.get("scenario_id")): item
            for item in current_suite.get("results", [])
            if isinstance(item, dict) and item.get("scenario_id")
        }
        baseline_results = {
            str(item.get("scenario_id")): item
            for item in baseline_suite.get("results", [])
            if isinstance(item, dict) and item.get("scenario_id")
        }
        for scenario_id in sorted(set(current_results) | set(baseline_results)):
            current_result = current_results.get(scenario_id)
            baseline_result = baseline_results.get(scenario_id)
            label = f"{suite_name}:{scenario_id}"
            if baseline_result is None:
                if current_result and not current_result.get("passed", False):
                    regressions.append(label)
                continue
            if current_result is None:
                regressions.append(label)
                continue
            if baseline_result.get("passed") and not current_result.get("passed"):
                regressions.append(label)
            elif not baseline_result.get("passed") and current_result.get("passed"):
                improvements.append(label)
            elif float(current_result.get("score", 0.0)) < float(
                baseline_result.get("score", 0.0)
            ):
                regressions.append(label)
            elif float(current_result.get("score", 0.0)) > float(
                baseline_result.get("score", 0.0)
            ):
                improvements.append(label)

    current_traces = {
        str(item.get("scenario_id")): item
        for item in current.get("traces", [])
        if isinstance(item, dict) and item.get("scenario_id")
    }
    baseline_traces = {
        str(item.get("scenario_id")): item
        for item in baseline.get("traces", [])
        if isinstance(item, dict) and item.get("scenario_id")
    }
    for scenario_id in sorted(set(current_traces) | set(baseline_traces)):
        current_trace = current_traces.get(scenario_id)
        baseline_trace = baseline_traces.get(scenario_id)
        label = f"trace:{scenario_id}"
        if current_trace is None or baseline_trace is None:
            if current_trace is None or not current_trace.get("passed", False):
                regressions.append(label)
            continue
        score_deltas[label] = float(current_trace.get("score", 0.0)) - float(
            baseline_trace.get("score", 0.0)
        )
        if baseline_trace.get("passed") and not current_trace.get("passed"):
            regressions.append(label)
        elif not baseline_trace.get("passed") and current_trace.get("passed"):
            improvements.append(label)
        elif float(current_trace.get("score", 0.0)) < float(
            baseline_trace.get("score", 0.0)
        ):
            regressions.append(label)
        elif float(current_trace.get("score", 0.0)) > float(
            baseline_trace.get("score", 0.0)
        ):
            improvements.append(label)
    return {
        "regressions": regressions,
        "improvements": improvements,
        "score_deltas": score_deltas,
    }


def _load_trace_file(path: Path) -> list[dict[str, Any]]:
    """Load one trace object or a list of trace objects from JSON."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise ValueError("trace file must contain a JSON object or list of objects")


async def _run(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    """Run requested suites and return a report plus its gate result."""
    report: dict[str, Any] = {
        "metadata": {
            "evaluation_version": "1",
            "git_sha": _git_revision(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "suites": {},
        "traces": [],
    }
    gate_passed = True

    if args.suite in {"calendar", "all"}:
        if args.list_scenarios:
            report.setdefault("scenarios", []).extend(
                scenario.scenario_id for scenario in build_calendar_scenarios()
            )
        else:
            suite = await run_calendar_suite()
            report["suites"]["calendar"] = suite.to_dict()
            gate_passed = gate_passed and suite.passed
    if args.suite in {"lead_capture", "all"}:
        if args.list_scenarios:
            report.setdefault("scenarios", []).extend(
                scenario.scenario_id for scenario in build_lead_capture_scenarios()
            )
        else:
            suite = await run_lead_capture_suite()
            report["suites"]["lead_capture"] = suite.to_dict()
            gate_passed = gate_passed and suite.passed
    if args.suite in {"callback", "all"}:
        if args.list_scenarios:
            report.setdefault("scenarios", []).extend(
                scenario.scenario_id for scenario in build_callback_scenarios()
            )
        else:
            suite = await run_callback_suite()
            report["suites"]["callback"] = suite.to_dict()
            gate_passed = gate_passed and suite.passed
    if args.suite in {"resend", "all"}:
        if args.list_scenarios:
            report.setdefault("scenarios", []).extend(
                scenario.scenario_id for scenario in build_resend_scenarios()
            )
        else:
            suite = await run_resend_suite()
            report["suites"]["resend"] = suite.to_dict()
            gate_passed = gate_passed and suite.passed

    for trace_path in args.trace or []:
        for trace in _load_trace_file(trace_path):
            evaluation = evaluate_trace(trace)
            report["traces"].append(evaluation.to_dict())
            gate_passed = gate_passed and evaluation.passed

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        comparison = compare_reports(report, baseline)
        report["comparison"] = comparison
        gate_passed = gate_passed and not comparison["regressions"]

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report, gate_passed


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evaluation CLI and return a process exit code."""
    parser = argparse.ArgumentParser(
        description=(
            "Run provider-independent agent evaluations. The default suite "
            "uses provider fakes and never needs external credentials."
        )
    )
    parser.add_argument(
        "--suite",
        choices=("all", "calendar", "callback", "lead_capture", "resend"),
        default="all",
        help="Deterministic suite to run (default: all).",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List scenario ids without executing the suite.",
    )
    parser.add_argument(
        "--trace",
        action="append",
        type=Path,
        help="JSON trace file to evaluate; may be supplied more than once.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for the machine-readable evaluation report.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Previous JSON report; fail the gate on scenario regressions.",
    )
    args = parser.parse_args(argv)
    report, passed = asyncio.run(_run(args))

    for suite_name in sorted(report["suites"]):
        print(f"[{suite_name}]")
        print(format_suite_summary(report["suites"][suite_name]))
    for trace in report["traces"]:
        print(
            f"Trace {trace['scenario_id']}: "
            f"{'PASS' if trace['passed'] else 'FAIL'} ({trace['score']:.1%})"
        )
        for failure in trace.get("failures", []):
            print(f"  - {failure}")
    if report.get("comparison"):
        comparison = report["comparison"]
        print(
            "Baseline comparison: "
            f"{len(comparison['improvements'])} improvements, "
            f"{len(comparison['regressions'])} regressions"
        )
        if comparison["regressions"]:
            print("Regressions: " + ", ".join(comparison["regressions"]))
    if args.list_scenarios:
        for scenario_id in report.get("scenarios", []):
            print(scenario_id)
    return 0 if passed else 1
