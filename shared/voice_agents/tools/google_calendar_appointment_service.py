"""Shared Google Calendar appointment-booking service.

The native tool and the in-process MCP connector both use this module.  Keeping
the Google API and booking rules here prevents the two exposed interfaces from
developing different confirmation, timezone, or double-booking behavior.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://www.googleapis.com/calendar/v3"
_TIMEOUT = 20.0
_MAX_SLOTS = 50
_PHONE_DIGITS = re.compile(r"\D+")


# Tests replace this seam with an httpx.MockTransport client.  The production
# path creates a short-lived client per Google operation and closes it in the
# same operation.
def _default_client_factory() -> httpx.AsyncClient:
    """Create the production Google HTTP client."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


class GoogleCalendarAppointmentService:
    """Book and manage appointments on one organization's Google Calendar.

    The service is deliberately transport-neutral.  A voice-native adapter and
    an MCP adapter construct it with the same OAuth token, calendar id, and
    organization timezone, then expose the same six operations to the model:
    availability search, exact availability, appointment search, create,
    update, and cancel.

    The service owns the operational safety rules that an LLM should not have
    to implement reliably: every datetime must carry a timezone, past windows
    are rejected, create/update performs a fresh conflict check immediately
    before writing, and create/update/cancel require an explicit confirmation
    flag.  The confirmation flag is request-scoped; this service does not store
    conversation state or treat a previous availability result as consent.

    Args:
        access_token: OAuth bearer for the organization's connected Google
            Calendar account.
        calendar_id: Calendar resource to read and write, normally ``primary``.
        timezone_name: IANA timezone configured for the organization or the
            selected calendar.  It is used for normalization and responses,
            not as a process-global setting.
        require_phone: Whether this organization's booking policy requires a
            phone number before creation.
        require_email: Whether this organization's booking policy requires an
            email address before creation.
        now_provider: Optional clock seam for deterministic tests.  Production
            callers should omit it so each operation uses the current time.
        idempotency_key: Optional session/action key used to make retried
            inserts addressable by a deterministic Google event id.
        client_factory: Optional HTTP client factory used by deterministic
            evaluations. Production callers should omit it.
    """

    def __init__(
        self,
        *,
        access_token: str,
        calendar_id: str = "primary",
        timezone_name: str = "UTC",
        require_phone: bool = False,
        require_email: bool = False,
        now_provider: Optional[Callable[[], datetime]] = None,
        idempotency_key: Optional[str] = None,
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        """Initialize a service for one connected organization calendar.

        ``client_factory`` is an optional transport seam for deterministic
        integration evaluations.  Production callers leave it unset and the
        service uses its normal short-lived HTTP client factory.
        """
        self.access_token = access_token.strip()
        self.calendar_id = calendar_id.strip() or "primary"
        self.timezone_name = timezone_name.strip() or "UTC"
        self.timezone = ZoneInfo(self.timezone_name)
        self.require_phone = require_phone
        self.require_email = require_email
        self.now_provider = now_provider
        self.idempotency_key = idempotency_key.strip() if idempotency_key else None
        self.client_factory = client_factory or _default_client_factory

    async def find_available_slots(
        self,
        *,
        window_start: str,
        window_end: str,
        duration_minutes: int,
        slot_interval_minutes: int = 30,
    ) -> dict[str, Any]:
        """Find free appointment starts inside a requested time window.

        Args:
            window_start: Inclusive ISO 8601 timestamp with an offset.
            window_end: Exclusive ISO 8601 timestamp with an offset.
            duration_minutes: Required appointment length.
            slot_interval_minutes: Distance between candidate starts.  This
                can be shorter than the duration to offer rolling starts.

        Returns:
            A stable result containing ``slots`` with ``start_time`` and
            ``end_time`` in the organization's timezone.  Caller identity is
            not used for this search.
        """
        parsed = self._parse_window(window_start, window_end)
        if isinstance(parsed, dict):
            return parsed
        start, end = parsed
        duration_minutes = self._coerce_int(duration_minutes)
        slot_interval_minutes = self._coerce_int(slot_interval_minutes)
        duration_error = self._validate_duration(duration_minutes)
        if duration_error:
            return duration_error
        if (
            not isinstance(slot_interval_minutes, int)
            or not 1 <= slot_interval_minutes <= 1440
        ):
            return self._error(
                "invalid_argument",
                "slot_interval_minutes must be between 1 and 1440.",
            )

        now = self._now()
        if end <= now:
            return self._past_interval(start, end)
        start = max(start, now)
        candidate = self._align_to_slot_grid(start, slot_interval_minutes)
        availability = await self._freebusy(start, end)
        if availability["status"] == "error":
            return availability
        busy = availability.get("busy_periods", [])
        slots: list[dict[str, Any]] = []
        delta = timedelta(minutes=duration_minutes)
        increment = timedelta(minutes=slot_interval_minutes)
        while candidate + delta <= end and len(slots) < _MAX_SLOTS:
            candidate_end = candidate + delta
            if not self._overlaps_any(candidate, candidate_end, busy):
                slots.append(
                    {
                        "start_time": self._format(candidate),
                        "end_time": self._format(candidate_end),
                    }
                )
            candidate += increment

        return self._with_context(
            {
                "status": "ok",
                "message": "Available appointment slots found.",
                "next_action": (
                    "proceed_to_booking" if slots else "ask_for_different_window"
                ),
                "window_start": self._format(start),
                "window_end": self._format(end),
                "duration_minutes": duration_minutes,
                "slots": slots,
            }
        )

    async def check_availability(
        self, *, start_time: str, duration_minutes: int
    ) -> dict[str, Any]:
        """Check one exact appointment interval without using caller details."""
        duration_minutes = self._coerce_int(duration_minutes)
        duration_error = self._validate_duration(duration_minutes)
        if duration_error:
            return duration_error
        parsed_start = self._parse_datetime(start_time, field="start_time")
        if isinstance(parsed_start, dict):
            return parsed_start
        start = parsed_start
        end = start + timedelta(minutes=duration_minutes)
        if start <= self._now():
            return self._past_interval(start, end)
        availability = await self._freebusy(start, end)
        if availability["status"] == "error":
            return availability
        if availability["status"] == "past":
            return self._with_context(
                {
                    "status": "past",
                    "message": "That time has already passed.",
                    "next_action": "choose_future_time",
                    "start_time": self._format(start),
                    "end_time": self._format(end),
                }
            )
        status = "busy" if availability.get("busy_periods") else "available"
        return self._with_context(
            {
                "status": status,
                "message": (
                    "That appointment time is available."
                    if status == "available"
                    else "That appointment time is already occupied."
                ),
                "next_action": (
                    "proceed_to_confirmation"
                    if status == "available"
                    else "choose_another_time"
                ),
                "start_time": self._format(start),
                "end_time": self._format(end),
                "duration_minutes": duration_minutes,
            }
        )

    async def find_appointments(
        self,
        *,
        window_start: str,
        window_end: str,
        caller_name: str = "",
        caller_phone: str = "",
        caller_email: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Find existing calendar appointments in a time window.

        Search is primarily temporal.  Optional caller fields are local
        filters over the compact event data returned by Google; they are not
        authentication and should not be treated as proof of identity.  The
        strongest identifier for later mutation is the returned appointment id.
        """
        parsed = self._parse_window(window_start, window_end)
        if isinstance(parsed, dict):
            return parsed
        limit = self._coerce_int(limit)
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            return self._error("invalid_argument", "limit must be between 1 and 50.")
        start, end = parsed
        status, body = await self._call_google(
            "GET",
            f"/calendars/{self.calendar_id}/events",
            params={
                "timeMin": self._format(start),
                "timeMax": self._format(end),
                "maxResults": limit,
                "singleEvents": "true",
                "orderBy": "startTime",
                "showDeleted": "false",
            },
        )
        if status != 200:
            return self._google_error(status, body)

        appointments = []
        for event in body.get("items", []) if isinstance(body, dict) else []:
            if event.get("status") == "cancelled":
                continue
            if not self._event_matches(event, caller_name, caller_phone, caller_email):
                continue
            compact = self._compact_event(event)
            if compact:
                appointments.append(compact)
        return self._with_context(
            {
                "status": "ok",
                "message": "Appointments found.",
                "appointments": appointments[:limit],
            }
        )

    async def create_appointment(
        self,
        *,
        caller_name: str,
        purpose: str,
        start_time: str,
        duration_minutes: int,
        caller_phone: str = "",
        caller_email: str = "",
        notes: str = "",
        user_confirmed: bool,
    ) -> dict[str, Any]:
        """Create an appointment after confirmation and a fresh conflict check."""
        duration_minutes = self._coerce_int(duration_minutes)
        validation = self._validate_booking_fields(
            caller_name=caller_name,
            purpose=purpose,
            caller_phone=caller_phone,
            caller_email=caller_email,
            notes=notes,
            duration_minutes=duration_minutes,
        )
        if validation:
            return validation
        parsed_start = self._parse_datetime(start_time, field="start_time")
        if isinstance(parsed_start, dict):
            return parsed_start
        start = parsed_start
        end = start + timedelta(minutes=duration_minutes)
        if start <= self._now():
            return self._past_interval(start, end)
        if not user_confirmed:
            return self._with_context(
                {
                    "status": "confirmation_required",
                    "message": "Ask the caller to confirm the appointment details before booking.",
                    "next_action": "ask_for_confirmation",
                    "start_time": self._format(start),
                    "end_time": self._format(end),
                }
            )

        event_id = self._deterministic_event_id(
            caller_name=caller_name,
            purpose=purpose,
            start=start,
            duration_minutes=duration_minutes,
        )
        availability = await self._freebusy(start, end)
        if availability["status"] == "error":
            return availability
        if availability["status"] == "past":
            return self._with_context(
                {
                    "status": "past",
                    "message": "That time has already passed.",
                    "next_action": "choose_future_time",
                    "start_time": self._format(start),
                    "end_time": self._format(end),
                }
            )
        if availability.get("busy_periods"):
            if event_id:
                existing = await self._get_event(event_id)
                if existing is not None:
                    retry_result = await self._merge_idempotent_create(
                        existing=existing,
                        appointment_id=event_id,
                        caller_name=caller_name,
                        purpose=purpose,
                        caller_phone=caller_phone,
                        caller_email=caller_email,
                        notes=notes,
                        start=start,
                        end=end,
                    )
                    if retry_result is not None:
                        return retry_result
            return self._with_context(
                {
                    "status": "busy",
                    "message": "That appointment time is no longer available.",
                    "next_action": "choose_another_time",
                    "start_time": self._format(start),
                    "end_time": self._format(end),
                }
            )

        summary = f"Appointment: {caller_name.strip()} — {purpose.strip()}"
        event: dict[str, Any] = {
            "summary": summary,
            "description": self._description(
                purpose=purpose,
                caller_phone=caller_phone,
                caller_email=caller_email,
                notes=notes,
            ),
            "start": {"dateTime": self._format(start), "timeZone": self.timezone_name},
            "end": {"dateTime": self._format(end), "timeZone": self.timezone_name},
        }
        if caller_email.strip():
            event["attendees"] = [{"email": caller_email.strip()}]
        if event_id:
            event["id"] = event_id

        status, body = await self._call_google(
            "POST",
            f"/calendars/{self.calendar_id}/events",
            params={"sendUpdates": "all" if caller_email.strip() else "none"},
            json_body=event,
        )
        if status == 409 and event_id:
            existing = await self._get_event(event_id)
            if existing is not None:
                return self._with_context(
                    {
                        "status": "created",
                        "message": "The appointment was already booked for this request.",
                        "appointment": self._appointment_from_values(
                            event_id, start, end, caller_name, purpose, caller_email
                        ),
                    }
                )
        if status not in (200, 201):
            return self._google_error(status, body)
        return self._with_context(
            {
                "status": "created",
                "message": "Appointment booked.",
                "appointment": self._appointment_from_values(
                    body.get("id", event_id),
                    start,
                    end,
                    caller_name,
                    purpose,
                    caller_email,
                ),
            }
        )

    async def _merge_idempotent_create(
        self,
        *,
        existing: dict[str, Any],
        appointment_id: str,
        caller_name: str,
        purpose: str,
        caller_phone: str,
        caller_email: str,
        notes: str,
        start: datetime,
        end: datetime,
    ) -> Optional[dict[str, Any]]:
        """Recover a same-session retry without creating a duplicate event.

        The model may repeat ``create_appointment`` after a caller supplies a
        missing email or phone number. The deterministic event id proves that
        this is the same booking request within the current voice session; it
        does not grant ownership of arbitrary calendar events. Only an event
        with the original interval, assistant-created summary, and booking
        marker is eligible for this recovery path.

        Args:
            existing: Google event returned for the deterministic retry id.
            appointment_id: Stable Google event id for the current session.
            caller_name: Caller name from the repeated booking request.
            purpose: Appointment purpose from the repeated booking request.
            caller_phone: Newly supplied or replacement caller phone.
            caller_email: Newly supplied or replacement caller email.
            notes: Newly supplied appointment notes.
            start: Normalized original appointment start.
            end: Normalized original appointment end.

        Returns:
            An ``updated`` or ``already_booked`` result when the event matches
            the same idempotent request; otherwise ``None`` so the caller gets
            the normal busy response for an unrelated calendar event.
        """
        if existing.get("status") == "cancelled":
            return None
        existing_start = self._event_datetime(existing.get("start"))
        existing_end = self._event_datetime(existing.get("end"))
        expected_summary = f"Appointment: {caller_name.strip()} — {purpose.strip()}"
        if (
            existing_start != start
            or existing_end != end
            or str(existing.get("summary") or "") != expected_summary
            or "Booked by 24x7 AI appointment assistant."
            not in str(existing.get("description") or "")
        ):
            return None

        existing_details = self._description_values(
            str(existing.get("description") or "")
        )
        existing_email = existing_details["email"] or self._first_attendee_email(
            existing.get("attendees")
        )
        resolved_phone = caller_phone.strip() or existing_details["phone"]
        resolved_email = caller_email.strip() or existing_email
        resolved_notes = notes.strip() or existing_details["notes"]
        patch: dict[str, Any] = {}

        if (
            caller_email.strip()
            and caller_email.strip().lower() != existing_email.lower()
        ):
            patch["attendees"] = self._replace_caller_attendee(
                existing.get("attendees"), existing_email, caller_email
            )
        if caller_phone.strip() or caller_email.strip() or notes.strip():
            patch["description"] = self._description(
                purpose=purpose,
                caller_phone=resolved_phone,
                caller_email=resolved_email,
                notes=resolved_notes,
            )

        if not patch:
            return self._with_context(
                {
                    "status": "already_booked",
                    "message": "The appointment was already booked for this request.",
                    "appointment": self._appointment_from_values(
                        appointment_id,
                        start,
                        end,
                        caller_name,
                        purpose,
                        resolved_email,
                    ),
                }
            )

        status, body = await self._call_google(
            "PATCH",
            f"/calendars/{self.calendar_id}/events/{appointment_id}",
            params={"sendUpdates": "all" if resolved_email else "none"},
            json_body=patch,
        )
        if status not in (200, 201):
            return self._google_error(status, body)
        return self._with_context(
            {
                "status": "updated",
                "message": "Appointment details updated on the existing booking.",
                "appointment": self._appointment_from_values(
                    appointment_id,
                    start,
                    end,
                    caller_name,
                    purpose,
                    resolved_email,
                ),
            }
        )

    async def update_appointment(
        self,
        *,
        appointment_id: str,
        new_start_time: str = "",
        new_duration_minutes: int = 0,
        new_purpose: str = "",
        caller_name: str = "",
        caller_phone: str = "",
        caller_email: str = "",
        notes: str = "",
        user_confirmed: bool,
    ) -> dict[str, Any]:
        """Update appointment details or move an appointment safely.

        When the time changes, the existing event is excluded from the
        conflict query so an appointment does not conflict with itself.
        """
        appointment_id = appointment_id.strip()
        if not appointment_id:
            return self._error("invalid_argument", "appointment_id is required.")
        if not user_confirmed:
            return self._with_context(
                {
                    "status": "confirmation_required",
                    "message": "Ask the caller to confirm the appointment changes before updating.",
                    "next_action": "ask_for_confirmation",
                }
            )
        if new_duration_minutes in (None, "", 0):
            new_duration_minutes = 0
        else:
            new_duration_minutes = self._coerce_int(new_duration_minutes)
        if (
            new_duration_minutes is None
            or new_duration_minutes < 0
            or new_duration_minutes > 1440
        ):
            return self._error(
                "invalid_argument",
                "new_duration_minutes must be between 1 and 1440 when provided.",
                field="new_duration_minutes",
                expected_format="positive integer from 1 through 1440",
                hint="Provide the final total appointment duration, not the number of extra minutes.",
            )

        status, existing = await self._call_google(
            "GET", f"/calendars/{self.calendar_id}/events/{appointment_id}"
        )
        if status != 200:
            return self._google_error(status, existing)
        old_start = self._event_datetime(existing.get("start"))
        old_end = self._event_datetime(existing.get("end"))
        if old_start is None or old_end is None:
            return self._error(
                "invalid_event", "The existing appointment has no timed interval."
            )

        start = old_start
        if new_start_time.strip():
            parsed_start = self._parse_datetime(new_start_time, field="new_start_time")
            if isinstance(parsed_start, dict):
                return parsed_start
            start = parsed_start
        duration = (
            new_duration_minutes
            if new_duration_minutes
            else int((old_end - old_start).total_seconds() // 60)
        )
        duration_error = self._validate_duration(
            duration,
            field=(
                "new_duration_minutes" if new_duration_minutes else "duration_minutes"
            ),
        )
        if duration_error:
            return duration_error
        end = start + timedelta(minutes=duration)
        time_changed = start != old_start or end != old_end
        if time_changed and start <= self._now():
            return self._past_interval(start, end)
        if not any(
            [
                time_changed,
                bool(new_purpose.strip()),
                bool(caller_name.strip()),
                bool(caller_phone.strip()),
                bool(caller_email.strip()),
                bool(notes.strip()),
            ]
        ):
            return self._error(
                "invalid_argument", "Provide at least one appointment change."
            )

        if time_changed:
            conflict = await self._event_list_conflict(start, end, appointment_id)
            if conflict["status"] == "error":
                return conflict
            if conflict.get("busy"):
                return self._with_context(
                    {
                        "status": "busy",
                        "message": "The new appointment time is occupied.",
                        "next_action": "choose_another_time",
                        "start_time": self._format(start),
                        "end_time": self._format(end),
                    }
                )

        patch: dict[str, Any] = {}
        existing_summary = str(existing.get("summary") or "")
        existing_name = self._name_from_summary(existing_summary)
        existing_purpose = self._purpose_from_summary(existing_summary)
        if new_purpose.strip() or caller_name.strip():
            resolved_name = caller_name.strip() or existing_name or "Caller"
            resolved_purpose = (
                new_purpose.strip()
                or existing_purpose
                or existing_summary
                or "Appointment"
            )
            patch["summary"] = f"Appointment: {resolved_name} — {resolved_purpose}"
        if time_changed:
            patch["start"] = {
                "dateTime": self._format(start),
                "timeZone": self.timezone_name,
            }
            patch["end"] = {
                "dateTime": self._format(end),
                "timeZone": self.timezone_name,
            }
        existing_description = str(existing.get("description") or "")
        existing_details = self._description_values(existing_description)
        if caller_email.strip():
            patch["attendees"] = self._replace_caller_attendee(
                existing.get("attendees"),
                existing_details["email"],
                caller_email,
            )
        if caller_phone.strip() or notes.strip() or caller_email.strip():
            patch["description"] = self._description(
                purpose=new_purpose or existing_purpose or existing_summary,
                caller_phone=caller_phone or existing_details["phone"],
                caller_email=caller_email or existing_details["email"],
                notes=notes or existing_details["notes"],
            )

        status, body = await self._call_google(
            "PATCH",
            f"/calendars/{self.calendar_id}/events/{appointment_id}",
            params={"sendUpdates": "all" if caller_email.strip() else "none"},
            json_body=patch,
        )
        if status not in (200, 201):
            return self._google_error(status, body)
        summary = str(
            body.get("summary")
            or patch.get("summary")
            or existing.get("summary")
            or "Appointment"
        )
        result_name = caller_name.strip() or self._name_from_summary(summary)
        result_purpose = (
            new_purpose.strip() or self._purpose_from_summary(summary) or summary
        )
        return self._with_context(
            {
                "status": "updated",
                "message": "Appointment updated.",
                "appointment": self._appointment_from_values(
                    appointment_id,
                    start,
                    end,
                    result_name,
                    result_purpose,
                    caller_email,
                ),
            }
        )

    async def cancel_appointment(
        self, *, appointment_id: str, user_confirmed: bool
    ) -> dict[str, Any]:
        """Cancel one appointment after explicit caller confirmation."""
        appointment_id = appointment_id.strip()
        if not appointment_id:
            return self._error("invalid_argument", "appointment_id is required.")
        if not user_confirmed:
            return self._with_context(
                {
                    "status": "confirmation_required",
                    "message": "Ask the caller to confirm cancellation before cancelling the appointment.",
                    "next_action": "ask_for_confirmation",
                }
            )
        status, body = await self._call_google(
            "DELETE", f"/calendars/{self.calendar_id}/events/{appointment_id}"
        )
        if status not in (200, 204):
            return self._google_error(status, body)
        return self._with_context(
            {"status": "cancelled", "message": "Appointment cancelled."}
        )

    async def _freebusy(self, start: datetime, end: datetime) -> dict[str, Any]:
        """Query Google freeBusy and normalize its calendar alias response."""
        if end <= start:
            return self._error(
                "invalid_argument", "The time window must end after it starts."
            )
        if end <= self._now():
            return self._with_context(
                {
                    "status": "past",
                    "message": "The requested time has already passed.",
                    "next_action": "choose_future_time",
                }
            )
        status, body = await self._call_google(
            "POST",
            "/freeBusy",
            json_body={
                "timeMin": self._format(start),
                "timeMax": self._format(end),
                "timeZone": self.timezone_name,
                "items": [{"id": self.calendar_id}],
            },
        )
        if status != 200:
            return self._google_error(status, body)
        busy = self._busy_blocks(body)
        return self._with_context({"status": "ok", "busy_periods": busy})

    async def _event_list_conflict(
        self, start: datetime, end: datetime, appointment_id: str
    ) -> dict[str, Any]:
        """Use event ids to exclude the appointment being moved."""
        status, body = await self._call_google(
            "GET",
            f"/calendars/{self.calendar_id}/events",
            params={
                "timeMin": self._format(start),
                "timeMax": self._format(end),
                "maxResults": 50,
                "singleEvents": "true",
                "orderBy": "startTime",
                "showDeleted": "false",
            },
        )
        if status != 200:
            return self._google_error(status, body)
        for event in body.get("items", []) if isinstance(body, dict) else []:
            if event.get("id") == appointment_id or event.get("status") == "cancelled":
                continue
            event_start = self._event_datetime(event.get("start"))
            event_end = self._event_datetime(event.get("end"))
            if event_start and event_end and event_start < end and start < event_end:
                return {"status": "ok", "busy": True}
        return {"status": "ok", "busy": False}

    async def _get_event(self, event_id: str) -> Optional[dict[str, Any]]:
        """Fetch an event used to resolve a retry after an idempotent insert."""
        status, body = await self._call_google(
            "GET", f"/calendars/{self.calendar_id}/events/{event_id}"
        )
        return body if status == 200 and isinstance(body, dict) else None

    async def _call_google(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> tuple[int, dict[str, Any]]:
        """Make one authenticated Google request with sanitized error logging."""
        if not self.access_token:
            return 401, {"error": {"message": "missing access token"}}
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        client = self.client_factory()
        try:
            response = await client.request(
                method,
                f"{_API_BASE}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
            if not response.content:
                return response.status_code, {}
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            return response.status_code, payload if isinstance(payload, dict) else {}
        except httpx.HTTPError as exc:
            logger.warning(
                "Google Calendar request failed method=%s path=%s error=%s",
                method,
                path,
                type(exc).__name__,
            )
            return 0, {}
        finally:
            await client.aclose()

    def _validate_booking_fields(self, **fields: Any) -> Optional[dict[str, Any]]:
        """Validate generic appointment policy before confirmation or I/O."""
        for name in ("caller_name", "purpose"):
            if not str(fields[name]).strip():
                return self._error(
                    "invalid_argument",
                    f"{name} is required.",
                    field=name,
                    hint=f"Provide a non-empty {name}.",
                )
        duration_error = self._validate_duration(
            fields["duration_minutes"], field="duration_minutes"
        )
        if duration_error:
            return duration_error
        if self.require_phone and not str(fields["caller_phone"]).strip():
            return self._error(
                "missing_customer_detail",
                "A phone number is required for this organization.",
                field="caller_phone",
                hint="Ask the caller for a phone number before booking.",
            )
        if self.require_email and not str(fields["caller_email"]).strip():
            return self._error(
                "missing_customer_detail",
                "An email address is required for this organization.",
                field="caller_email",
                hint="Ask the caller for an email address before booking.",
            )
        if len(str(fields["caller_name"])) > 200 or len(str(fields["purpose"])) > 300:
            return self._error("invalid_argument", "Appointment text is too long.")
        if len(str(fields["notes"])) > 2000:
            return self._error(
                "invalid_argument", "notes must be 2000 characters or fewer."
            )
        return None

    def _validate_duration(
        self, duration_minutes: Any, *, field: str = "duration_minutes"
    ) -> Optional[dict[str, Any]]:
        """Validate an appointment duration and explain how to correct it."""
        if not isinstance(duration_minutes, int) or not 1 <= duration_minutes <= 1440:
            return self._error(
                "invalid_argument",
                f"{field} must be a positive integer from 1 through 1440.",
                field=field,
                expected_format="positive integer from 1 through 1440",
                hint="Use the final total appointment duration in minutes.",
            )
        return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        """Coerce an integer-like provider value without accepting booleans."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    def _parse_datetime(
        self, value: str, *, field: Optional[str] = None
    ) -> datetime | dict[str, Any]:
        """Parse an offset-aware ISO timestamp and normalize it to org time.

        ``field`` is included in validation errors so a model can correct the
        exact argument instead of guessing which datetime was rejected.
        """
        expected_format = "ISO 8601 datetime with numeric UTC offset"
        example = self._now().replace(hour=10, minute=30, second=0, microsecond=0)
        hint = (
            "Include the UTC offset; for example, "
            f"{self._format(example)}. Do not send a naive local datetime."
        )
        if not isinstance(value, str) or not value.strip():
            return self._error(
                "invalid_argument",
                "A timezone-aware ISO datetime is required.",
                field=field,
                expected_format=expected_format,
                hint=hint,
            )
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return self._error(
                "invalid_argument",
                "Use an ISO 8601 datetime with a timezone offset.",
                field=field,
                expected_format=expected_format,
                hint=hint,
            )
        if parsed.tzinfo is None:
            return self._error(
                "invalid_argument",
                "The datetime must include a timezone offset.",
                field=field,
                expected_format=expected_format,
                hint=hint,
            )
        return parsed.astimezone(self.timezone)

    def _parse_window(
        self, window_start: str, window_end: str
    ) -> tuple[datetime, datetime] | dict[str, Any]:
        """Parse and validate an inclusive/exclusive search window."""
        start = self._parse_datetime(window_start, field="window_start")
        if isinstance(start, dict):
            return start
        end = self._parse_datetime(window_end, field="window_end")
        if isinstance(end, dict):
            return end
        if end <= start:
            return self._error(
                "invalid_argument", "window_end must be after window_start."
            )
        return start, end

    def _now(self) -> datetime:
        """Return current time in the organization's timezone."""
        current = (
            self.now_provider() if self.now_provider else datetime.now(self.timezone)
        )
        if current.tzinfo is None:
            current = current.replace(tzinfo=self.timezone)
        return current.astimezone(self.timezone)

    @staticmethod
    def _align_to_slot_grid(value: datetime, interval_minutes: int) -> datetime:
        """Round a candidate up to the local midnight-based slot grid.

        Availability searches may begin at the current instant or at an
        arbitrary caller-provided minute.  Using that instant as the first
        candidate creates starts such as ``10:07:23`` and can omit ordinary
        starts such as ``10:00``.  A local-midnight grid keeps returned times
        predictable while preserving the requested interval.

        Args:
            value: Timezone-aware candidate start in the organization's zone.
            interval_minutes: Positive distance between candidate starts.

        Returns:
            The earliest grid-aligned timestamp that is not before ``value``.
        """
        day_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed_seconds = int((value - day_start).total_seconds())
        interval_seconds = interval_minutes * 60
        remainder = elapsed_seconds % interval_seconds
        if remainder:
            value += timedelta(seconds=interval_seconds - remainder)
        return value.replace(second=0, microsecond=0)

    def _with_context(self, result: dict[str, Any]) -> dict[str, Any]:
        """Add timezone and execution time to every scheduling result."""
        return {
            "timezone": self.timezone_name,
            "current_time": self._format(self._now()),
            **result,
        }

    def _error(
        self,
        code: str,
        message: str,
        *,
        field: Optional[str] = None,
        hint: Optional[str] = None,
        expected_format: Optional[str] = None,
        retryable: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Build a stable, actionable, non-sensitive tool error.

        The top-level ``code`` and ``message`` remain for compatibility.  The
        nested ``error`` object gives model adapters structured recovery data:
        the field to correct, an expected format, a hint, a retry flag, and the
        next action implied by the error code.
        """
        next_actions = {
            "invalid_argument": "retry_with_corrected_arguments",
            "missing_customer_detail": "ask_for_missing_detail",
            "temporary_failure": "retry_later",
            "authentication_required": "reauthorize",
            "not_found": "ask_user_to_verify_appointment",
            "conflict": "choose_another_time",
        }
        details: dict[str, Any] = {
            "code": code,
            "message": message,
            "next_action": next_actions.get(code, "explain_failure"),
            "retryable": (
                retryable
                if retryable is not None
                else code in {"conflict", "temporary_failure"}
            ),
        }
        if field:
            details["field"] = field
        if expected_format:
            details["expected_format"] = expected_format
        if hint:
            details["hint"] = hint
        return self._with_context(
            {"status": "error", "code": code, "message": message, "error": details}
        )

    def _past_interval(self, start: datetime, end: datetime) -> dict[str, Any]:
        """Build the consistent response for an interval that cannot be booked."""
        return self._with_context(
            {
                "status": "past",
                "message": "That time has already passed.",
                "next_action": "choose_future_time",
                "start_time": self._format(start),
                "end_time": self._format(end),
            }
        )

    def _google_error(self, status: int, body: dict[str, Any]) -> dict[str, Any]:
        """Map Google HTTP failures to stable recovery codes."""
        if status in (401, 403):
            return self._error(
                "authentication_required",
                "Google Calendar authorization is unavailable.",
            )
        if status == 404:
            return self._error(
                "not_found", "The appointment or calendar could not be found."
            )
        if status == 409:
            return self._error(
                "conflict",
                "Google Calendar rejected the change because it conflicted with another update.",
            )
        if status == 429 or status >= 500 or status == 0:
            return self._error(
                "temporary_failure", "Google Calendar is temporarily unavailable."
            )
        return self._error(
            "provider_error", "Google Calendar could not complete that request."
        )

    def _busy_blocks(self, body: dict[str, Any]) -> list[dict[str, str]]:
        """Extract busy intervals even when ``primary`` resolves to an email key."""
        calendars = body.get("calendars") if isinstance(body, dict) else None
        if not isinstance(calendars, dict):
            return []
        direct = calendars.get(self.calendar_id)
        entries = [direct] if isinstance(direct, dict) else list(calendars.values())
        blocks: list[dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for block in entry.get("busy", []) or []:
                if (
                    not isinstance(block, dict)
                    or not block.get("start")
                    or not block.get("end")
                ):
                    continue
                blocks.append({"start": str(block["start"]), "end": str(block["end"])})
        return blocks

    def _overlaps_any(
        self, start: datetime, end: datetime, blocks: list[dict[str, str]]
    ) -> bool:
        """Return whether one candidate interval overlaps a busy block."""
        for block in blocks:
            block_start = self._parse_datetime(block.get("start", ""))
            block_end = self._parse_datetime(block.get("end", ""))
            if isinstance(block_start, dict) or isinstance(block_end, dict):
                continue
            if block_start < end and start < block_end:
                return True
        return False

    def _event_matches(
        self,
        event: dict[str, Any],
        caller_name: str,
        caller_phone: str,
        caller_email: str,
    ) -> bool:
        """Apply optional caller filters without treating them as identity proof."""
        summary = str(event.get("summary") or "")
        description = str(event.get("description") or "")
        attendees = " ".join(
            str(item.get("email") or "")
            for item in event.get("attendees", [])
            if isinstance(item, dict)
        )
        searchable = f"{summary} {description} {attendees}".lower()
        if caller_name.strip() and caller_name.strip().lower() not in searchable:
            return False
        if caller_email.strip() and caller_email.strip().lower() not in searchable:
            return False
        if caller_phone.strip():
            wanted = _PHONE_DIGITS.sub("", caller_phone)
            present = _PHONE_DIGITS.sub("", searchable)
            if wanted and wanted not in present:
                return False
        return True

    def _compact_event(self, event: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Convert a Google event into a safe appointment summary."""
        start = self._event_datetime(event.get("start"))
        end = self._event_datetime(event.get("end"))
        if not start or not end or not event.get("id"):
            return None
        return {
            "id": event["id"],
            "start_time": self._format(start),
            "end_time": self._format(end),
            "duration_minutes": int((end - start).total_seconds() // 60),
            "summary": str(event.get("summary") or "Appointment"),
        }

    def _event_datetime(self, span: Any) -> Optional[datetime]:
        """Parse a timed Google event span, ignoring all-day events."""
        if not isinstance(span, dict) or not span.get("dateTime"):
            return None
        value = self._parse_datetime(str(span["dateTime"]))
        return value if isinstance(value, datetime) else None

    def _appointment_from_values(
        self,
        appointment_id: Any,
        start: datetime,
        end: datetime,
        caller_name: str,
        purpose: str,
        caller_email: str,
    ) -> dict[str, Any]:
        """Build the stable appointment object returned after a mutation."""
        return {
            "id": appointment_id,
            "start_time": self._format(start),
            "end_time": self._format(end),
            "duration_minutes": int((end - start).total_seconds() // 60),
            "purpose": purpose.strip(),
            "caller_name": caller_name.strip(),
            "caller_email": caller_email.strip() or None,
        }

    def _description(
        self, *, purpose: str, caller_phone: str, caller_email: str, notes: str
    ) -> str:
        """Build a minimal event description without silently storing DOB/PHI."""
        lines = [f"Purpose: {purpose.strip()}"]
        if caller_phone.strip():
            lines.append(f"Phone: {caller_phone.strip()}")
        if caller_email.strip():
            lines.append(f"Email: {caller_email.strip()}")
        if notes.strip():
            lines.append(f"Notes: {notes.strip()}")
        lines.append("Booked by 24x7 AI appointment assistant.")
        return "\n".join(lines)

    def _deterministic_event_id(
        self, *, caller_name: str, purpose: str, start: datetime, duration_minutes: int
    ) -> Optional[str]:
        """Return a stable Google-compatible id for retries in one session."""
        if not self.idempotency_key:
            return None
        value = json.dumps(
            [
                self.idempotency_key,
                caller_name.strip().lower(),
                purpose.strip().lower(),
                self._format(start),
                duration_minutes,
            ],
            separators=(",", ":"),
        )
        return "a1" + hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _name_from_summary(summary: str) -> str:
        """Extract a best-effort display name from an assistant-created title."""
        prefix = "Appointment: "
        if summary.startswith(prefix):
            remainder = summary[len(prefix) :]
            return remainder.split(" — ", 1)[0].strip()
        return ""

    @staticmethod
    def _purpose_from_summary(summary: str) -> str:
        """Extract the purpose portion from an assistant-created title."""
        prefix = "Appointment: "
        if summary.startswith(prefix):
            remainder = summary[len(prefix) :]
            parts = remainder.split(" — ", 1)
            return parts[1].strip() if len(parts) == 2 else ""
        return ""

    @staticmethod
    def _description_values(description: str) -> dict[str, str]:
        """Read replaceable contact fields so partial updates preserve details."""
        values = {"phone": "", "email": "", "notes": ""}
        for line in description.splitlines():
            field, separator, value = line.partition(":")
            if separator and field.strip().lower() in values:
                values[field.strip().lower()] = value.strip()
        return values

    @staticmethod
    def _first_attendee_email(attendees: Any) -> str:
        """Return the first usable attendee email from an existing event."""
        for attendee in attendees if isinstance(attendees, list) else []:
            if isinstance(attendee, dict) and attendee.get("email"):
                return str(attendee["email"]).strip()
        return ""

    @staticmethod
    def _replace_caller_attendee(
        attendees: Any, existing_email: str, replacement_email: str
    ) -> list[dict[str, str]]:
        """Replace the stored caller invitee while retaining business invitees."""
        replacement = replacement_email.strip()
        normalized_existing = existing_email.strip().lower()
        result: list[dict[str, str]] = []
        replaced = False
        for attendee in attendees if isinstance(attendees, list) else []:
            if not isinstance(attendee, dict) or not attendee.get("email"):
                continue
            email = str(attendee["email"]).strip()
            if normalized_existing and email.lower() == normalized_existing:
                if not replaced:
                    result.append({"email": replacement})
                    replaced = True
                continue
            result.append({"email": email})
        if not replaced:
            result.insert(0, {"email": replacement})
        return result

    def _format(self, value: datetime) -> str:
        """Format a datetime with the organization timezone offset."""
        return value.astimezone(self.timezone).isoformat(timespec="seconds")
