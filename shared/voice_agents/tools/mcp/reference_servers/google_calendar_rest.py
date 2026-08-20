"""Google Calendar REST connector — an MCP server that wraps Google's REST API.

This is the connector we point the platform's MCP path at so a voice agent can
read/write a user's Google Calendar using only that user's **personal Gmail**
OAuth token — **without** the Google Workspace Developer Preview enrollment
that gates Google's *remote* Calendar MCP server
(``calendarmcp.googleapis.com``).

Why this exists:
    Google ships two different Calendar integrations:
      1. **Google Workspace MCP** (``calendarmcp.googleapis.com``) — the remote
         MCP server. It is in **Developer Preview** and is gated by the Google
         Workspace Developer Preview Program, which (currently) requires a
         **Workspace** account. A personal Gmail cannot use it. This was the
         blocker behind "The caller does not have permission".
      2. **Google Calendar REST API** (``www.googleapis.com/calendar/v3``) — the
         plain, GA, un-gated REST API. It works with a **personal Gmail** OAuth
         token today (verified: it lists the user's calendars with the stored
         token).

    This module is a small FastMCP server that exposes the same six appointment
    operations as the native ``Google_calendar_appointment`` adapter and, on
    each tool call, forwards the per-user OAuth bearer to the **REST API**. The
    platform points the ``Google_calendar_appointment_mcp`` row at this server
    instead of Google's gated remote server, so the agent reads and writes the
    organization's real calendar with a personal Gmail — no Workspace Preview
    enrollment is required for the REST path.

    This is also the better long-term design: we own the tool schemas (clean,
    Gemini-friendly — no sanitization hack needed) and the error handling. If we
    later get Workspace Preview/GA access, we can add a provider adapter without
    changing the appointment-facing contract.

Auth model:
    The worker's dispatch layer
    (:func:`shared.voice_agents.tools.mcp.dispatch.mcp_server_config_from_agent_tool`)
    decrypts the user's stored OAuth ``access_token`` and injects it as
    ``Authorization: Bearer <token>`` into the MCP request headers. Each tool
    reads that header (:func:`_bearer`) and forwards it to Google. This server
    never handles token refresh — :class:`TokenRefreshService` keeps the stored
    token fresh and the dispatch layer re-reads it per session.

Testability:
    All Google HTTP calls go through the module-level ``_default_client_factory``
    seam, which tests override with an ``httpx.MockTransport``-backed client —
    no real network, no Google credentials. The pure ``*_logic`` functions are
    the unit boundary; the FastMCP wrappers are thin and covered by a full-pipeline
    integration test (in-process server + :class:`McpClient`).

Scopes required on the stored token (standard Google Calendar REST scopes; all
    are granted by the ``Google_calendar_appointment_mcp`` OAuth config):
    - ``https://www.googleapis.com/auth/calendar.events``
    - ``https://www.googleapis.com/auth/calendar.readonly``
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from shared.voice_agents.tools.google_calendar_appointment_service import (
    GoogleCalendarAppointmentService,
)

# Google Calendar REST API base. The REST API is GA and un-gated (unlike the
# Preview-gated calendarmcp.googleapis.com remote MCP server).
_API_BASE = "https://www.googleapis.com/calendar/v3"
_TIMEOUT = 20.0


# Testability seam: tests override this to return an httpx.AsyncClient backed by
# a MockTransport so no real network call is made. Default returns a real client.
def _default_client_factory() -> httpx.AsyncClient:
    """Create the production Google HTTP client."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


