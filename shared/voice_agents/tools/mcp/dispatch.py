"""MCP dispatch helpers shared by voice-ws and the backend.

Builds an :class:`McpServerConfig` from an MCP-sourced ``agent_tools`` row by
merging server-level static headers with the per-user OAuth bearer from the
decrypted ``sensitive_config``.
"""

import logging

from shared.common.security import decrypt_data
from shared.voice_agents.tool_models import AgentTool
from shared.voice_agents.tools.mcp.models import McpServerConfig
from shared.voice_agents.tools.mcp.security import validate_mcp_server_url

logger = logging.getLogger(__name__)

_API_KEY_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "api-key",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
}


def _is_api_key_header(name: str) -> bool:
    """Return whether a header conventionally carries an API credential."""
    normalized = name.strip().lower()
    return normalized in _API_KEY_HEADER_NAMES or normalized.endswith(
        ("-api-key", "-auth-token", "-access-token")
    )


def _apply_org_key(value: str, org_api_key: str) -> str:
    """Apply an org key while preserving common Authorization schemes."""
    if "{{KEY}}" in value:
        return value.replace("{{KEY}}", org_api_key)
    scheme, separator, _ = value.partition(" ")
    if separator and scheme.lower() in {"bearer", "basic", "token"}:
        return f"{scheme} {org_api_key}"
    return org_api_key


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
       passes through unchanged as the platform fallback. A templated header
       with no org key is dropped rather than sending the bare marker.
    3. the per-user OAuth bearer from the agent_tool's decrypted
       ``sensitive_config`` (``access_token``), injected as
       ``Authorization: Bearer <token>``. For OAuth tools it replaces any
       stale static ``Authorization`` header so a platform-level grant can
       never override the connected user's grant.

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

    # A saved URL can change DNS answers after configuration, so repeat the
    # SSRF check at the last boundary before any credential is decrypted or
    # merged into the request headers. This protects long-lived agent_tools
    # from DNS rebinding and out-of-band database/configuration changes.
    valid_url, reason = validate_mcp_server_url(platform_tool.mcp_server_url)
    if not valid_url:
        raise ValueError(f"Cannot build McpServerConfig: {reason}")

    sensitive = agent_tool.sensitive_config
    org_api_key = sensitive.get("api_key") if isinstance(sensitive, dict) else None

    headers: dict[str, str] = {}
    for key, raw_value in (platform_tool.mcp_server_headers or {}).items():
        value = str(raw_value)
        if "{{KEY}}" in value:
            if org_api_key:
                headers[str(key)] = _apply_org_key(value, str(org_api_key))
            # Never send a literal placeholder or a platform test credential.
            continue
        if org_api_key and _is_api_key_header(str(key)):
            headers[str(key)] = _apply_org_key(value, str(org_api_key))
            continue
        headers[str(key)] = value

    if platform_tool.mcp_server_secret_headers:
        try:
            secret_headers = decrypt_data(platform_tool.mcp_server_secret_headers)
            if isinstance(secret_headers, dict):
                for k, v in secret_headers.items():
                    value = str(v)
                    if "{{KEY}}" in value:
                        if org_api_key:
                            headers[str(k)] = _apply_org_key(value, str(org_api_key))
                    elif org_api_key and _is_api_key_header(str(k)):
                        headers[str(k)] = _apply_org_key(value, str(org_api_key))
                    else:
                        headers[str(k)] = value
        except Exception as e:
            logger.error(
                "Failed to decrypt mcp_server_secret_headers for %s (%s)",
                platform_tool.name,
                type(e).__name__,
            )

    access_token = (
        sensitive.get("access_token") if isinstance(sensitive, dict) else None
    )
    is_oauth_tool = getattr(platform_tool, "auth_type", None) == "oauth2"
    if access_token and is_oauth_tool:
        # A stale static Authorization header must never override the
        # per-connection OAuth grant. This also prevents a platform-level
        # bearer from being sent after an org admin connects their account.
        for key in list(headers):
            if key.lower() == "authorization":
                del headers[key]
        headers["Authorization"] = f"Bearer {access_token}"
    elif access_token and not any(key.lower() == "authorization" for key in headers):
        headers["Authorization"] = f"Bearer {access_token}"

    return McpServerConfig(
        url=platform_tool.mcp_server_url,
        name=platform_tool.mcp_server_name or platform_tool.name,
        headers=headers,
    )
