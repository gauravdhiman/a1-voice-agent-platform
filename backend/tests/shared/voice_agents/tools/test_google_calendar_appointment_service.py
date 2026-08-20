"""Contract tests for the organization-scoped Google Calendar appointment service."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

import httpx

from shared.voice_agents.tools import (
    google_calendar_appointment_service as service_module,
)
from shared.voice_agents.tools.google_calendar_appointment_service import (
    GoogleCalendarAppointmentService,
)


def _install_google_transport(
    monkeypatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Route service HTTP calls through a deterministic MockTransport."""
    monkeypatch.setattr(
        service_module,
        "_default_client_factory",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _service(
    monkeypatch,
    handler,
    *,
    now: datetime | None = None,
    idempotency_key: str | None = None,
) -> GoogleCalendarAppointmentService:
    """Build a service with the test clock and mocked Google transport."""
    _install_google_transport(monkeypatch, handler)
    return GoogleCalendarAppointmentService(
        access_token="oauth-token",
        calendar_id="primary",
        timezone_name="America/Phoenix",
        now_provider=lambda: now
        or datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Phoenix")),
        idempotency_key=idempotency_key,
    )


class TestGoogleCalendarAppointmentService:
    """Verify the small, model-facing appointment contract."""

    async def test_create_requires_current_user_confirmation_and_does_not_call_google(
        self, monkeypatch
    ) -> None:
        """A missing confirmation must be a safe no-op, not a pending booking."""
        called = False

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(500)

        service = _service(monkeypatch, handler)

        result = await service.create_appointment(
            caller_name="Jane Doe",
            purpose="Dental cleaning",
            start_time="2026-08-20T10:30:00-07:00",
            duration_minutes=60,
            caller_phone="+15551234567",
            user_confirmed=False,
        )

        assert result["status"] == "confirmation_required"
        assert called is False
        assert "appointment" in result["message"].lower()

    async def test_create_rechecks_availability_then_writes_normalized_event(
        self, monkeypatch
    ) -> None:
        """Confirmed booking checks the exact interval before inserting it."""
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path == "/calendar/v3/freeBusy":
                return httpx.Response(
                    200,
                    json={"calendars": {"business@example.com": {"busy": []}}},
                )
            assert request.url.path == "/calendar/v3/calendars/primary/events"
            body = json.loads(request.content)
            assert body["start"]["timeZone"] == "America/Phoenix"
            assert body["end"]["timeZone"] == "America/Phoenix"
            assert body["attendees"] == [{"email": "jane@example.com"}]
            assert "Date of birth" not in body.get("description", "")
            return httpx.Response(
                201,
                json={
                    "id": "event-123",
                    "htmlLink": "https://calendar.google.com/event/event-123",
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.create_appointment(
            caller_name="Jane Doe",
            purpose="Dental cleaning",
            start_time="2026-08-20T17:30:00Z",
            duration_minutes=60,
            caller_phone="+15551234567",
            caller_email="jane@example.com",
            notes="First visit",
            user_confirmed=True,
        )

        assert [request.method for request in requests] == ["POST", "POST"]
        assert result["status"] == "created"
        assert result["timezone"] == "America/Phoenix"
        assert result["appointment"] == {
            "id": "event-123",
            "start_time": "2026-08-20T10:30:00-07:00",
            "end_time": "2026-08-20T11:30:00-07:00",
            "duration_minutes": 60,
            "purpose": "Dental cleaning",
            "caller_name": "Jane Doe",
            "caller_email": "jane@example.com",
        }

    async def test_create_refuses_busy_slot_without_posting_event(
        self, monkeypatch
    ) -> None:
        """A fresh conflict check must prevent a double booking."""
        requests: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request.method)
            return httpx.Response(
                200,
                json={
                    "calendars": {
                        "primary": {
                            "busy": [
                                {
                                    "start": "2026-08-20T17:30:00Z",
                                    "end": "2026-08-20T18:30:00Z",
                                }
                            ]
                        }
                    }
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.create_appointment(
            caller_name="Jane Doe",
            purpose="Dental cleaning",
            start_time="2026-08-20T10:30:00-07:00",
            duration_minutes=60,
            user_confirmed=True,
        )

        assert result["status"] == "busy"
        assert requests == ["POST"]
        assert "no longer" in result["message"].lower()

    async def test_create_retry_merges_new_email_into_same_session_booking(
        self, monkeypatch
    ) -> None:
        """A repeated create request must update its own booking, not fail busy."""
        requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, request.url.path))
            if request.method == "POST":
                return httpx.Response(
                    200,
                    json={
                        "calendars": {
                            "primary": {
                                "busy": [
                                    {
                                        "start": "2026-08-20T17:30:00Z",
                                        "end": "2026-08-20T18:30:00Z",
                                    }
                                ]
                            }
                        }
                    },
                )
            if request.method == "GET":
                event_id = request.url.path.rsplit("/", 1)[-1]
                return httpx.Response(
                    200,
                    json={
                        "id": event_id,
                        "summary": "Appointment: Jane Doe — Dental cleaning",
                        "description": (
                            "Purpose: Dental cleaning\n"
                            "Phone: +15551234567\n"
                            "Booked by 24x7 AI appointment assistant."
                        ),
                        "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                        "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                    },
                )
            assert request.method == "PATCH"
            body = json.loads(request.content)
            assert body["attendees"] == [{"email": "jane@example.com"}]
            assert "Phone: +15551234567" in body["description"]
            assert "Email: jane@example.com" in body["description"]
            return httpx.Response(
                200,
                json={
                    "id": request.url.path.rsplit("/", 1)[-1],
                    "summary": "Appointment: Jane Doe — Dental cleaning",
                    "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                    "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                },
            )

        service = _service(
            monkeypatch,
            handler,
            idempotency_key="voice-session-1",
        )
        result = await service.create_appointment(
            caller_name="Jane Doe",
            purpose="Dental cleaning",
            start_time="2026-08-20T10:30:00-07:00",
            duration_minutes=60,
            caller_phone="+15551234567",
            caller_email="jane@example.com",
            user_confirmed=True,
        )

        assert result["status"] == "updated"
        assert (
            result["message"] == "Appointment details updated on the existing booking."
        )
        assert result["appointment"]["caller_email"] == "jane@example.com"
        assert [method for method, _path in requests] == ["POST", "GET", "PATCH"]

    async def test_create_refuses_interval_that_has_already_started(
        self, monkeypatch
    ) -> None:
        """A booking cannot begin in the past even when its end is in the future."""
        called = False

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(500)

        service = _service(monkeypatch, handler)
        result = await service.create_appointment(
            caller_name="Jane Doe",
            purpose="Cleaning",
            start_time="2026-08-20T07:30:00-07:00",
            duration_minutes=60,
            user_confirmed=True,
        )

        assert result["status"] == "past"
        assert called is False

    async def test_create_accepts_integer_like_duration_from_provider_adapters(
        self, monkeypatch
    ) -> None:
        """A provider coercion quirk must not make a valid booking impossible."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/calendar/v3/freeBusy":
                return httpx.Response(
                    200, json={"calendars": {"primary": {"busy": []}}}
                )
            return httpx.Response(201, json={"id": "event-typed"})

        service = _service(monkeypatch, handler)
        result = await service.create_appointment(
            caller_name="Jane Doe",
            purpose="Cleaning",
            start_time="2026-08-20T10:30:00-07:00",
            duration_minutes="60",
            user_confirmed=True,
        )

        assert result["status"] == "created"
        assert result["appointment"]["duration_minutes"] == 60

    async def test_find_available_slots_uses_org_timezone_and_handles_primary_alias(
        self, monkeypatch
    ) -> None:
        """Availability is a time-window search, independent of caller identity."""
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "calendars": {
                        "business@example.com": {
                            "busy": [
                                {
                                    "start": "2026-08-20T17:00:00Z",
                                    "end": "2026-08-20T18:00:00Z",
                                }
                            ]
                        }
                    }
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.find_available_slots(
            window_start="2026-08-20T09:00:00-07:00",
            window_end="2026-08-20T12:00:00-07:00",
            duration_minutes=60,
            slot_interval_minutes=30,
        )

        body = captured["body"]
        assert body["items"] == [{"id": "primary"}]
        assert result["timezone"] == "America/Phoenix"
        assert [(slot["start_time"], slot["end_time"]) for slot in result["slots"]] == [
            ("2026-08-20T09:00:00-07:00", "2026-08-20T10:00:00-07:00"),
            ("2026-08-20T11:00:00-07:00", "2026-08-20T12:00:00-07:00"),
        ]

    async def test_find_available_slots_drops_elapsed_starts_from_partial_window(
        self, monkeypatch
    ) -> None:
        """A partially elapsed search window must never return past starts."""

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"calendars": {"primary": {"busy": []}}})

        service = _service(monkeypatch, handler)
        result = await service.find_available_slots(
            window_start="2026-08-20T07:00:00-07:00",
            window_end="2026-08-20T09:00:00-07:00",
            duration_minutes=30,
            slot_interval_minutes=30,
        )

        assert result["slots"][0]["start_time"] == "2026-08-20T08:00:00-07:00"

    async def test_find_available_slots_aligns_candidates_to_local_clock_boundaries(
        self, monkeypatch
    ) -> None:
        """Rolling searches must not create second or arbitrary-minute starts."""

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"calendars": {"primary": {"busy": []}}})

        service = _service(monkeypatch, handler)
        result = await service.find_available_slots(
            window_start="2026-08-20T08:07:23-07:00",
            window_end="2026-08-20T10:00:00-07:00",
            duration_minutes=30,
            slot_interval_minutes=30,
        )

        assert [slot["start_time"] for slot in result["slots"]] == [
            "2026-08-20T08:30:00-07:00",
            "2026-08-20T09:00:00-07:00",
            "2026-08-20T09:30:00-07:00",
        ]
        assert all("." not in slot["start_time"] for slot in result["slots"])

    async def test_update_excludes_target_event_when_rechecking_new_slot(
        self, monkeypatch
    ) -> None:
        """Rescheduling an appointment must not conflict with its old copy."""
        requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, request.url.path))
            if request.method == "GET" and request.url.path.endswith("/event-123"):
                return httpx.Response(
                    200,
                    json={
                        "id": "event-123",
                        "summary": "Appointment: Jane Doe — Cleaning",
                        "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                        "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                    },
                )
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "event-123",
                                "summary": "Appointment: Jane Doe — Cleaning",
                                "start": {"dateTime": "2026-08-20T13:00:00-07:00"},
                                "end": {"dateTime": "2026-08-20T13:30:00-07:00"},
                            }
                        ]
                    },
                )
            assert request.method == "PATCH"
            body = json.loads(request.content)
            assert body["start"]["timeZone"] == "America/Phoenix"
            return httpx.Response(
                200,
                json={
                    "id": "event-123",
                    "start": {"dateTime": "2026-08-20T13:00:00-07:00"},
                    "end": {"dateTime": "2026-08-20T13:30:00-07:00"},
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.update_appointment(
            appointment_id="event-123",
            new_start_time="2026-08-20T13:00:00-07:00",
            new_duration_minutes=30,
            user_confirmed=True,
        )

        assert result["status"] == "updated"
        assert requests == [
            ("GET", "/calendar/v3/calendars/primary/events/event-123"),
            ("GET", "/calendar/v3/calendars/primary/events"),
            ("PATCH", "/calendar/v3/calendars/primary/events/event-123"),
        ]

    async def test_update_extension_excludes_target_event_from_its_new_interval(
        self, monkeypatch
    ) -> None:
        """Extending an appointment must not treat its original event as busy."""
        requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, request.url.path))
            if request.method == "GET" and request.url.path.endswith("/event-123"):
                return httpx.Response(
                    200,
                    json={
                        "id": "event-123",
                        "summary": "Appointment: Jane Doe — Cleaning",
                        "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                        "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                    },
                )
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "event-123",
                                "summary": "Appointment: Jane Doe — Cleaning",
                                "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                                "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                            }
                        ]
                    },
                )
            assert request.method == "PATCH"
            body = json.loads(request.content)
            assert body["start"]["dateTime"] == "2026-08-20T10:30:00-07:00"
            assert body["end"]["dateTime"] == "2026-08-20T12:00:00-07:00"
            return httpx.Response(
                200,
                json={
                    "id": "event-123",
                    "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                    "end": {"dateTime": "2026-08-20T12:00:00-07:00"},
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.update_appointment(
            appointment_id="event-123",
            new_duration_minutes=90,
            user_confirmed=True,
        )

        assert result["status"] == "updated"
        assert result["appointment"]["duration_minutes"] == 90
        assert result["appointment"]["end_time"] == "2026-08-20T12:00:00-07:00"
        assert requests == [
            ("GET", "/calendar/v3/calendars/primary/events/event-123"),
            ("GET", "/calendar/v3/calendars/primary/events"),
            ("PATCH", "/calendar/v3/calendars/primary/events/event-123"),
        ]

    async def test_update_caller_name_changes_summary_without_empty_patch(
        self, monkeypatch
    ) -> None:
        """A caller-name-only update must persist an actual calendar change."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "id": "event-123",
                        "summary": "Appointment: Jane Doe — Cleaning",
                        "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                        "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                    },
                )
            assert request.method == "PATCH"
            body = json.loads(request.content)
            assert body == {"summary": "Appointment: Janet Doe — Cleaning"}
            return httpx.Response(
                200,
                json={
                    "id": "event-123",
                    "summary": "Appointment: Janet Doe — Cleaning",
                    "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                    "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.update_appointment(
            appointment_id="event-123",
            caller_name="Janet Doe",
            user_confirmed=True,
        )

        assert result["status"] == "updated"
        assert result["appointment"]["caller_name"] == "Janet Doe"
        assert result["appointment"]["purpose"] == "Cleaning"

    async def test_update_email_preserves_other_event_attendees(
        self, monkeypatch
    ) -> None:
        """Updating the caller email must not remove business attendees."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "id": "event-123",
                        "summary": "Appointment: Jane Doe — Cleaning",
                        "description": (
                            "Purpose: Cleaning\n"
                            "Email: jane@example.com\n"
                            "Booked by 24x7 AI appointment assistant."
                        ),
                        "attendees": [
                            {"email": "jane@example.com"},
                            {"email": "provider@business.example"},
                        ],
                        "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                        "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                    },
                )
            assert request.method == "PATCH"
            body = json.loads(request.content)
            assert body["attendees"] == [
                {"email": "janet@example.com"},
                {"email": "provider@business.example"},
            ]
            return httpx.Response(
                200,
                json={
                    "id": "event-123",
                    "summary": "Appointment: Jane Doe — Cleaning",
                    "start": {"dateTime": "2026-08-20T10:30:00-07:00"},
                    "end": {"dateTime": "2026-08-20T11:30:00-07:00"},
                },
            )

        service = _service(monkeypatch, handler)
        result = await service.update_appointment(
            appointment_id="event-123",
            caller_email="janet@example.com",
            user_confirmed=True,
        )

        assert result["status"] == "updated"
