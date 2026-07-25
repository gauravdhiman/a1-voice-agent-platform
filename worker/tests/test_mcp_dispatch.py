"""Tests for the worker MCP dispatch helpers (Phase 3a).

These cover the two pieces the worker needs to route an MCP-sourced
``platform_tools`` row through the new path while the legacy ``BaseTool`` path
stays untouched (coexistence, RFC §1.1):

  - :func:`mcp_server_config_from_agent_tool` — builds an
    :class:`McpServerConfig` from the row's ``mcp_server_*`` fields and injects
    the per-user OAuth bearer from the agent_tool's decrypted
    ``sensitive_config``.
  - :func:`build_mcp_livekit_tools` — opens an :class:`McpClient`, discovers the
    server's tools, filters out ``unselected_functions``, and synthesizes a
    LiveKit ``RawFunctionTool`` per tool. Returns the tools **and** the client
    (the caller owns the client's lifecycle; the tool handlers hold a reference
    to it, so it must stay open for the agent session).

Red-green: written FIRST. It fails at collection because
``shared.voice_agents.tools.mcp.dispatch`` does not exist yet.
"""
import pytest
from uuid import uuid4

from shared.voice_agents.tool_models import AgentTool, PlatformTool, ToolSource
from shared.voice_agents.tools.mcp.dispatch import (
    build_mcp_livekit_tools,
    mcp_server_config_from_agent_tool,
)

# Reference MCP server fixtures (mcp_server_url / mcp_server_config) come from
# conftest.py.

_TS = "2024-01-01T00:00:00"


def _mcp_platform_tool(**over) -> PlatformTool:
    base = dict(
        id=str(uuid4()),
        name="Google_calendar_mcp",
        description="Google Calendar via remote MCP server",
        requires_auth=True,
        auth_type="oauth2",
        is_active=True,
        tool_source=ToolSource.MCP,
        mcp_server_url="https://calendar-mcp.example.com/mcp",
        mcp_server_headers={"X-Api-Key": "server-level-key"},
        mcp_server_name="google-calendar",
        created_at=_TS,
        updated_at=_TS,
    )
    base.update(over)
    return PlatformTool(**base)


def _agent_tool(platform_tool: PlatformTool, sensitive_config=None) -> AgentTool:
    return AgentTool(
        id=str(uuid4()),
        agent_id=str(uuid4()),
        tool_id=str(platform_tool.id),
        config={"calendar_id": "primary"},
        sensitive_config=sensitive_config,
        is_enabled=True,
        created_at=_TS,
        updated_at=_TS,
        tool=platform_tool,
    )


class TestMcpServerConfigFromAgentTool:
    """Build an McpServerConfig from an MCP-sourced agent_tool."""

    def test_carries_url_name_and_static_headers(self):
        agent_tool = _agent_tool(_mcp_platform_tool())
        config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.url == "https://calendar-mcp.example.com/mcp"
        assert config.name == "google-calendar"
        assert config.headers["X-Api-Key"] == "server-level-key"

    def test_injects_per_user_oauth_bearer_from_sensitive_config(self):
        agent_tool = _agent_tool(
            _mcp_platform_tool(), sensitive_config={"access_token": "user-token-123"}
        )
        config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["Authorization"] == "Bearer user-token-123"

    def test_no_bearer_when_sensitive_config_missing_access_token(self):
        agent_tool = _agent_tool(_mcp_platform_tool(), sensitive_config={})
        config = mcp_server_config_from_agent_tool(agent_tool)

        assert "Authorization" not in config.headers

    def test_does_not_overwrite_existing_authorization_header(self):
        # Server-level Authorization (rare but valid) must not be clobbered by
        # the per-user token.
        pt = _mcp_platform_tool(
            mcp_server_headers={"Authorization": "Bearer server-side-token"}
        )
        agent_tool = _agent_tool(pt, sensitive_config={"access_token": "user-token"})
        config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["Authorization"] == "Bearer server-side-token"

    def test_name_defaults_to_tool_name_when_mcp_server_name_unset(self):
        pt = _mcp_platform_tool(mcp_server_name=None)
        agent_tool = _agent_tool(pt)
        config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.name == "Google_calendar_mcp"


class TestBuildMcpLivekitTools:
    """build_mcp_livekit_tools discovers, filters, and synthesizes LiveKit tools."""

    async def test_returns_one_livekit_tool_per_server_tool(self, mcp_server_config):
        tools, client = await build_mcp_livekit_tools(mcp_server_config)

        try:
            names = {t.info.name for t in tools}
            assert names == {"add", "multiply"}
        finally:
            await client.close()

    async def test_filters_unselected_functions(self, mcp_server_config):
        tools, client = await build_mcp_livekit_tools(
            mcp_server_config, unselected_functions=["multiply"]
        )

        try:
            names = {t.info.name for t in tools}
            assert names == {"add"}
        finally:
            await client.close()

    async def test_synthesized_tool_invokes_mcp_server(self, mcp_server_config):
        # The synthesized LiveKit tool's handler must reach the MCP server.
        tools, client = await build_mcp_livekit_tools(mcp_server_config)

        try:
            add_tool = next(t for t in tools if t.info.name == "add")
            result = await add_tool.__wrapped__({"a": 6, "b": 7})
            assert result.strip() == "13"
        finally:
            await client.close()

    async def test_returned_client_stays_open_for_caller(self, mcp_server_config):
        # The caller owns the client lifecycle; build must NOT close it.
        _, client = await build_mcp_livekit_tools(mcp_server_config)

        try:
            assert client._closed is False
            # And it is still usable after build returns.
            result = await client.call_tool("add", {"a": 1, "b": 1})
            assert result.text.strip() == "2"
        finally:
            await client.close()