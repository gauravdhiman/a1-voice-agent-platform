"""Deterministic Google Calendar appointment evaluation suite.

The fake provider implements only the Google Calendar HTTP resources used by
the shared appointment service.  The service itself remains the system under
test; the fake exists to make conflict races, retries, outages, and existing
appointments reproducible without OAuth credentials or real calendar writes.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import httpx

from shared.voice_agents.tools.google_calendar_appointment_service import (
    GoogleCalendarAppointmentService,
)

from .core import EvalAdapter, EvalScenario, EvalStep, SuiteResult, run_suite


_CALENDAR_ID = "primary"
_PHOENIX = "America/Phoenix"
_NOW = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo(_PHOENIX))


def _parse_datetime(value: str) -> datetime:
    """Parse a provider timestamp for fake-calendar interval comparisons."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _event(
    event_id: str,
    start_time: str,
    end_time: str,
    *,
    summary: str = "Appointment: Jane Doe — Cleaning",
    description: str = "Purpose: Cleaning\nEmail: jane@example.com",
    attendees: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build a compact timed Google event for scenario seed data."""
    return {
        "id": event_id,
        "status": "confirmed",
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
        "attendees": attendees or [],
    }


class FakeGoogleCalendar:
    """Small stateful HTTP fake for the Calendar API subset under test.

    The fake tracks provider requests and successful mutations.  It is not a
    general Google API emulator; unsupported behavior should be added only when
    a scenario needs it, keeping the evaluation contract easy to audit.
    """

    def __init__(
        self,
        events: Iterable[dict[str, Any]] = (),
        *,
        calendar_id: str = _CALENDAR_ID,
        failure_status: int | None = None,
    ) -> None:
        """Initialize fake state with optional events and a forced failure."""
        self.calendar_id = calendar_id
        self.events = {
            str(item["id"]): copy.deepcopy(item) for item in events if item.get("id")
        }
        self.failure_status = failure_status
        self.requests: list[dict[str, str]] = []
        self.write_count = 0

    def client_factory(self) -> httpx.AsyncClient:
        """Return an HTTP client bound to this fake's transport."""
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle))

    def handle(self, request: httpx.Request) -> httpx.Response:
        """Handle one request using the Calendar REST shape."""
        self.requests.append({"method": request.method, "path": request.url.path})
        if self.failure_status is not None:
            return httpx.Response(
                self.failure_status,
                json={"error": {"message": "simulated provider failure"}},
            )

        base = f"/calendar/v3/calendars/{self.calendar_id}/events"
        if request.url.path == "/calendar/v3/freeBusy":
            return self._freebusy(request)
        if request.url.path == base:
            if request.method == "GET":
                return self._list_events(request)
            if request.method == "POST":
                return self._create_event(request)
        if request.url.path.startswith(base + "/"):
            event_id = request.url.path[len(base) + 1 :]
            if request.method == "GET":
                return self._get_event(event_id)
            if request.method == "PATCH":
                return self._patch_event(event_id, request)
            if request.method == "DELETE":
                return self._delete_event(event_id)
        return httpx.Response(
            404, json={"error": {"message": "unsupported fake request"}}
        )

    def _freebusy(self, request: httpx.Request) -> httpx.Response:
        """Return seeded event intervals that overlap the requested window."""
        body = json.loads(request.content or b"{}")
        start = _parse_datetime(str(body.get("timeMin")))
        end = _parse_datetime(str(body.get("timeMax")))
        busy = []
        for event in self.events.values():
            event_start = _parse_datetime(event["start"]["dateTime"])
            event_end = _parse_datetime(event["end"]["dateTime"])
            if event_start < end and start < event_end:
                busy.append(
                    {
                        "start": event["start"]["dateTime"],
                        "end": event["end"]["dateTime"],
                    }
                )
        return httpx.Response(
            200,
            json={"calendars": {self.calendar_id: {"busy": busy}}},
        )

    def _list_events(self, request: httpx.Request) -> httpx.Response:
        """Return timed events overlapping the requested list window."""
        time_min = request.url.params.get("timeMin")
        time_max = request.url.params.get("timeMax")
        start = _parse_datetime(time_min) if time_min else None
        end = _parse_datetime(time_max) if time_max else None
        items = []
        for event in self.events.values():
            event_start = _parse_datetime(event["start"]["dateTime"])
            event_end = _parse_datetime(event["end"]["dateTime"])
            if start and event_end <= start:
                continue
            if end and event_start >= end:
                continue
            items.append(copy.deepcopy(event))
        items.sort(key=lambda item: item["start"]["dateTime"])
        return httpx.Response(200, json={"items": items})

    def _create_event(self, request: httpx.Request) -> httpx.Response:
        """Create an event or return a conflict for a repeated idempotent insert."""
        body = json.loads(request.content or b"{}")
        event_id = str(body.get("id") or f"event-{len(self.events) + 1}")
        if event_id in self.events:
            return httpx.Response(409, json={"error": {"message": "duplicate id"}})
        event = copy.deepcopy(body)
        event["id"] = event_id
        event.setdefault("status", "confirmed")
        self.events[event_id] = event
        self.write_count += 1
        return httpx.Response(201, json=copy.deepcopy(event))

    def _get_event(self, event_id: str) -> httpx.Response:
        """Return one event or a provider-style not-found response."""
        event = self.events.get(event_id)
        if event is None:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        return httpx.Response(200, json=copy.deepcopy(event))

    def _patch_event(self, event_id: str, request: httpx.Request) -> httpx.Response:
        """Apply the shallow event patch used by the appointment service."""
        event = self.events.get(event_id)
        if event is None:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        patch = json.loads(request.content or b"{}")
        for key, value in patch.items():
            event[key] = copy.deepcopy(value)
        self.write_count += 1
        return httpx.Response(200, json=copy.deepcopy(event))

    def _delete_event(self, event_id: str) -> httpx.Response:
        """Delete one event and return the empty success response."""
        if event_id not in self.events:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        del self.events[event_id]
        self.write_count += 1
        return httpx.Response(204)


