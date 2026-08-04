"""MCP-based tool integration (Phase 1 of the MCP integration RFC).

This package implements a generic MCP client that connects to remote MCP servers
over Streamable HTTP. It lives alongside the legacy ``BaseTool`` mechanism
(``shared/voice_agents/tools/base/``).

Public API:
    - :class:`McpClient` — async client (list_tools / call_tool / close).
    - :class:`McpServerConfig`, :class:`McpToolDef`, :class:`McpToolResult`
      — data models.
    - :func:`mcp_server_config_from_agent_tool` — build server config from an
      MCP-sourced ``agent_tools`` row.
"""
from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.dispatch import mcp_server_config_from_agent_tool
from shared.voice_agents.tools.mcp.models import (
    McpServerConfig,
    McpToolDef,
    McpToolResult,
)

__all__ = [
    "McpClient",
    "McpServerConfig",
    "McpToolDef",
    "McpToolResult",
    "mcp_server_config_from_agent_tool",
]
