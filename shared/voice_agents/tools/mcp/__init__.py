"""MCP-based tool integration (Phase 1 of the MCP integration RFC).

This package implements the *new* tool-integration path: a generic MCP client
that connects to remote MCP servers over Streamable HTTP and exposes their
tools to the LiveKit worker. It lives alongside the legacy ``BaseTool``
mechanism (``shared/voice_agents/tools/base/``) and does **not** modify or
replace it. See ``docs/03_implementation/mcp_integration_rfc.md`` §1.1 for the
coexistence hard constraint.

Public API:
    - :class:`McpClient` — async client (list_tools / call_tool / close).
    - :class:`McpServerConfig`, :class:`McpToolDef`, :class:`McpToolResult`
      — data models.
    - :func:`mcp_tool_to_livekit_tool` — synthesize a LiveKit ``RawFunctionTool``
      from an :class:`McpToolDef` (Phase 1).
    - :func:`mcp_server_config_from_agent_tool`, :func:`build_mcp_livekit_tools`,
      :func:`build_livekit_tools_for_agent_tool` — worker dispatch helpers
      (Phase 3a): turn an MCP-sourced ``agent_tools`` row into LiveKit tools.
"""
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
    "build_livekit_tools_for_agent_tool",
    "build_mcp_livekit_tools",
    "mcp_server_config_from_agent_tool",
    "mcp_tool_to_livekit_tool",
]


def __getattr__(name: str):
    """Load LiveKit-only helpers lazily so Pipecat can use the MCP client.

    The Pipecat container deliberately excludes ``livekit-agents``. Keeping
    the legacy adapter imports lazy preserves the worker's package-level public
    API without making the shared MCP client depend on LiveKit at import time.
    """
    if name == "McpClient":
        from shared.voice_agents.tools.mcp.client import McpClient

        return McpClient
    if name in {
        "build_livekit_tools_for_agent_tool",
        "build_mcp_livekit_tools",
        "mcp_server_config_from_agent_tool",
    }:
        from shared.voice_agents.tools.mcp import dispatch

        return getattr(dispatch, name)
    if name == "mcp_tool_to_livekit_tool":
        from shared.voice_agents.tools.mcp.livekit_adapter import mcp_tool_to_livekit_tool

        return mcp_tool_to_livekit_tool
    raise AttributeError(name)