def _bearer(ctx: Context) -> str:
    """Extract the per-user OAuth bearer the dispatch layer injected.

    The worker's ``mcp_server_config_from_agent_tool`` injects the user's stored
    ``access_token`` as ``Authorization: Bearer <token>`` into the MCP request
    headers. FastMCP surfaces that header on the Starlette request reachable via
    ``ctx.request_context.request.headers``.

    Args:
        ctx: The FastMCP tool :class:`Context` for the in-flight call.

    Returns:
        The bare access token (the part after ``Bearer ``).

    Raises:
        ValueError: If the Authorization header is missing or not a Bearer
            scheme. This is a config error (dispatch must inject the token),
            not a normal runtime path; FastMCP surfaces the raised exception as
            an MCP ``is_error`` result so the agent relays it cleanly.
    """
    request = ctx.request_context.request
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise ValueError(
            "Google Calendar connector: missing Authorization bearer. The "
            "worker dispatch layer must inject the user's OAuth access_token "
            "as 'Authorization: Bearer <token>'."
        )
    return auth.split(" ", 1)[1]


async def _call_google(
    method: str,
    path: str,
    token: str,
    *,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> tuple[int, dict]:
    """Make one authenticated call to the Google Calendar REST API.

    Args:
        method: HTTP method (``GET`` / ``POST``).
        path: Path under ``_API_BASE``, e.g. ``/users/me/calendarList``.
        token: The user's OAuth access token (forwarded as a Bearer).
        params: Optional query-string parameters.
        json_body: Optional JSON request body.

    Returns:
        A ``(status_code, body)`` tuple. ``body`` is the parsed JSON response
        (``{}`` when the response has no content).
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    client = _default_client_factory()
    try:
        resp = await client.request(
            method,
            f"{_API_BASE}{path}",
            params=params,
            json=json_body,
            headers=headers,
        )
        body = resp.json() if resp.content else {}
        return resp.status_code, body
    finally:
        await client.aclose()


def _err(status: int, body: dict) -> dict:
    """Shape a Google error response into a small JSON-serializable error dict.

    Args:
        status: The HTTP status code Google returned.
        body: The parsed JSON error body (may contain ``error.message``).

    Returns:
        ``{"error": <message>, "status": <status>}``. Falls back to a status
        string when Google did not return a structured ``error.message``.
    """
    err_obj = body.get("error") if isinstance(body, dict) else None
    message = err_obj.get("message") if isinstance(err_obj, dict) else None
    if not message:
        message = f"Google Calendar API returned status {status}"
    return {"error": message, "status": status}


# --- pure logic (the unit boundary; testable with a MockTransport) ------------


async def list_calendars_logic(token: str) -> list[dict] | dict:
    """List the calendars on the caller's Google account.

    Args:
        token: The caller's OAuth access token.

    Returns:
        A list of ``{id, summary, primary}`` dicts, or an error dict on non-200.
    """
    status, body = await _call_google("GET", "/users/me/calendarList", token)
    if status != 200:
        return _err(status, body)
    return [
        {
            "id": c.get("id"),
            "summary": c.get("summary"),
            "primary": bool(c.get("primary")),
        }
        for c in body.get("items", [])
    ]


async def list_events_logic(
    token: str,
    time_min: str,
    time_max: str = "",
    max_results: int = 10,
    calendar_id: str = "primary",
) -> list[dict] | dict:
    """List calendar events overlapping a time range.

    Args:
        token: The caller's OAuth access token.
        time_min: Window start (ISO 8601 with timezone), e.g.
            ``2026-07-22T00:00:00-07:00``.
        time_max: Window end (ISO 8601). Optional; when empty, Google returns
            events from ``time_min`` onward (bounded by ``max_results``).
        max_results: Maximum events to return (default 10).
        calendar_id: Calendar to read (default ``primary``).

    Returns:
        A list of ``{id, summary, start, end}`` dicts sorted by start time, or
        an error dict on non-200. ``start``/``end`` use ``dateTime`` when present
        (timed events) and fall back to ``date`` (all-day events).
    """
    params = {
        "timeMin": time_min,
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    if time_max:
        params["timeMax"] = time_max
    status, body = await _call_google(
        "GET", f"/calendars/{calendar_id}/events", token, params=params
    )
    if status != 200:
        return _err(status, body)

    def _when(span: dict) -> str:
        # Timed events use "dateTime"; all-day events use "date".
        return (span or {}).get("dateTime") or (span or {}).get("date")

    return [
        {
            "id": e.get("id"),
            "summary": e.get("summary"),
            "start": _when(e.get("start")),
            "end": _when(e.get("end")),
        }
        for e in body.get("items", [])
    ]


async def get_event_logic(
    token: str, event_id: str, calendar_id: str = "primary"
) -> dict:
    """Fetch a single calendar event by id.

    Args:
        token: The caller's OAuth access token.
        event_id: The event id (as returned by ``list_events`` / ``create_event``).
        calendar_id: Calendar owning the event (default ``primary``).

    Returns:
        A dict with ``id`` / ``summary`` / ``start`` / ``end`` / ``html_link`` /
        ``attendees`` (list of emails), ``{"error": "not_found"}`` on 404, or an
        error dict on other non-200.
    """
    status, body = await _call_google(
        "GET", f"/calendars/{calendar_id}/events/{event_id}", token
    )
    if status != 200:
        if status == 404:
            return {"error": "not_found"}
        return _err(status, body)

    def _when(span: dict) -> str:
        return (span or {}).get("dateTime") or (span or {}).get("date")

    return {
        "id": body.get("id"),
        "summary": body.get("summary"),
        "start": _when(body.get("start")),
        "end": _when(body.get("end")),
        "html_link": body.get("htmlLink"),
        "attendees": [a.get("email") for a in body.get("attendees", [])],
    }


async def create_event_logic(
    token: str,
    caller_name: str,
    purpose: str,
    start: str,
    duration_minutes: int = 30,
    caller_phone: str = "",
    caller_email: str = "",
    caller_dob: str = "",
    calendar_id: str = "primary",
) -> dict:
    """Book an appointment on the organization's Google Calendar.

    This is the front-desk booking tool. The caller's details are formatted into
    a calendar event: the caller's name + purpose become the event summary, the
    contact details go in the description, and the caller's email (if any) is
    added as an invitee. The end time is computed from ``start`` +
    ``duration_minutes``.

    Args:
        token: The organization's OAuth access token (the business's account).
        caller_name: The caller's full name — the appointment is for this
            person. The agent MUST collect this before booking.
        purpose: Reason for the appointment in a few words (e.g.
            ``"Dental cleaning"``, ``"New patient consultation"``).
        start: Appointment start as ISO 8601 WITH timezone, e.g.
            ``2026-07-23T14:00:00-07:00``.
        duration_minutes: Appointment length in minutes (default 30).
        caller_phone: Caller's phone number. The agent should collect this
            before booking; it is stored in the event description.
        caller_email: Caller's email address. If provided, the caller is added
            as an invitee (and stored in the description).
        caller_dob: Caller's date of birth (``YYYY-MM-DD``) or age, when the
            business requires it (e.g. a dental or medical practice).
        calendar_id: The organization's calendar to book into (default
            ``primary`` — the business's calendar).

    Returns:
        ``{"id", "status": "created", "summary", "html_link"}`` on success, or
        an error dict on non-2xx.
    """
    summary = (
        f"Appointment: {caller_name} — {purpose}"
        if purpose
        else f"Appointment: {caller_name}"
    )
    desc_lines: list[str] = []
    if purpose:
        desc_lines.append(f"Purpose: {purpose}")
    if caller_phone:
        desc_lines.append(f"Phone: {caller_phone}")
    if caller_email:
        desc_lines.append(f"Email: {caller_email}")
    if caller_dob:
        desc_lines.append(f"Date of birth: {caller_dob}")
    desc_lines.append("Booked by 24x7 AI voice agent.")

    start_dt = _parse_iso_datetime(start)
    end_dt = (start_dt + timedelta(minutes=duration_minutes)).isoformat()

    body: dict = {
        "summary": summary,
        "description": "\n".join(desc_lines),
        "start": {"dateTime": start},
        "end": {"dateTime": end_dt},
    }
    if caller_email:
        body["attendees"] = [{"email": caller_email}]

    status, resp_body = await _call_google(
        "POST", f"/calendars/{calendar_id}/events", token, json_body=body
    )
    if status not in (200, 201):
        return _err(status, resp_body)
    return {
        "id": resp_body.get("id"),
        "status": "created",
        "summary": summary,
        "html_link": resp_body.get("htmlLink"),
    }


def _parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 timestamp, treating ``Z`` as UTC."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _availability_window_is_in_past(
    time_min: str,
    time_max: str,
    *,
    reference_now: datetime | None = None,
) -> bool:
    """Return True when the requested window starts before the reference instant.

    Args:
        time_min: Window start (ISO 8601 with timezone).
        time_max: Window end (ISO 8601 with timezone).
        reference_now: Optional fixed instant for tests; defaults to wall-clock
            ``now`` in the same timezone as ``time_min``.

    Returns:
        True when ``time_min`` is strictly before the reference instant, meaning
        the slot must not be offered or booked.
    """
    start = _parse_iso_datetime(time_min)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    now = reference_now or datetime.now(start.tzinfo)
    if now.tzinfo is None:
        now = now.replace(tzinfo=start.tzinfo)
    else:
        now = now.astimezone(start.tzinfo)
    # End before/at now also means the window is unusable (fully in the past).
    end = _parse_iso_datetime(time_max)
    if end.tzinfo is None:
        end = end.replace(tzinfo=start.tzinfo)
    else:
        end = end.astimezone(start.tzinfo)
    return end <= now or start < now


def _busy_blocks_from_freebusy(resp_body: dict, calendar_id: str) -> list:
    """Extract busy intervals from a Google freeBusy response for one calendar.

    Google's freeBusy API accepts ``"primary"`` in the request ``items`` list,
    but the response ``calendars`` map is keyed by the resolved calendar id
    (usually the account email), not the literal string ``"primary"``. Looking
    up only ``calendars[calendar_id]`` therefore misses busy blocks and
    incorrectly reports free.

    Args:
        resp_body: Parsed JSON body from ``POST /calendar/v3/freeBusy``.
        calendar_id: Calendar id requested in the freeBusy call (often
            ``primary``).

    Returns:
        List of busy interval dicts (``start`` / ``end``). Empty when the
        calendar is free or the response has no calendar entries.
    """
    calendars = resp_body.get("calendars") or {}
    if not isinstance(calendars, dict) or not calendars:
        return []

    direct = calendars.get(calendar_id)
    if isinstance(direct, dict):
        return list(direct.get("busy") or [])

    # ``primary`` (and any other alias) may resolve to a single email-keyed
    # entry. Aggregate busy blocks across all returned calendars for the query
    # so we never miss an occupied slot.
    busy: list = []
    for entry in calendars.values():
        if isinstance(entry, dict):
            busy.extend(list(entry.get("busy") or []))
    return busy


async def check_availability_logic(
    token: str,
    time_min: str,
    time_max: str,
    calendar_id: str = "primary",
    *,
    reference_now: datetime | None = None,
) -> dict:
    """Check whether a time window is free or busy on a calendar.

    Uses Google's freebusy endpoint. Rejects windows that start in the past so
    the agent cannot offer stale slots when the caller asks about "today".

    Args:
        token: The caller's OAuth access token.
        time_min: Window start (ISO 8601 with timezone).
        time_max: Window end (ISO 8601 with timezone).
        calendar_id: Calendar to check (default ``primary``).
        reference_now: Optional fixed instant for unit tests.

    Returns:
        ``{"status": "free"}`` or ``{"status": "busy"}``, ``{"status": "past"}``
        when the window is before the current time, or an error dict on non-200.
    """
    if _availability_window_is_in_past(time_min, time_max, reference_now=reference_now):
        return {
            "status": "past",
            "message": (
                "The requested time is before the current moment. Do not offer or "
                "book past slots. Suggest a future time and call "
                "check_availability again before stating it is free."
            ),
        }
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": calendar_id}],
    }
    status, resp_body = await _call_google("POST", "/freeBusy", token, json_body=body)
    if status != 200:
        return _err(status, resp_body)
    busy = _busy_blocks_from_freebusy(resp_body, calendar_id)
    return {"status": "busy" if busy else "free"}


def _header(ctx: Context, name: str, default: str = "") -> str:
    """Read one namespaced runtime header from the in-flight MCP request."""
    return str(ctx.request_context.request.headers.get(name, default) or default)


def _bool_header(ctx: Context, name: str) -> bool:
    """Read a boolean policy header emitted by the worker."""
    return _header(ctx, name).strip().lower() == "true"


def _appointment_service(ctx: Context) -> GoogleCalendarAppointmentService:
    """Build the shared service from OAuth and trusted runtime headers."""
    return GoogleCalendarAppointmentService(
        access_token=_bearer(ctx),
        calendar_id=_header(ctx, "x-247ai-calendar-id", "primary"),
        timezone_name=_header(ctx, "x-247ai-organization-timezone", "UTC"),
        require_phone=_bool_header(ctx, "x-247ai-require-phone"),
        require_email=_bool_header(ctx, "x-247ai-require-email"),
        idempotency_key=_header(ctx, "x-247ai-session-id") or None,
    )


def build_google_calendar_rest_server() -> FastMCP:
    """Build the platform-owned Google Calendar Appointment MCP server.

    The server exposes the same six operations as the native tool.  Calendar
    id, organization timezone, policy flags, and session id are request
    context supplied by the worker; they are intentionally not model-facing
    arguments.  The OAuth bearer is forwarded to Google's Calendar REST API.
    """
    mcp = FastMCP("google-calendar-appointment")

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True
        )
    )
    async def find_available_slots(
        ctx: Context,
        window_start: str,
        window_end: str,
        duration_minutes: int,
        slot_interval_minutes: int = 30,
    ) -> str:
        """Find future free appointment starts in a requested time window.

        Use this when the caller asks what times are open. The search is based
        on the organization's calendar and appointment duration, not caller
        name, phone, or email. Timestamps must be ISO 8601 with a timezone.
        Returned starts are aligned to predictable local clock boundaries; use
        the organization's normal interval, typically fifteen or thirty
        minutes, rather than deriving an interval from the current minute.
        """
        return json.dumps(
            await _appointment_service(ctx).find_available_slots(
                window_start=window_start,
                window_end=window_end,
                duration_minutes=duration_minutes,
                slot_interval_minutes=slot_interval_minutes,
            )
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True
        )
    )
    async def check_availability(
        ctx: Context, start_time: str, duration_minutes: int
    ) -> str:
        """Check one exact interval for a possible new appointment.

        Use this only when the caller is considering a new booking and there
        is no existing appointment being changed. If the caller wants to
        reschedule, extend, shorten, or edit an existing appointment, use
        ``update_appointment`` instead. Do not use this tool as a pre-check for
        an existing appointment because its own calendar event is busy by
        design; ``update_appointment`` performs the conflict check while
        excluding the appointment being changed.

        The result reports whether the requested interval is free or busy.
        """
        return json.dumps(
            await _appointment_service(ctx).check_availability(
                start_time=start_time, duration_minutes=duration_minutes
            )
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True
        )
    )
    async def find_appointments(
        ctx: Context,
        window_start: str,
        window_end: str,
        caller_name: str = "",
        caller_phone: str = "",
        caller_email: str = "",
        limit: int = 20,
    ) -> str:
        """Find existing appointments in a time window with optional caller filters.

        Time is the primary search key.  Caller details narrow the results but
        are not identity verification.  Use the returned appointment id only
        for a later update or cancellation; never read it to the caller.
        """
        return json.dumps(
            await _appointment_service(ctx).find_appointments(
                window_start=window_start,
                window_end=window_end,
                caller_name=caller_name,
                caller_phone=caller_phone,
                caller_email=caller_email,
                limit=limit,
            )
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True
        )
    )
    async def create_appointment(
        ctx: Context,
        caller_name: str,
        purpose: str,
        start_time: str,
        duration_minutes: int,
        user_confirmed: bool,
        caller_phone: str = "",
        caller_email: str = "",
        notes: str = "",
    ) -> str:
        """Book a business appointment on the organization's Google Calendar after explicit caller confirmation.

        Use this only when no existing appointment satisfies the caller's
        request. Do not use it to add or correct contact details or reschedule
        an appointment already returned by a tool; use ``update_appointment``
        with the returned ``appointment.id`` instead. A same-session retry is
        handled idempotently by the server so it cannot create a duplicate.

        Collect the caller's name and the business-required contact details, read back the purpose,
        date, time, duration, and contact details, then call with
        ``user_confirmed=true``.  The server performs a fresh exact conflict
        check immediately before writing, so an earlier availability result is
        not treated as a guarantee.  Do not put DOB, insurance, or other
        sensitive health information in notes unless the organization's policy
        explicitly permits calendar storage.
        """
        return json.dumps(
            await _appointment_service(ctx).create_appointment(
                caller_name=caller_name,
                purpose=purpose,
                start_time=start_time,
                duration_minutes=duration_minutes,
                caller_phone=caller_phone,
                caller_email=caller_email,
                notes=notes,
                user_confirmed=user_confirmed,
            )
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True
        )
    )
    async def update_appointment(
        ctx: Context,
        appointment_id: str,
        user_confirmed: bool,
        new_start_time: str = "",
        new_duration_minutes: int = 0,
        new_purpose: str = "",
        caller_name: str = "",
        caller_phone: str = "",
        caller_email: str = "",
        notes: str = "",
    ) -> str:
        """Update an existing appointment after caller confirmation.

        Use this for every change to an existing appointment: rescheduling or
        moving it, extending or shortening its duration, changing its purpose,
        or adding and correcting caller details. Do not call
        ``check_availability`` first; this operation checks the proposed
        interval and excludes the appointment being changed from its own
        conflict check. For a duration change, ``new_duration_minutes`` is the
        final total duration, not the number of minutes to add. For example,
        changing a 60-minute appointment to 90 minutes requires
        ``new_duration_minutes=90``. Omit ``new_start_time`` to keep the
        current start time. Never call ``create_appointment`` for an existing
        booking.

        The appointment id is the Google event id returned by
        ``create_appointment`` or ``find_appointments``; if it is not already
        known, find the matching appointment first and pass the returned id.
        Never invent an id.
        """
        return json.dumps(
            await _appointment_service(ctx).update_appointment(
                appointment_id=appointment_id,
                new_start_time=new_start_time,
                new_duration_minutes=new_duration_minutes,
                new_purpose=new_purpose,
                caller_name=caller_name,
                caller_phone=caller_phone,
                caller_email=caller_email,
                notes=notes,
                user_confirmed=user_confirmed,
            )
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=True
        )
    )
    async def cancel_appointment(
        ctx: Context, appointment_id: str, user_confirmed: bool
    ) -> str:
        """Cancel an appointment only after explicit caller confirmation."""
        return json.dumps(
            await _appointment_service(ctx).cancel_appointment(
                appointment_id=appointment_id, user_confirmed=user_confirmed
            )
        )

    return mcp


if __name__ == "__main__":
    # Run the connector as a standalone Streamable HTTP service so the worker
    # can point the ``Google_calendar_appointment_mcp`` platform_tools row at it. Configure
    # host/port via env vars; defaults bind to localhost on 8733.
    #
    #   python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest
    #
    # Then point the platform_tools row at ``http://127.0.0.1:8733/mcp`` (the
    # worker dispatch layer injects the user's OAuth bearer into the request
    # headers, which this connector forwards to Google's REST API).
    import asyncio
    import os

    import uvicorn

    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8733"))

    async def _serve() -> None:
        app = build_google_calendar_rest_server().streamable_http_app()
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(_serve())
