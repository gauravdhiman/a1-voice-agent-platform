"""Security helpers for user-configured MCP servers.

These helpers gate which remote MCP servers an end-user can configure from the
UI (``docs/03_implementation/mcp_integration_rfc.md``). They are pure (no DB, no
network beyond DNS resolution) and backend-/worker-importable so the same rules
apply at discover time (backend), save time (backend), and call time (worker
dispatch).

Two concerns:

* :func:`validate_mcp_server_url` — SSRF guard. Prevents a user from pointing an
  agent at an internal address (e.g. the cloud metadata endpoint
  ``169.254.169.254``) to exfiltrate credentials or scan the private network.
  https is required for public hosts; plain http is allowed only to loopback
  and only when ``MCP_ALLOW_LOCAL_URLS`` is set (dev/test).

* :func:`parse_mcp_servers_json` — accepts the Claude Desktop / VS Code
  ``mcpServers`` JSON format (a map of named servers, each with ``url``/
  ``headers`` for HTTP transport). ``stdio`` entries (``command``/``args``)
  are rejected with a per-entry error: spawning arbitrary subprocesses is not
  supportable in a hosted multi-tenant platform.
"""
import ipaddress
import json
import logging
import os
import socket
from typing import Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from shared.voice_agents.tools.mcp.models import McpServerConfig

logger = logging.getLogger(__name__)

# Private/loopback/link-local addresses are blocked unless this env var is set
# (dev/test only — lets you point an agent at a local FastMCP server). Never
# enable in production: it would allow users to reach internal services.
_ALLOW_LOCAL = "MCP_ALLOW_LOCAL_URLS"


class McpServerParseError(BaseModel):
    """A single rejected entry from a pasted ``mcpServers`` config.

    Attributes:
        name: The entry's key in the ``mcpServers`` map (or ``<root>`` for a
            bare object / top-level parse error).
        message: Why the entry was rejected (shown inline in the UI).
    """

    name: str
    message: str


class McpServersParseResult(BaseModel):
    """Outcome of parsing a pasted ``mcpServers`` JSON config.

    A paste can yield some valid servers AND some per-entry errors (e.g. one
    stdio entry alongside HTTP entries). The UI shows both: the valid servers
    to configure, and the rejected entries with their reasons.

    Attributes:
        servers: Valid HTTP server configs ready to discover/save.
        errors: Rejected entries with per-entry reasons.
    """

    servers: list[McpServerConfig] = Field(default_factory=list)
    errors: list[McpServerParseError] = Field(default_factory=list)


def _resolve_host(host: str) -> list[str]:
    """Resolve a hostname to a list of IP address strings.

    Wrapped at module level so tests can monkeypatch it for offline
    determinism. Raises ``socket.gaierror`` on failure (propagated to the
    caller, which reports the URL as unresolvable).
    """
    infos = socket.getaddrinfo(host, None)
    # Dedup while preserving order.
    seen: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in seen:
            seen.append(ip)
    return seen