class CalendarEvalAdapter:
    """Expose the shared appointment service through the evaluation protocol."""

    def __init__(
        self,
        *,
        events: Iterable[dict[str, Any]] = (),
        timezone_name: str = _PHOENIX,
        now: datetime = _NOW,
        failure_status: int | None = None,
    ) -> None:
        """Build isolated fake provider and service state for one scenario."""
        self.provider = FakeGoogleCalendar(
            events,
            calendar_id=_CALENDAR_ID,
            failure_status=failure_status,
        )
        self.service = GoogleCalendarAppointmentService(
            access_token="eval-token",
            calendar_id=_CALENDAR_ID,
            timezone_name=timezone_name,
            now_provider=lambda: now,
            idempotency_key="eval-session",
            client_factory=self.provider.client_factory,
        )
        self.call_records: list[dict[str, Any]] = []

    @property
    def provider_write_count(self) -> int:
        """Return the number of fake provider mutations."""
        return self.provider.write_count

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one real shared service operation and record its call."""
        function = getattr(self.service, tool_name)
        result = await function(**arguments)
        self.call_records.append(
            {"tool": tool_name, "arguments": copy.deepcopy(arguments), "result": result}
        )
        return result


def _scenario_seed(scenario_id: str) -> dict[str, Any]:
    """Return isolated provider configuration for a named scenario."""
    if scenario_id == "calendar.availability_excludes_busy":
        return {
            "events": [
                _event(
                    "busy-morning",
                    "2026-08-20T09:30:00-07:00",
                    "2026-08-20T10:30:00-07:00",
                )
            ]
        }
    if scenario_id == "calendar.create_conflict_rechecked":
        return {
            "events": [
                _event(
                    "busy-target",
                    "2026-08-20T10:30:00-07:00",
                    "2026-08-20T11:30:00-07:00",
                )
            ]
        }
    if scenario_id in {
        "calendar.find_existing_appointment",
        "calendar.update_existing_metadata",
        "calendar.update_extension_excludes_self",
        "calendar.update_conflict_is_reported",
        "calendar.cancel_requires_confirmation",
        "calendar.cancel_success",
        "calendar.update_requires_confirmation",
    }:
        events = [
            _event(
                "target-appointment",
                "2026-08-20T10:30:00-07:00",
                "2026-08-20T11:30:00-07:00",
                attendees=[{"email": "jane@example.com"}],
            )
        ]
        if scenario_id == "calendar.update_conflict_is_reported":
            events.append(
                _event(
                    "other-appointment",
                    "2026-08-20T14:30:00-07:00",
                    "2026-08-20T15:30:00-07:00",
                    summary="Appointment: Other Caller — Consultation",
                )
            )
        return {"events": events}
    if scenario_id == "calendar.provider_outage_is_explicit":
        return {"failure_status": 503}
    return {}


def build_calendar_scenarios() -> list[EvalScenario]:
    """Return the critical appointment workflows and corner cases.

    These scenarios intentionally cover both safe refusal and successful
    mutation paths.  They are model-facing contracts, not merely provider
    response tests: every step uses the public six-function appointment API.
    """
    return [
        EvalScenario(
            scenario_id="calendar.availability_excludes_busy",
            description="Availability returns only starts that fit the requested duration.",
            tags=("availability", "timezone", "conflict"),
            steps=(
                EvalStep(
                    step_id="search",
                    tool_name="find_available_slots",
                    arguments={
                        "window_start": "2026-08-20T09:00:00-07:00",
                        "window_end": "2026-08-20T12:00:00-07:00",
                        "duration_minutes": 60,
                        "slot_interval_minutes": 30,
                    },
                    expected_status="ok",
                    expected_fields={
                        "slots": [
                            {
                                "start_time": "2026-08-20T10:30:00-07:00",
                                "end_time": "2026-08-20T11:30:00-07:00",
                            },
                            {
                                "start_time": "2026-08-20T11:00:00-07:00",
                                "end_time": "2026-08-20T12:00:00-07:00",
                            },
                        ],
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.naive_datetime_is_rejected",
            description="The tool rejects ambiguous local datetimes instead of guessing.",
            tags=("timezone", "validation"),
            steps=(
                EvalStep(
                    step_id="check",
                    tool_name="check_availability",
                    arguments={
                        "start_time": "2026-08-20T10:30:00",
                        "duration_minutes": 60,
                    },
                    expected_status="error",
                    expected_code="invalid_argument",
                    expected_fields={
                        "error.field": "start_time",
                        "error.next_action": "retry_with_corrected_arguments",
                        "error.expected_format": "ISO 8601 datetime with numeric UTC offset",
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.create_requires_confirmation",
            description="A booking request without explicit confirmation is a no-op.",
            tags=("safety", "confirmation"),
            steps=(
                EvalStep(
                    step_id="create",
                    tool_name="create_appointment",
                    arguments={
                        "caller_name": "Jane Doe",
                        "purpose": "Cleaning",
                        "start_time": "2026-08-20T10:30:00-07:00",
                        "duration_minutes": 60,
                        "caller_phone": "+15551234567",
                        "user_confirmed": False,
                    },
                    expected_status="confirmation_required",
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.create_conflict_rechecked",
            description="A just-occupied slot is rejected immediately before insert.",
            tags=("safety", "conflict"),
            steps=(
                EvalStep(
                    step_id="create",
                    tool_name="create_appointment",
                    arguments={
                        "caller_name": "Jane Doe",
                        "purpose": "Cleaning",
                        "start_time": "2026-08-20T10:30:00-07:00",
                        "duration_minutes": 60,
                        "user_confirmed": True,
                    },
                    expected_status="busy",
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.past_time_is_rejected",
            description="A past interval is rejected without contacting the provider.",
            tags=("safety", "timezone", "validation"),
            steps=(
                EvalStep(
                    step_id="check",
                    tool_name="check_availability",
                    arguments={
                        "start_time": "2026-08-20T07:30:00-07:00",
                        "duration_minutes": 60,
                    },
                    expected_status="past",
                    expected_fields={"next_action": "choose_future_time"},
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.invalid_duration_is_actionable",
            description="An invalid duration identifies the argument and correction.",
            tags=("safety", "validation"),
            steps=(
                EvalStep(
                    step_id="check",
                    tool_name="check_availability",
                    arguments={
                        "start_time": "2026-08-20T10:30:00-07:00",
                        "duration_minutes": 0,
                    },
                    expected_status="error",
                    expected_code="invalid_argument",
                    expected_fields={
                        "error.field": "duration_minutes",
                        "error.next_action": "retry_with_corrected_arguments",
                        "error.expected_format": "positive integer from 1 through 1440",
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.create_retry_is_idempotent",
            description="A repeated create request returns the existing appointment instead of duplicating it.",
            tags=("reliability", "booking", "mutation"),
            steps=(
                EvalStep(
                    step_id="create",
                    tool_name="create_appointment",
                    arguments={
                        "caller_name": "Jane Doe",
                        "purpose": "Cleaning",
                        "start_time": "2026-08-20T16:30:00-07:00",
                        "duration_minutes": 60,
                        "user_confirmed": True,
                    },
                    expected_status="created",
                    capture="booking",
                ),
                EvalStep(
                    step_id="retry",
                    tool_name="create_appointment",
                    arguments={
                        "caller_name": "Jane Doe",
                        "purpose": "Cleaning",
                        "start_time": "2026-08-20T16:30:00-07:00",
                        "duration_minutes": 60,
                        "user_confirmed": True,
                    },
                    expected_status="already_booked",
                    expected_fields={"appointment.id": "${booking.appointment.id}"},
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.create_then_update",
            description="A created appointment can be updated using its returned id.",
            tags=("booking", "mutation", "confirmation"),
            steps=(
                EvalStep(
                    step_id="create",
                    tool_name="create_appointment",
                    arguments={
                        "caller_name": "Jane Doe",
                        "purpose": "Cleaning",
                        "start_time": "2026-08-20T16:30:00-07:00",
                        "duration_minutes": 60,
                        "caller_phone": "+15551234567",
                        "user_confirmed": True,
                    },
                    expected_status="created",
                    capture="booking",
                ),
                EvalStep(
                    step_id="update",
                    tool_name="update_appointment",
                    arguments={
                        "appointment_id": "${booking.appointment.id}",
                        "caller_email": "jane@example.com",
                        "user_confirmed": True,
                    },
                    expected_status="updated",
                    expected_fields={"appointment.caller_email": "jane@example.com"},
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.find_existing_appointment",
            description="Existing appointments are found by time window and optional caller data.",
            tags=("lookup", "mutation"),
            steps=(
                EvalStep(
                    step_id="find",
                    tool_name="find_appointments",
                    arguments={
                        "window_start": "2026-08-20T00:00:00-07:00",
                        "window_end": "2026-08-21T00:00:00-07:00",
                        "caller_email": "jane@example.com",
                    },
                    expected_status="ok",
                    expected_fields={
                        "appointments": [
                            {
                                "id": "target-appointment",
                                "start_time": "2026-08-20T10:30:00-07:00",
                                "end_time": "2026-08-20T11:30:00-07:00",
                                "duration_minutes": 60,
                                "summary": "Appointment: Jane Doe — Cleaning",
                            }
                        ]
                    },
                    capture="found",
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.update_existing_metadata",
            description="Updating email or details uses update, not availability search.",
            tags=("mutation", "safety"),
            steps=(
                EvalStep(
                    step_id="update",
                    tool_name="update_appointment",
                    arguments={
                        "appointment_id": "target-appointment",
                        "caller_email": "new@example.com",
                        "user_confirmed": True,
                    },
                    expected_status="updated",
                    expected_fields={"appointment.caller_email": "new@example.com"},
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.update_requires_confirmation",
            description="Changing an existing appointment without confirmation is a safe no-op.",
            tags=("mutation", "confirmation", "safety"),
            steps=(
                EvalStep(
                    step_id="update",
                    tool_name="update_appointment",
                    arguments={
                        "appointment_id": "target-appointment",
                        "caller_email": "new@example.com",
                        "user_confirmed": False,
                    },
                    expected_status="confirmation_required",
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.update_extension_excludes_self",
            description="Extending an appointment does not conflict with its old interval.",
            tags=("mutation", "conflict"),
            steps=(
                EvalStep(
                    step_id="extend",
                    tool_name="update_appointment",
                    arguments={
                        "appointment_id": "target-appointment",
                        "new_duration_minutes": 90,
                        "user_confirmed": True,
                    },
                    expected_status="updated",
                    expected_fields={"appointment.duration_minutes": 90},
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.update_conflict_is_reported",
            description="Moving an appointment onto another event returns a conflict.",
            tags=("mutation", "conflict", "safety"),
            steps=(
                EvalStep(
                    step_id="move",
                    tool_name="update_appointment",
                    arguments={
                        "appointment_id": "target-appointment",
                        "new_start_time": "2026-08-20T14:30:00-07:00",
                        "new_duration_minutes": 60,
                        "user_confirmed": True,
                    },
                    expected_status="busy",
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.cancel_requires_confirmation",
            description="Cancellation without confirmation is a safe no-op.",
            tags=("safety", "confirmation", "mutation"),
            steps=(
                EvalStep(
                    step_id="cancel",
                    tool_name="cancel_appointment",
                    arguments={
                        "appointment_id": "target-appointment",
                        "user_confirmed": False,
                    },
                    expected_status="confirmation_required",
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.cancel_success",
            description="A confirmed cancellation deletes the selected appointment.",
            tags=("mutation", "confirmation"),
            steps=(
                EvalStep(
                    step_id="cancel",
                    tool_name="cancel_appointment",
                    arguments={
                        "appointment_id": "target-appointment",
                        "user_confirmed": True,
                    },
                    expected_status="cancelled",
                ),
            ),
        ),
        EvalScenario(
            scenario_id="calendar.provider_outage_is_explicit",
            description="Provider failure becomes an explicit recoverable result.",
            tags=("reliability", "error-handling"),
            steps=(
                EvalStep(
                    step_id="check",
                    tool_name="check_availability",
                    arguments={
                        "start_time": "2026-08-20T10:30:00-07:00",
                        "duration_minutes": 60,
                    },
                    expected_status="error",
                    expected_code="temporary_failure",
                    expected_fields={
                        "error.next_action": "retry_later",
                        "error.retryable": True,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
    ]


async def run_calendar_suite(
    scenarios: list[EvalScenario] | None = None,
) -> SuiteResult:
    """Run the default Calendar appointment suite with isolated fake state."""
    selected = scenarios or build_calendar_scenarios()

    def adapter_factory(scenario: EvalScenario) -> EvalAdapter:
        seed = _scenario_seed(scenario.scenario_id)
        return CalendarEvalAdapter(**seed)

    return await run_suite(selected, adapter_factory)
