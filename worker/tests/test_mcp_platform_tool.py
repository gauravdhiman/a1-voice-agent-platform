"""Tests for the MCP-source fields added to ``PlatformTool`` (Phase 2).

These pin the additive contract: a ``platform_tools`` row that predates the
MCP migration (no ``tool_source`` column) is treated as ``LEGACY`` so the
existing ``LiveKitToolRegistry`` path keeps working, while a row marked
``tool_source='mcp'`` carries the connection details the worker needs to reach
a remote MCP server. See ``docs/03_implementation/mcp_integration_rfc.md`` §1.1
(coexistence) and §5 (target architecture).
"""
from uuid import uuid4

from shared.voice_agents.tool_models import (
    AgentTool,
    PlatformTool,
    ToolSource,
)

# A representative created-at/updated-at pair accepted by the model.
_TS = "2024-01-01T00:00:00"


def _legacy_platform_tool_row() -> dict:
    """A pre-Phase-2 platform_tools row: no MCP columns present at all."""
    return {
        "id": str(uuid4()),
        "name": "Google_calendar",
        "description": "Google Calendar integration",
        "requires_auth": True,
        "auth_type": "oauth2",
        "is_active": True,
        "created_at": _TS,
        "updated_at": _TS,
    }


def _mcp_platform_tool_row() -> dict:
    """A Phase-2 platform_tools row pointing at a remote MCP server."""
    return {
        "id": str(uuid4()),
        "name": "Google_calendar_mcp",
        "description": "Google Calendar via remote MCP server",
        "requires_auth": True,
        "auth_type": "oauth2",
        "is_active": True,
        "tool_source": "mcp",
        "mcp_server_url": "https://calendar-mcp.example.com/mcp",
        "mcp_server_headers": {"X-Api-Key": "server-level-key"},
        "mcp_server_name": "google-calendar",
        "created_at": _TS,
        "updated_at": _TS,
    }


class TestToolSourceEnum:
    """The ToolSource enum must expose the two coexistence values."""

    def test_legacy_and_mcp_values(self):
        assert ToolSource.LEGACY.value == "legacy"
        assert ToolSource.MCP.value == "mcp"


class TestPlatformToolLegacyDefaults:
    """A pre-migration row defaults to LEGACY and empty MCP fields."""

    def test_missing_tool_source_defaults_to_legacy(self):
        tool = PlatformTool(**_legacy_platform_tool_row())
        assert tool.tool_source is ToolSource.LEGACY

    def test_mcp_fields_default_none_for_legacy_rows(self):
        tool = PlatformTool(**_legacy_platform_tool_row())
        assert tool.mcp_server_url is None
        assert tool.mcp_server_headers is None
        assert tool.mcp_server_name is None

    def test_explicit_legacy_is_preserved(self):
        row = _legacy_platform_tool_row()
        row["tool_source"] = "legacy"
        tool = PlatformTool(**row)
        assert tool.tool_source is ToolSource.LEGACY


class TestPlatformToolMcpRow:
    """An MCP-sourced row carries its connection details through the model."""

    def test_parses_mcp_fields(self):
        tool = PlatformTool(**_mcp_platform_tool_row())
        assert tool.tool_source is ToolSource.MCP
        assert tool.mcp_server_url == "https://calendar-mcp.example.com/mcp"
        assert tool.mcp_server_headers == {"X-Api-Key": "server-level-key"}
        assert tool.mcp_server_name == "google-calendar"

    def test_mcp_row_serializes_back_with_source(self):
        """Dumping the model keeps tool_source as the enum's string value."""
        tool = PlatformTool(**_mcp_platform_tool_row())
        dumped = tool.model_dump()
        assert dumped["tool_source"] is ToolSource.MCP or dumped["tool_source"] == "mcp"


class TestAgentToolCarriesMcpPlatformTool:
    """The worker reads tools via AgentTool.tool; MCP fields must survive the join."""

    def test_agent_tool_with_mcp_platform_tool(self):
        mcp_row = _mcp_platform_tool_row()
        platform_tool = PlatformTool(**mcp_row)

        agent_tool = AgentTool(
            id=str(uuid4()),
            agent_id=str(uuid4()),
            tool_id=mcp_row["id"],
            config={"calendar_id": "primary"},
            sensitive_config={"access_token": "tok"},
            is_enabled=True,
            created_at=_TS,
            updated_at=_TS,
            tool=platform_tool,
        )

        assert agent_tool.tool is not None
        assert agent_tool.tool.tool_source is ToolSource.MCP
        assert agent_tool.tool.mcp_server_url == mcp_row["mcp_server_url"]