def _is_blocked_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Whether an IP is private/loopback/link-local/reserved/multicast.

    These are the addresses a user-configured server must not reach (SSRF
    surface). ``is_link_local`` covers the 169.254.169.254 cloud metadata
    endpoint.
    """
    return bool(
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _allow_local() -> bool:
    return os.getenv(_ALLOW_LOCAL, "").strip().lower() in ("1", "true", "yes")


def validate_mcp_server_url(url: Optional[str]) -> tuple[bool, str]:
    """Validate that an MCP server URL is safe to contact.

    Rules:
        - Must be an http or https URL with a host.
        - The host must resolve; unresolvable → reject.
        - Resolved IPs must not be private/loopback/link-local/reserved/etc.
          unless ``MCP_ALLOW_LOCAL_URLS`` is set (dev/test only).
        - Plain ``http`` is allowed only to loopback and only with
          ``MCP_ALLOW_LOCAL_URLS``; public hosts require ``https``.

    Args:
        url: The MCP server endpoint to validate.

    Returns:
        ``(True, "")`` if the URL is safe to contact, otherwise
        ``(False, reason)`` with a human-readable reason suitable to surface
        in the UI.
    """
    if not url or not isinstance(url, str):
        return False, "URL is required"

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False, "Invalid URL"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, "URL must use the http or https scheme"
    host = parsed.hostname
    if not host:
        return False, "URL has no host"

    try:
        ips_str = _resolve_host(host)
    except socket.gaierror:
        return False, f"Could not resolve host: {host}"
    except Exception as e:  # defensive: never crash the request on a DNS oddity
        return False, f"Could not resolve host: {host} ({type(e).__name__})"

    if not ips_str:
        return False, f"Could not resolve host: {host}"

    try:
        ips = [ipaddress.ip_address(ip) for ip in ips_str]
    except ValueError:
        return False, f"Unparseable address for host: {host}"

    allow_local = _allow_local()

    for ip in ips:
        if _is_blocked_ip(ip):
            if allow_local:
                # Dev/test: allow loopback/private only. Link-local/metadata is
                # still blocked even with the flag (no reason to reach it).
                if ip.is_loopback or ip.is_private:
                    continue
            return False, f"URL resolves to a blocked address ({ip})"

    if scheme == "http":
        # Plain http is only for local dev against loopback.
        if not allow_local:
            return False, (
                "http URLs require MCP_ALLOW_LOCAL_URLS=true (dev/test only); "
                "use https for public servers"
            )
        if not all(ip.is_loopback for ip in ips):
            return False, "http URLs are only allowed to loopback addresses"

    return True, ""


def parse_mcp_servers_json(raw: str) -> McpServersParseResult:
    """Parse a pasted ``mcpServers`` JSON config into server configs + errors.

    Accepted shapes:
        - Bare single server: ``{"url": "https://host/mcp", "headers": {...}}``.
        - Claude Desktop / VS Code map: ``{"mcpServers": {"name": {...}}}``.
        - Bare name→config map: ``{"name": {"url": ...}}``.

    ``stdio`` entries (those with ``command``/``args`` and no ``url``) are
    rejected with a per-entry error rather than raising — a paste may mix
    valid HTTP servers with stdio servers, and the UI shows both.

    Args:
        raw: The pasted JSON string.

    Returns:
        A :class:`McpServersParseResult` with valid ``servers`` and per-entry
        ``errors``. Malformed JSON or a non-object top level yields a single
        ``<root>`` error and no servers.
    """
    if not raw or not isinstance(raw, str) or not raw.strip():
        return McpServersParseResult(
            errors=[McpServerParseError(name="<root>", message="Configuration is empty")]
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return McpServersParseResult(
            errors=[McpServerParseError(name="<root>", message=f"Invalid JSON: {e.msg}")]
        )

    if not isinstance(data, dict):
        return McpServersParseResult(
            errors=[
                McpServerParseError(
                    name="<root>", message="Configuration must be a JSON object"
                )
            ]
        )

    # Normalize into a name→config map.
    if "mcpServers" in data:
        servers_map = data["mcpServers"]
        if not isinstance(servers_map, dict):
            return McpServersParseResult(
                errors=[
                    McpServerParseError(
                        name="<root>", message="'mcpServers' must be an object"
                    )
                ]
            )
    elif "url" in data:
        # Bare single-server object.
        servers_map = {"": data}
    else:
        # Treat the top-level object as a name→config map.
        servers_map = data

    servers: list[McpServerConfig] = []
    errors: list[McpServerParseError] = []
    for key, cfg in servers_map.items():
        name = key or "mcp-server"
        if not isinstance(cfg, dict):
            errors.append(
                McpServerParseError(name=name, message="Entry must be an object")
            )
            continue

        url = cfg.get("url")
        has_stdio = "command" in cfg or "args" in cfg
        if not url and has_stdio:
            errors.append(
                McpServerParseError(
                    name=name,
                    message=(
                        "stdio servers (command/args) aren't supported in a "
                        "hosted platform — use a remote HTTP MCP server (url)"
                    ),
                )
            )
            continue
        if not url:
            errors.append(
                McpServerParseError(name=name, message="Entry has no 'url'")
            )
            continue

        raw_headers = cfg.get("headers") or {}
        if not isinstance(raw_headers, dict):
            errors.append(
                McpServerParseError(name=name, message="'headers' must be an object")
            )
            continue
        # Coerce header values to strings (JSON numbers/bools are common).
        headers = {str(k): str(v) for k, v in raw_headers.items()}

        servers.append(
            McpServerConfig(
                url=str(url),
                name=str(cfg.get("name") or name),
                headers=headers,
            )
        )

    return McpServersParseResult(servers=servers, errors=errors)