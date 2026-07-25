"""Full-pipeline e2e test for the Google Calendar MCP tool (Phase 3b).

Proves the platform's new MCP path works end-to-end for a Google-Calendar-shaped
tool: a ``platform_tools`` row marked ``tool_source='mcp'`` points at the
in-process Google Calendar MCP reference server
(:mod:`shared.voice_agents.tools.mcp.reference_servers.google_calendar`); the
worker's dispatch layer discovers the server's tools, synthesizes LiveKit
``RawFunctionTool`` wrappers, and the model-facing handlers invoke the remote
tools (``list_events`` / ``create_event`` / ``get_event`` /
``check_availability``) and return correct results.

This is the "first working MCP tool" milestone. The legacy ``GoogleCalendarTool``
is not touched — this is the parallel path (RFC §1.1). The in-memory server
mirrors the real Google Calendar tool contract; swapping in the real Google
Calendar API is documented in the reference server module (no platform-side
change needed — only the server internals change).
"""
import json

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.dispatch import build_mcp_livekit_tools

# Fixtures (google_calendar_mcp_url / google_calendar_mcp_config) come from
# conftest.py.

# Tool names the Google Calendar reference server exposes.
_EXPECTED_TOOL_NAMES = {
    "list_events",
    "create_event",
    "get_event",
    "check_availability",
}


class TestGoogleCalendarMcpDiscovery:
    """list_tools discovers the four calendar tools with typed schemas."""

    async def test_lists_all_four_tools(self, google_calendar_mcp_config):
        async with McpClient(google_calendar_mcp_config) as client:
            tools = await client.list_tools()

        assert {t.name for t in tools} == _EXPECTED_TOOL_NAMES

    async def test_create_event_has_typed_param_schema(self, google_calendar_mcp_config):
        async with McpClient(google_calendar_mcp_config) as client:
            tools = {t.name: t for t in await client.list_tools()}

        schema = tools["create_event"].input_schema
        props = schema.get("properties", {})
        # FastMCP derives these from the function signature.
        assert set(props.keys()) >= {"summary", "start", "end"}


class TestGoogleCalendarMcpFullPipeline:
    """build_mcp_livekit_tools -> invoke handlers end-to-end against the server."""

    async def test_create_then_list_then_get_event(self, google_calendar_mcp_config):
        tools, client = await build_mcp_livekit_tools(google_calendar_mcp_config)
        try:
            by_name = {t.info.name: t for t in tools}
            assert set(by_name.keys()) == _EXPECTED_TOOL_NAMES

            # 1. Availability before creating anything -> free.
            free = await by_name["check_availability"].__wrapped__(
                {"time_min": "2026-07-15T10:00:00Z", "time_max": "2026-07-15T11:00:00Z"}
            )
            assert json.loads(free)["status"] == "free"

            # 2. Create an event.
            created = await by_name["create_event"].__wrapped__(
                {
                    "summary": "MCP sync",
                    "start": "2026-07-15T10:00:00Z",
                    "end": "2026-07-15T10:30:00Z",
                }
            )
            created_data = json.loads(created)
            assert created_data["status"] == "created"
            event_id = created_data["id"]

            # 3. The window is now busy.
            busy = await by_name["check_availability"].__wrapped__(
                {"time_min": "2026-07-15T10:00:00Z", "time_max": "2026-07-15T11:00:00Z"}
            )
            assert json.loads(busy)["status"] == "busy"

            # 4. list_events returns the new event.
            listed = await by_name["list_events"].__wrapped__(
                {
                    "time_min": "2026-07-15T00:00:00Z",
                    "time_max": "2026-07-16T00:00:00Z",
                    "max_results": 10,
                }
            )
            listed_events = json.loads(listed)
            assert any(e["id"] == event_id for e in listed_events)
            assert listed_events[0]["summary"] == "MCP sync"

            # 5. get_event returns the full event.
            fetched = await by_name["get_event"].__wrapped__({"event_id": event_id})
            fetched_data = json.loads(fetched)
            assert fetched_data["id"] == event_id
            assert fetched_data["summary"] == "MCP sync"
        finally:
            await client.close()

    async def test_get_unknown_event_returns_not_found_payload(
        self, google_calendar_mcp_config
    ):
        # Application-level "not found" is a NORMAL text result carrying an
        # error payload — the MCP server only signals is_error=True for
        # protocol-level failures (unknown tool name, type-validation failures),
        # not for app-level misses. The model receives the payload and reasons
        # about it. (The is_error -> ToolError path is covered separately in
        # test_mcp_livekit_adapter.py against the calculator server.)
        tools, client = await build_mcp_livekit_tools(google_calendar_mcp_config)
        try:
            by_name = {t.info.name: t for t in tools}
            result = await by_name["get_event"].__wrapped__({"event_id": "does-not-exist"})
            assert json.loads(result) == {"error": "not_found"}
        finally:
            await client.close()

    async def test_unselected_functions_skips_calendar_tool(
        self, google_calendar_mcp_config
    ):
        # Disable `check_availability` for this agent (mirrors
        # agent_tools.unselected_functions); it must not appear in the tool list.
        tools, client = await build_mcp_livekit_tools(
            google_calendar_mcp_config,
            unselected_functions=["check_availability"],
        )
        try:
            names = {t.info.name for t in tools}
            assert names == _EXPECTED_TOOL_NAMES - {"check_availability"}
        finally:
            await client.close()