"""Google Calendar MCP reference server (Phase 3b — first working MCP tool).

A self-contained FastMCP server that exposes a Google-Calendar-shaped tool
contract over Streamable HTTP. It mirrors the function set of the legacy
in-tree ``GoogleCalendarTool`` (``list_events``, ``create_event``,
``get_event``, ``check_availability``) so the platform's MCP path can be
exercised against a calendar tool without standing up real Google OAuth.

This module is BOTH:

- **The first working MCP tool.** A ``platform_tools`` row with
  ``tool_source='mcp'`` and ``mcp_server_url`` pointed at a running instance of
  this server is routed through the worker's MCP dispatch
  (:mod:`shared.voice_agents.tools.mcp.dispatch`). See
  ``docs/03_implementation/mcp_integration_rfc.md``.
- **A reference implementation.** It demonstrates the contract a real
  Google Calendar MCP server should expose so it can be a drop-in replacement.

Storage:
    Events are kept in an in-memory list on the returned server object
    (``server.events``). This is intentionally process-local: it makes the server
    deterministic for tests and obvious to reason about. It is NOT a real
    calendar backend.

Swapping in the REAL Google Calendar API:
    Replace each tool function body with a call to the Google Calendar REST API
    (``https://www.googleapis.com/calendar/v3/...``) using the per-user OAuth
    bearer that the dispatch layer injects as ``Authorization: Bearer <token>``
    (see :func:`shared.voice_agents.tools.mcp.dispatch.mcp_server_config_from_agent_tool`).
    The tool signatures and JSON Schemas stay identical, so no platform-side
    change is needed — only the server's internals change. Required Google
    OAuth config:

      - OAuth client (GCP) with redirect URIs for the MCP server host.
      - Scopes: ``https://www.googleapis.com/auth/calendar.events`` and
        ``https://www.googleapis.com/auth/calendar.readonly`` (same as the
        legacy ``GoogleCalendarTool.AuthConfig.scopes``).
      - The user's ``access_token`` (and ``refresh_token``) are stored in the
        ``agent_tools.sensitive_config`` (encrypted, auto-refreshed by
        ``TokenRefreshService``); the dispatch layer decrypts and injects the
        bearer, so this server never handles refresh logic.

    Live-testing against the real Google API requires those credentials, which
    are not present in this dev environment; the in-memory server below is the
    testable proof of the platform plumbing. See
    ``docs/03_implementation/mcp_integration_rfc.md`` §6 for the auth hard parts.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

# Module-level default window used when ``time_max`` is omitted. Kept small so
# list_events stays bounded and deterministic in tests.
_DEFAULT_WINDOW_DAYS = 30


def _parse_iso(value: str) -> datetime:
    """Parse an ISO 8601 timestamp into an aware datetime.

    Args:
        value: ISO 8601 timestamp, e.g. ``2026-07-15T09:00:00Z`` or
            ``2026-07-15T09:00:00+02:00``.

    Returns:
        Timezone-aware datetime. Naive inputs are assumed UTC.

    Raises:
        ValueError: If ``value`` is not a valid ISO 8601 timestamp.
    """
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt: datetime) -> str:
    """Render a datetime as an ISO 8601 UTC string."""
    return dt.astimezone(timezone.utc).isoformat()


def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Return True if [start_a, end_a) overlaps [start_b, end_b)."""
    return start_a < end_b and start_b < end_a


