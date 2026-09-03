"""Deterministic Google Sheets service-inquiry evaluation suite."""

from __future__ import annotations

import copy
import json
from typing import Any

import httpx

from shared.voice_agents.tools.google_sheets_lead_service import GoogleSheetsLeadService

from .core import EvalScenario, EvalStep, SuiteResult, run_suite


class FakeGoogleSheets:
    """Small stateful fake for the read-before-append Sheets API contract."""

    def __init__(
        self,
        *,
        existing_submission_id: str | None = None,
        failure_status: int | None = None,
    ) -> None:
        self.existing_submission_id = existing_submission_id
        self.failure_status = failure_status
        self.requests: list[dict[str, str]] = []
        self.write_count = 0

    def client_factory(self) -> httpx.AsyncClient:
        """Return an async client bound to the isolated fake transport."""
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle))

    def handle(self, request: httpx.Request) -> httpx.Response:
        """Handle only the Sheets values read and append resources under test."""
        self.requests.append({"method": request.method, "path": request.url.path})
        if self.failure_status is not None:
            return httpx.Response(
                self.failure_status, json={"message": "simulated failure"}
            )
        if request.method == "GET":
            values = [["Submission ID"]]
            if self.existing_submission_id:
                values.append([self.existing_submission_id])
            return httpx.Response(200, json={"values": values})
        if request.method == "POST":
            self.write_count += 1
            body = json.loads(request.content or b"{}")
            if not body.get("values"):
                return httpx.Response(400, json={"message": "row required"})
            return httpx.Response(
                200,
                json={"updates": {"updatedRange": "Lead submissions!A2:L2"}},
            )
        return httpx.Response(404, json={"message": "unsupported fake method"})


class LeadCaptureEvalAdapter:
    """Expose the focused Google Sheets service through the eval protocol."""

    def __init__(
        self,
        *,
        existing_submission_id: str | None = None,
        failure_status: int | None = None,
    ) -> None:
        self.provider = FakeGoogleSheets(
            existing_submission_id=existing_submission_id,
            failure_status=failure_status,
        )
        self.service = GoogleSheetsLeadService(
            access_token="eval-token",
            spreadsheet_id="sheet-eval-123456",
            lead_source="evaluation",
            client_factory=self.provider.client_factory,
        )

    @property
    def provider_write_count(self) -> int:
        """Return the number of Google Sheets append mutations."""
        return self.provider.write_count

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one service operation and retain no sensitive provider state."""
        result = await getattr(self.service, tool_name)(**arguments)
        return copy.deepcopy(result)


def _adapter_for_scenario(scenario: EvalScenario) -> LeadCaptureEvalAdapter:
    """Create the provider state needed by one named scenario."""
    if scenario.scenario_id == "lead.capture_updates_existing_submission":
        return LeadCaptureEvalAdapter(existing_submission_id="session-eval-1")
    if scenario.scenario_id == "lead.provider_outage_is_explicit":
        return LeadCaptureEvalAdapter(failure_status=503)
    return LeadCaptureEvalAdapter()


def _capture_arguments() -> dict[str, Any]:
    """Return a complete, representative service inquiry."""
    return {
        "caller_name": "Maria Garcia",
        "caller_email": "maria@example.com",
        "caller_phone": "602-555-0101",
        "service_needed": "AC repair",
        "issue_summary": "The upstairs unit is blowing warm air.",
        "property_address": "123 Main Street, Phoenix, AZ",
        "urgency": "This week",
        "preferred_callback_window": "Weekday afternoons",
        "submission_id": "session-eval-1",
    }


def build_lead_capture_scenarios() -> list[EvalScenario]:
    """Return success, dedupe, validation, and outage contracts."""
    return [
        EvalScenario(
            scenario_id="lead.capture_creates_row",
            description="A complete confirmed inquiry becomes one Google Sheets row.",
            tags=("lead", "provider", "mutation"),
            steps=(
                EvalStep(
                    step_id="capture",
                    tool_name="capture_lead",
                    arguments=_capture_arguments(),
                    expected_status="created",
                    expected_fields={
                        "provider": "google_sheets",
                        "sheet.record_id": "session-eval-1",
                        "sheet.record_type": "lead_row",
                        "deduplicated": False,
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="lead.capture_updates_existing_submission",
            description="A same-session retry finds the existing row instead of appending.",
            tags=("lead", "idempotency", "mutation"),
            steps=(
                EvalStep(
                    step_id="capture",
                    tool_name="capture_lead",
                    arguments=_capture_arguments(),
                    expected_status="created",
                    expected_fields={
                        "sheet.record_id": "session-eval-1",
                        "deduplicated": True,
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="lead.follow_up_channel_is_required",
            description="The service refuses to create an unaddressable inquiry.",
            tags=("lead", "validation", "safety"),
            steps=(
                EvalStep(
                    step_id="validate",
                    tool_name="capture_lead",
                    arguments={
                        "caller_name": "Taylor Smith",
                        "service_needed": "Duct cleaning",
                        "issue_summary": "I would like an estimate.",
                    },
                    expected_status="needs_details",
                    expected_fields={"error.code": "missing_or_invalid_detail"},
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="lead.provider_outage_is_explicit",
            description="A Sheets outage is surfaced as retryable without a false success.",
            tags=("lead", "failure", "safety"),
            steps=(
                EvalStep(
                    step_id="capture",
                    tool_name="capture_lead",
                    arguments=_capture_arguments(),
                    expected_status="error",
                    expected_fields={
                        "provider": "google_sheets",
                        "error.code": "temporary_failure",
                        "error.retryable": True,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
    ]


async def run_lead_capture_suite(
    scenarios: list[EvalScenario] | None = None,
) -> SuiteResult:
    """Run the Google Sheets lead-capture suite against fresh fake state per scenario."""
    selected = scenarios or build_lead_capture_scenarios()
    return await run_suite(selected, _adapter_for_scenario)


__all__ = ["build_lead_capture_scenarios", "run_lead_capture_suite"]
