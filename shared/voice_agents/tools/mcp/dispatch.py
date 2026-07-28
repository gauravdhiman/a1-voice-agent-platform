"""Worker-side dispatch: turn an MCP-sourced agent_tool into LiveKit tools.

This module is the glue the worker's per-agent tool-assembly loop calls when a
``platform_tools`` row is marked ``tool_source='mcp'``. It builds an
:class:`McpServerConfig` from the row (merging server-level static headers with
the per-user OAuth bearer from the decrypted ``sensitive_config``), opens an
:class:`McpClient`, discovers the server's tools, filters out any
``unselected_functions``, and synthesizes a LiveKit ``RawFunctionTool`` per tool
via :func:`mcp_tool_to_livekit_tool`.

Coexistence (RFC §1.1): the legacy ``BaseTool`` / ``LiveKitToolRegistry`` path
is untouched. The worker picks this module only for MCP-sourced rows; every
other row follows the original path. No legacy file is modified here.

Lifecycle — IMPORTANT:
    :func:`build_mcp_livekit_tools` returns the open :class:`McpClient` alongside
    the synthesized tools. The caller (the worker) must keep that client open for
    the lifetime of the agent session, because each tool handler holds a
    reference to it and will call through it when the model invokes the tool.
    The caller must :meth:`close <McpClient.close>` the client when the session
    ends. Closing it early would make every synthesized tool fail at call time.
"""
import logging
from typing import Optional

from shared.common.security import decrypt_data
from shared.voice_agents.tool_models import AgentTool, ToolSource
from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.livekit_adapter import mcp_tool_to_livekit_tool
from shared.voice_agents.tools.mcp.models import McpServerConfig

logger = logging.getLogger(__name__)


def mcp_server_config_from_agent_tool(agent_tool: AgentTool) -> McpServerConfig:
    """Build an :class:`McpServerConfig` from an MCP-sourced agent_tool.

    Merges three header sources, in increasing precedence (later wins):

    1. ``mcp_server_headers`` — non-secret static headers (plaintext JSONB).
    2. ``mcp_server_secret_headers`` — encrypted server-level secret headers,
       decrypted here via :func:`decrypt_data`. Under the publish-lifecycle
       model (RFC §6.6) these are a **template**: a value containing the
       ``{{KEY}}`` placeholder is filled with the **org admin's** API key from
       the agent_tool's decrypted ``sensitive_config["api_key"]`` — never the
       platform admin's transient test key. A literal value (no ``{{KEY}}``)
       passes through unchanged (fixed shared header). A templated header with
       no org key is dropped (no platform fallback) so the tool is left in an
       "API key required" state rather than sending the bare marker.
    3. the per-user OAuth bearer from the agent_tool's decrypted
       ``sensitive_config`` (``access_token``), injected as
       ``Authorization: Bearer <token>`` only when the merged headers do not
       already set ``Authorization`` (a ``{{KEY}}``-resolved Authorization, a
       literal Authorization, or a server-level Authorization all win; in
       practice the per-user token is the common case for vendor MCP servers
       like Google Calendar).

    The URL itself was validated against the SSRF guard at discover/save time
    (see :func:`shared.voice_agents.tools.mcp.security.validate_mcp_server_url`).
    Runtime re-validation is deferred to a follow-up — it would add a per-session
    DNS resolve and break loopback dev/test servers; save-time validation is the
    gate. TODO: add a best-effort rebinding re-check inside McpClient before
    connect once a non-DNS / cached-resolution variant exists.

    Args:
        agent_tool: An :class:`AgentTool` whose ``tool`` is a ``platform_tools``
            row with ``tool_source='mcp'``. The caller is responsible for only
            calling this for MCP-sourced rows.

    Returns:
        An :class:`McpServerConfig` ready to hand to :class:`McpClient`.

    Raises:
        ValueError: If the platform tool has no ``mcp_server_url`` (an MCP row
            without a server URL is a data error, not a runtime fallback).
    """
    platform_tool = agent_tool.tool
    if platform_tool is None or not platform_tool.mcp_server_url:
        raise ValueError(
            "Cannot build McpServerConfig: agent_tool's platform tool has no "
            "mcp_server_url (is it actually tool_source='mcp'?)."
        )

    # Decrypted per-agent sensitive config (org API key + per-user OAuth token).
    sensitive = agent_tool.sensitive_config
    org_api_key = (
        sensitive.get("api_key") if isinstance(sensitive, dict) else None
    )

    # 1. Non-secret static headers (plaintext).
    headers = dict(platform_tool.mcp_server_headers or {})

    # 2. Encrypted server-level secret headers (template with ``{{KEY}}``
    #    placeholder), decrypted. Publish-lifecycle model (RFC §6.6): a platform
    #    admin authors a server whose secret headers may contain ``{{KEY}}``;
    #    at runtime it is filled with the ORG ADMIN's API key from
    #    ``sensitive_config["api_key"]`` — never the platform admin's transient
    #    test key. A literal value (no ``{{KEY}}``) passes through as a fixed
    #    shared header (optional shared-key mode, platform-admin's call). A
    #    templated header with no org key is DROPPED (no platform fallback) so
    #    the tool is left in an "API key required" state rather than sending the
    #    bare ``{{KEY}}`` marker or a stale platform key.
    if platform_tool.mcp_server_secret_headers:
        try:
            secret_headers = decrypt_data(platform_tool.mcp_server_secret_headers)
            if isinstance(secret_headers, dict):
                for k, v in secret_headers.items():
                    value = str(v)
                    if "{{KEY}}" in value:
                        if org_api_key:
                            headers[str(k)] = value.replace(
                                "{{KEY}}", str(org_api_key)
                            )
                        # No org key → drop this header (no platform fallback).
                    else:
                        headers[str(k)] = value
        except Exception as e:
            logger.error(
                "Failed to decrypt mcp_server_secret_headers for %s: %s",
                platform_tool.name,
                e,
                exc_info=True,
            )

    # 3. Per-user OAuth bearer (only if no Authorization header is set yet).
    access_token = sensitive.get("access_token") if isinstance(sensitive, dict) else None
    if access_token and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {access_token}"

    return McpServerConfig(
        url=platform_tool.mcp_server_url,
        name=platform_tool.mcp_server_name or platform_tool.name,
        headers=headers,
    )