def build_google_calendar_server() -> FastMCP:
    """Build the in-memory Google Calendar MCP reference server.

    Returns:
        A FastMCP server named ``google-calendar`` exposing four tools:
        ``list_events``, ``create_event``, ``get_event``, ``check_availability``.
        The server carries an ``events`` list attribute (in-memory store) so
        callers/tests can inspect or seed state.
    """
    mcp = FastMCP("google-calendar")
    # In-memory event store. Each event: {id, summary, start, end, attendees}.
    # Attached to the server instance so tests can inspect/seed it.
    mcp.events: list[dict[str, Any]] = []  # type: ignore[attr-defined]

    @mcp.tool()
    def list_events(time_min: str, time_max: str = "", max_results: int = 10) -> str:
        """List calendar events within a time range.

        Args:
            time_min: Start of the window (ISO 8601, with timezone), e.g.
                ``2026-07-15T00:00:00Z``.
            time_max: End of the window (ISO 8601). Optional; defaults to
                ``time_min`` + 30 days.
            max_results: Maximum number of events to return (default 10).

        Returns:
            JSON array of events (id, summary, start, end) overlapping the
            window, sorted by start time, capped at ``max_results``.
        """
        start = _parse_iso(time_min)
        end = _parse_iso(time_max) if time_max else start + timedelta(days=_DEFAULT_WINDOW_DAYS)
        matching = [
            e
            for e in mcp.events  # type: ignore[attr-defined]
            if _overlaps(start, end, _parse_iso(e["start"]), _parse_iso(e["end"]))
        ]
        matching.sort(key=lambda e: e["start"])
        capped = matching[:max_results]
        return json.dumps(
            [{"id": e["id"], "summary": e["summary"], "start": e["start"], "end": e["end"]} for e in capped]
        )

    @mcp.tool()
    def create_event(summary: str, start: str, end: str) -> str:
        """Create a calendar event.

        Args:
            summary: Event title / summary.
            start: Event start (ISO 8601, with timezone).
            end: Event end (ISO 8601, with timezone). Must be after ``start``.

        Returns:
            JSON object with the created event's ``id`` (e.g.
            ``{"id": "evt-...", "status": "created"}``).
        """
        start_dt = _parse_iso(start)
        end_dt = _parse_iso(end)
        if end_dt <= start_dt:
            return json.dumps({"error": "end must be after start"})
        event = {
            "id": f"evt-{uuid.uuid4().hex[:12]}",
            "summary": summary,
            "start": _iso(start_dt),
            "end": _iso(end_dt),
            "attendees": [],
        }
        mcp.events.append(event)  # type: ignore[attr-defined]
        return json.dumps({"id": event["id"], "status": "created"})

    @mcp.tool()
    def get_event(event_id: str) -> str:
        """Fetch a single calendar event by id.

        Args:
            event_id: The event id returned by ``create_event``.

        Returns:
            JSON object of the event, or ``{"error": "not_found"}``.
        """
        for e in mcp.events:  # type: ignore[attr-defined]
            if e["id"] == event_id:
                return json.dumps(e)
        return json.dumps({"error": "not_found"})

    @mcp.tool()
    def check_availability(time_min: str, time_max: str) -> str:
        """Check whether a window is free or busy.

        Args:
            time_min: Window start (ISO 8601, with timezone).
            time_max: Window end (ISO 8601, with timezone).

        Returns:
            JSON object ``{"status": "free"}`` or ``{"status": "busy"}``.
            Busy if any existing event overlaps the window.
        """
        start = _parse_iso(time_min)
        end = _parse_iso(time_max)
        for e in mcp.events:  # type: ignore[attr-defined]
            if _overlaps(start, end, _parse_iso(e["start"]), _parse_iso(e["end"])):
                return json.dumps({"status": "busy"})
        return json.dumps({"status": "free"})

    return mcp


if __name__ == "__main__":
    # Run the reference server as a standalone Streamable HTTP service so it can
    # be deployed as its own container and pointed at by a ``platform_tools`` row
    # with ``tool_source='mcp'``. Configure host/port via env vars; defaults bind
    # to all interfaces on 8000 (container-friendly).
    #
    #   python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar
    #
    # Then point a platform_tools row at ``http://<host>:8000/mcp``.
    import asyncio
    import os

    import uvicorn

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    async def _serve() -> None:
        app = build_google_calendar_server().streamable_http_app()
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(_serve())