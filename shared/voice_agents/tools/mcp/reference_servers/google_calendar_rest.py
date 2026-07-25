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

    This module is a small FastMCP server that exposes a Google-Calendar-shaped
    tool contract (``list_calendars`` / ``list_events`` / ``get_event`` /
    ``create_event`` / ``check_availability``) and, on each tool call, forwards
    the per-user OAuth bearer to the **REST API** (option 2). The platform points
    the ``Google_calendar_mcp`` ``platform_tools`` row at this server instead of
    Google's gated remote server, so the agent reads the caller's real calendar
    with a personal Gmail — no Workspace, no Preview wait.

    This is also the better long-term design: we own the tool schemas (clean,
    Gemini-friendly — no sanitization hack needed) and the error handling. If we
    later get Workspace Preview access, we can repoint the row at Google's remote
    server with no platform change (the dispatch layer is server-agnostic).

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
are granted by the existing ``Google_calendar_mcp`` OAuth config):
    - ``https://www.googleapis.com/auth/calendar`` (read/write) or
      ``calendar.events`` + ``calendar.calendarlist.readonly``.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import httpx
from mcp.server.fastmcp import Context, FastMCP

# Google Calendar REST API base. The REST API is GA and un-gated (unlike the
# Preview-gated calendarmcp.googleapis.com remote MCP server).
_API_BASE = "https://www.googleapis.com/calendar/v3"
_TIMEOUT = 20.0

# Testability seam: tests override this to return an httpx.AsyncClient backed by
# a MockTransport so no real network call is made. Default returns a real client.
_default_client_factory: Callable[[], httpx.AsyncClient] = lambda: httpx.AsyncClient(timeout=_TIMEOUT)


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
        {"id": c.get("id"), "summary": c.get("summary"), "primary": bool(c.get("primary"))}
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
    desc_lines.append("Booked by CogniNets voice agent.")

    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
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


async def check_availability_logic(
    token: str, time_min: str, time_max: str, calendar_id: str = "primary"
) -> dict:
    """Check whether a time window is free or busy on a calendar.

    Uses Google's freebusy endpoint.

    Args:
        token: The caller's OAuth access token.
        time_min: Window start (ISO 8601 with timezone).
        time_max: Window end (ISO 8601 with timezone).
        calendar_id: Calendar to check (default ``primary``).

    Returns:
        ``{"status": "free"}`` or ``{"status": "busy"}``, or an error dict on
        non-200.
    """
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": calendar_id}],
    }
    status, resp_body = await _call_google("POST", "/freeBusy", token, json_body=body)
    if status != 200:
        return _err(status, resp_body)
    busy = (resp_body.get("calendars", {}).get(calendar_id, {}) or {}).get("busy", [])
    return {"status": "busy" if busy else "free"}