async def build_mcp_livekit_tools(
    config: McpServerConfig,
    unselected_functions: Optional[list[str]] = None,
) -> tuple[list, McpClient]:
    """Open a client, discover the server's tools, and synthesize LiveKit tools.

    Args:
        config: The :class:`McpServerConfig` for the remote MCP server.
        unselected_functions: Tool names to exclude (mirrors the legacy
            ``agent_tools.unselected_functions`` semantics). ``None`` or empty
            means "include every tool the server exposes".

    Returns:
        A tuple ``(livekit_tools, client)``. ``livekit_tools`` is a list of
        LiveKit ``RawFunctionTool`` instances (one per discovered tool, minus
        any unselected names). ``client`` is the open :class:`McpClient` the
        tool handlers reference; the caller owns its lifecycle and must keep it
        open for the agent session.

    Raises:
        Exception: If the MCP server cannot be reached or ``list_tools`` fails.
        The client is closed before propagating so the caller does not leak an
        open connection on a failed setup.
    """
    client = McpClient(config)
    try:
        tool_defs = await client.list_tools()
    except Exception:
        # Setup failed — clean up the half-open client so we don't leak it.
        await client.close()
        raise

    skip = set(unselected_functions or [])
    tools = [
        mcp_tool_to_livekit_tool(client, tool_def)
        for tool_def in tool_defs
        if tool_def.name not in skip
    ]
    logger.info(
        "Built %d MCP LiveKit tool(s) from server '%s' (skipped %d unselected)",
        len(tools),
        config.name or config.url,
        len(skip),
    )
    return tools, client


async def build_livekit_tools_for_agent_tool(
    agent_tool: AgentTool,
) -> tuple[list, McpClient]:
    """Convenience: build LiveKit tools for a single MCP-sourced agent_tool.

    Combines :func:`mcp_server_config_from_agent_tool` and
    :func:`build_mcp_livekit_tools`, applying the agent_tool's
    ``unselected_functions``.

    Args:
        agent_tool: An MCP-sourced :class:`AgentTool`.

    Returns:
        ``(livekit_tools, client)`` — see :func:`build_mcp_livekit_tools`.

    Raises:
        ValueError: If the agent_tool is not MCP-sourced (defensive guard so a
            legacy row is never silently routed through the MCP path).
    """
    if not agent_tool.tool or agent_tool.tool.tool_source is not ToolSource.MCP:
        raise ValueError(
            "build_livekit_tools_for_agent_tool only accepts MCP-sourced "
            f"agent_tools (got tool_source={getattr(agent_tool.tool, 'tool_source', None)!r})."
        )
    config = mcp_server_config_from_agent_tool(agent_tool)
    return await build_mcp_livekit_tools(
        config, unselected_functions=agent_tool.unselected_functions
    )