"""Reference MCP servers for the new tool-integration path.

These are small, self-contained FastMCP servers that expose a tool contract over
Streamable HTTP. They serve two purposes:

1. **The first working MCP tool** — a platform ``platform_tools`` row with
   ``tool_source='mcp'`` can point at one of these servers and the worker will
   route to it via :mod:`shared.voice_agents.tools.mcp.dispatch`. See
   ``docs/03_implementation/mcp_integration_rfc.md``.
2. **Test fixtures** — the worker tests stand these up in-process on an
   ephemeral localhost port (see ``worker/tests/conftest.py``) to prove the
   platform's MCP plumbing end-to-end without third-party OAuth or external
   network.

The ``google_calendar`` server is an in-memory stand-in for the real Google
Calendar MCP server. It mirrors the tool contract of the legacy
``GoogleCalendarTool`` (``list_events`` / ``create_event`` / ``get_event`` /
``check_availability``) so the platform's MCP path is exercised against a
Google-Calendar-shaped tool. The module docstring of
:mod:`shared.voice_agents.tools.mcp.reference_servers.google_calendar`
documents how to swap the in-memory store for the real Google Calendar API
(per-user OAuth bearer injected by the dispatch layer).

The ``google_calendar_rest`` server is the **REST connector** — the path that
works with a **personal Gmail** today. It wraps Google's plain, GA, un-gated
Calendar REST API (``www.googleapis.com/calendar/v3``) and forwards the per-user
OAuth bearer (injected by the dispatch layer) to it. This bypasses the Google
Workspace Developer Preview gate that blocks Google's *remote* Calendar MCP
server (``calendarmcp.googleapis.com``) for personal-Gmail users. The
``Google_calendar_mcp`` ``platform_tools`` row points at this connector. See
:mod:`shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest`
and ``docs/03_implementation/mcp_connector_access_model.md``.
"""
from shared.voice_agents.tools.mcp.reference_servers.google_calendar import (
    build_google_calendar_server,
)
from shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest import (
    build_google_calendar_rest_server,
)

__all__ = ["build_google_calendar_server", "build_google_calendar_rest_server"]