def build_google_calendar_rest_server() -> FastMCP:
    """Build the Google Calendar REST connector MCP server.

    Returns:
        A FastMCP server named ``google-calendar-rest`` exposing five tools:
        ``list_calendars``, ``list_events``, ``get_event``, ``create_event``,
        ``check_availability``. Each forwards the caller's OAuth bearer (from
        the MCP request ``Authorization`` header, injected by the worker
        dispatch layer) to Google's Calendar REST API.
    """
    mcp = FastMCP("google-calendar-rest")

    @mcp.tool()
    async def list_calendars(ctx: Context) -> str:
        """List the calendars on the organization's Google account.

        This is the organization's (the business's) Google account, NOT the
        caller's. Use this only if the business keeps more than one calendar and
        you need to pick the right ``calendar_id``; otherwise book into
        ``primary`` (the default).

        Returns:
            JSON array of ``{id, summary, primary}`` for each calendar the
            business owns or is subscribed to.
        """
        return json.dumps(await list_calendars_logic(_bearer(ctx)))

    @mcp.tool()
    async def list_events(
        ctx: Context,
        time_min: str,
        time_max: str = "",
        max_results: int = 10,
        calendar_id: str = "primary",
    ) -> str:
        """List the organization's upcoming appointments within a time range.

        Use this to see what is already booked on the business's calendar (e.g.
        to answer "what does the doctor's schedule look like next week?"). This
        is the organization's calendar, not the caller's.

        Args:
            time_min: Window start (ISO 8601 WITH timezone),
                e.g. ``2026-07-22T00:00:00-07:00``. Always include the timezone;
                ask the caller for their timezone if you cannot infer it, and
                reason from the current date/time you were given.
            time_max: Window end (ISO 8601). Optional; when empty, events from
                ``time_min`` onward (bounded by ``max_results``).
            max_results: Maximum events to return (default 10).
            calendar_id: The organization's calendar to read (default
                ``primary`` — do not ask the caller for this).

        Returns:
            JSON array of ``{id, summary, start, end}`` sorted by start time.
        """
        return json.dumps(
            await list_events_logic(_bearer(ctx), time_min, time_max, max_results, calendar_id)
        )

    @mcp.tool()
    async def get_event(
        ctx: Context, event_id: str, calendar_id: str = "primary"
    ) -> str:
        """Fetch a single appointment by id from the organization's calendar.

        Use this to look up an existing appointment and read its details back to
        the caller (e.g. to confirm or reschedule). Find the ``event_id`` with
        ``list_events`` first.

        Args:
            event_id: The event id returned by ``list_events`` / ``create_event``.
            calendar_id: The organization's calendar owning the event (default
                ``primary`` — do not ask the caller for this).

        Returns:
            JSON object of the event (id, summary, start, end, html_link,
            attendees), or ``{"error": "not_found"}``.
        """
        return json.dumps(await get_event_logic(_bearer(ctx), event_id, calendar_id))

    @mcp.tool()
    async def create_event(
        ctx: Context,
        caller_name: str,
        purpose: str,
        start: str,
        duration_minutes: int = 30,
        caller_phone: str = "",
        caller_email: str = "",
        caller_dob: str = "",
        calendar_id: str = "primary",
    ) -> str:
        """Book an appointment on the ORGANIZATION'S Google Calendar (the
        business's calendar — NOT the caller's). You are the business's front
        desk; this writes the appointment into the business's calendar so the
        business knows who it is with.

        BEFORE you call this tool, you MUST complete these steps with the caller:
        1. COLLECT the caller's details: their full name (required), a contact
           phone number, an email address, and their date of birth or age when
           the business needs it (e.g. a dental or medical practice). Ask
           politely, one or two questions at a time — do NOT skip this and do
           NOT book for an unknown caller.
        2. Use ``check_availability`` to confirm the requested slot is free
           (avoid double-booking). If it is busy, propose the nearest free
           alternative and agree on it with the caller.
        3. READ BACK the appointment to the caller: the caller's name, the
           purpose, the date and time WITH the time zone, and the contact
           details you captured.
        4. Get the caller's EXPLICIT confirmation ("Shall I go ahead and book
           that for you?") BEFORE calling this tool. DO NOT book without
           explicit confirmation.

        Args:
            caller_name: The caller's full name — the appointment is for this
                person. Required; collect it from the caller before booking.
            purpose: Reason for the appointment in a few words (e.g.
                ``"Dental cleaning"``, ``"New patient consultation"``).
            start: Appointment start as ISO 8601 WITH timezone, e.g.
                ``2026-07-23T14:00:00-07:00``. Always include the timezone; ask
                the caller if you cannot infer it, and reason from the current
                date/time you were given.
            duration_minutes: Appointment length in minutes (default 30).
            caller_phone: Caller's phone number. Collect it before booking.
            caller_email: Caller's email address. If provided, the caller is
                added as an invitee. Collect it before booking.
            caller_dob: Caller's date of birth (``YYYY-MM-DD``) or age, when the
                business requires it.
            calendar_id: The organization's calendar to book into (default
                ``primary`` — the business's calendar). Do not ask the caller
                for this.

        Returns:
            JSON object ``{"id", "status": "created", "summary", "html_link"}``
            on success, or an error object.
        """
        return json.dumps(
            await create_event_logic(
                _bearer(ctx),
                caller_name,
                purpose,
                start,
                duration_minutes,
                caller_phone,
                caller_email,
                caller_dob,
                calendar_id,
            )
        )

    @mcp.tool()
    async def check_availability(
        ctx: Context, time_min: str, time_max: str, calendar_id: str = "primary"
    ) -> str:
        """Check whether a time window is free or busy on the organization's
        calendar. USE THIS BEFORE ``create_event`` to avoid double-booking.

        Args:
            time_min: Window start (ISO 8601 WITH timezone), e.g.
                ``2026-07-23T14:00:00-07:00``. Always include the timezone; ask
                the caller for their timezone if you cannot infer it.
            time_max: Window end (ISO 8601 WITH timezone).
            calendar_id: The organization's calendar to check (default
                ``primary`` — the business's calendar; do not ask the caller).

        Returns:
            JSON object ``{"status": "free"}`` or ``{"status": "busy"}``. If
            busy, propose the nearest free alternative to the caller.
        """
        return json.dumps(
            await check_availability_logic(_bearer(ctx), time_min, time_max, calendar_id)
        )

    return mcp


if __name__ == "__main__":
    # Run the connector as a standalone Streamable HTTP service so the worker
    # can point the ``Google_calendar_mcp`` platform_tools row at it. Configure
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