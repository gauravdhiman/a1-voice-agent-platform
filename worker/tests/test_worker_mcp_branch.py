"""Tests for the worker's MCP dispatch branch helper (Phase 3a).

``worker._integrate_mcp_agent_tool`` is the extracted Phase 3a branch: it
routes one MCP-sourced ``agent_tool`` through the remote MCP server path,
extending the per-agent LiveKit tool list and tracking the open client for
session-end cleanup. The legacy ``BaseTool`` path is not exercised here — this
is the parallel path (RFC §1.1).

The success case runs against the in-process FastMCP calculator reference
server (from ``conftest.py``), proving the branch wires a real MCP server's
tools into the LiveKit tool list end-to-end. The failure case points at a dead
URL and asserts the branch fails soft (logs + skips) without raising, so a
broken MCP server never blocks the rest of the agent's tools.
"""
from uuid import uuid4

import worker
from shared.voice_agents.tool_models import AgentTool, PlatformTool, ToolSource

_TS = "2024-01-01T00:00:00"


def _mcp_agent_tool(mcp_server_url: str, name: str = "Google_calendar_mcp") -> AgentTool:
    """Build an MCP-sourced AgentTool pointing at the given MCP server URL."""
    platform_tool = PlatformTool(
        id=str(uuid4()),
        name=name,
        description="Google Calendar via remote MCP server",
        requires_auth=True,
        auth_type="oauth2",
        is_active=True,
        tool_source=ToolSource.MCP,
        mcp_server_url=mcp_server_url,
        mcp_server_name="google-calendar",
        created_at=_TS,
        updated_at=_TS,
    )
    return AgentTool(
        id=str(uuid4()),
        agent_id=str(uuid4()),
        tool_id=platform_tool.id,
        config={},
        sensitive_config={"access_token": "user-token"},
        is_enabled=True,
        created_at=_TS,
        updated_at=_TS,
        tool=platform_tool,
    )


class TestIntegrateMcpAgentTool:
    """The extracted worker MCP branch: success and fail-soft behavior."""

    async def test_success_extends_tools_and_tracks_client(self, mcp_server_url):
        agent_tool = _mcp_agent_tool(mcp_server_url)
        livekit_tools: list = []
        mcp_clients: list = []
        enabled_tool_names: list = []

        await worker._integrate_mcp_agent_tool(
            agent_tool, livekit_tools, mcp_clients, enabled_tool_names
        )

        try:
            # The calculator server exposes two tools; both get synthesized.
            assert len(livekit_tools) == 2
            names = {t.info.name for t in livekit_tools}
            assert names == {"add", "multiply"}
            # The open client is tracked for session-end cleanup.
            assert len(mcp_clients) == 1
            assert mcp_clients[0]._closed is False
            # The tool name is recorded for the prompt builder.
            assert enabled_tool_names == ["Google_calendar_mcp"]
        finally:
            for c in mcp_clients:
                await c.close()

    async def test_synthesized_tool_invokes_mcp_server(self, mcp_server_url):
        agent_tool = _mcp_agent_tool(mcp_server_url)
        livekit_tools: list = []
        mcp_clients: list = []
        enabled_tool_names: list = []

        await worker._integrate_mcp_agent_tool(
            agent_tool, livekit_tools, mcp_clients, enabled_tool_names
        )

        try:
            add_tool = next(t for t in livekit_tools if t.info.name == "add")
            result = await add_tool.__wrapped__({"a": 10, "b": 20})
            assert result.strip() == "30"
        finally:
            for c in mcp_clients:
                await c.close()

    async def test_failure_is_soft_and_does_not_raise(self):
        # A URL pointing at a closed port must not raise out of the branch.
        agent_tool = _mcp_agent_tool("http://127.0.0.1:1/mcp")  # port 1: unreachable
        livekit_tools: list = []
        mcp_clients: list = []
        enabled_tool_names: list = []

        # No exception propagates — the branch logs and skips.
        await worker._integrate_mcp_agent_tool(
            agent_tool, livekit_tools, mcp_clients, enabled_tool_names
        )

        assert livekit_tools == []
        assert mcp_clients == []
        assert enabled_tool_names == []