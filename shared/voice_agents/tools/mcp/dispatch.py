"""MCP dispatch helpers shared by voice-ws and the backend.

Builds an :class:`McpServerConfig` from an MCP-sourced ``agent_tools`` row by
merging server-level static headers with the per-user OAuth bearer from the
decrypted ``sensitive_config``.
"""
import logging

from shared.common.security import decrypt_data
from shared.voice_agents.tool_models import AgentTool
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
       already set ``Authorization``.

    Args:
        agent_tool: An :class:`AgentTool` whose ``tool`` is a ``platform_tools``
            row with ``tool_source='mcp'``. The caller is responsible for only
            calling this for MCP-sourced rows.

    Returns:
        An :class:`McpServerConfig` ready to hand to :class:`McpClient`.

    Raises:
        ValueError: If the platform tool has no ``mcp_server_url``.
    """
    platform_tool = agent_tool.tool
    if platform_tool is None or not platform_tool.mcp_server_url:
        raise ValueError(
            "Cannot build McpServerConfig: agent_tool's platform tool has no "
            "mcp_server_url (is it actually tool_source='mcp'?)."
        )

    sensitive = agent_tool.sensitive_config
    org_api_key = (
        sensitive.get("api_key") if isinstance(sensitive, dict) else None
    )

    headers = dict(platform_tool.mcp_server_headers or {})

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
                    else:
                        headers[str(k)] = value
        except Exception as e:
            logger.error(
                "Failed to decrypt mcp_server_secret_headers for %s: %s",
                platform_tool.name,
                e,
                exc_info=True,
            )

    access_token = sensitive.get("access_token") if isinstance(sensitive, dict) else None
    if access_token and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {access_token}"

    return McpServerConfig(
        url=platform_tool.mcp_server_url,
        name=platform_tool.mcp_server_name or platform_tool.name,
        headers=headers,
    )
