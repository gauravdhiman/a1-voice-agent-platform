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

* :func:`parse_mcp_servers_json` — accepts common Claude Desktop, VS Code,
  Cursor, Windsurf, and similar host-config shapes (``mcpServers``, ``servers``,
  nested ``mcp`` wrappers, or a bare server). ``stdio`` entries
  (``command``/``args``) are rejected with a per-entry error: spawning
  arbitrary subprocesses is not supportable in a hosted multi-tenant platform.
"""

import ipaddress
import json
import logging
import os
import re
import socket
from typing import Any, Mapping, Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from shared.voice_agents.tools.mcp.models import McpServerConfig

logger = logging.getLogger(__name__)

# Private/loopback/link-local addresses are blocked unless this env var is set
# (dev/test only — lets you point an agent at a local FastMCP server). Never
# enable in production: it would allow users to reach internal services.
_ALLOW_LOCAL = "MCP_ALLOW_LOCAL_URLS"

_SERVER_CONTAINER_KEYS = ("mcpServers", "servers", "mcp_servers", "mcp")
_URL_KEYS = (
    "url",
    "serverUrl",
    "server_url",
    "httpUrl",
    "http_url",
    "endpoint",
    "mcpUrl",
    "mcp_url",
)
_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "api-key",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
}
_PLACEHOLDER_PATTERN = re.compile(
    r"(?:"
    r"\{\{[^{}]+\}\}|"
    r"\$\{[^{}]+\}|"
    r"<[^<>]*(?:api|token|secret|key|credential)[^<>]*>|"
    r"\b(?:your|replace|insert)[-_ ]?(?:api[-_ ]?)?(?:key|token|secret)\b"
    r")",
    re.IGNORECASE,
)


class McpServerParseError(BaseModel):
    """A single rejected entry from a pasted MCP host configuration.

    Attributes:
        name: The entry's key in the ``mcpServers`` map (or ``<root>`` for a
            bare object / top-level parse error).
        message: Why the entry was rejected (shown inline in the UI).
    """

    name: str
    message: str


class McpServersParseResult(BaseModel):
    """Outcome of parsing a pasted MCP host JSON configuration.

    A paste can yield some valid servers AND some per-entry errors (e.g. one
    stdio entry alongside HTTP entries). The UI shows both: the valid servers
    to configure, and the rejected entries with their reasons.

    Attributes:
        servers: Valid HTTP server configs ready to discover/save.
        errors: Rejected entries with per-entry reasons.
    """

    servers: list[McpServerConfig] = Field(default_factory=list)
    errors: list[McpServerParseError] = Field(default_factory=list)


def _is_server_like(value: Mapping[str, Any]) -> bool:
    """Return whether a JSON object resembles one server definition."""
    return any(
        key in value
        for key in (
            *_URL_KEYS,
            "command",
            "args",
            "transport",
            "type",
            "headers",
            "auth",
            "authentication",
            "oauth",
            "auth_type",
            "authType",
        )
    )


def _normalize_entries(data: dict[str, Any]) -> dict[str, Any] | list[Any]:
    """Normalize common host-level server containers to a server collection.

    MCP standardizes the wire protocol, not the JSON file used by a host such
    as Claude Desktop, VS Code, Cursor, Windsurf, or Gemini CLI. Those hosts
    use slightly different container names and URL aliases, so the parser
    accepts the known conventions while keeping per-entry validation below.
    """
    for key in _SERVER_CONTAINER_KEYS:
        if key in data:
            value = data[key]
            # Some exporters add an extra ``mcp`` namespace around the same
            # host-specific ``servers``/``mcpServers`` collection.
            if key == "mcp" and isinstance(value, Mapping):
                return _normalize_entries(dict(value))
            return value
    if _is_server_like(data):
        return {"": data}
    return data


def _transport_name(value: Any) -> str:
    """Normalize transport spelling used by popular MCP host configs."""
    if isinstance(value, Mapping):
        value = value.get("type") or value.get("name")
    normalized = str(value or "streamable_http").strip().lower()
    normalized = normalized.replace("-", "").replace("_", "").replace(" ", "")
    if normalized in {"http", "https", "streamablehttp", "streamable"}:
        return "streamable_http"
    if normalized in {"sse", "httpsse", "serversentevents"}:
        return "sse"
    if normalized in {"stdio", "command"}:
        return "stdio"
    return normalized or "streamable_http"


def _header_value_has_placeholder(value: str) -> bool:
    """Return whether a header contains a host/config credential placeholder."""
    return bool(_PLACEHOLDER_PATTERN.search(value))


def _canonicalize_key_placeholder(value: str) -> str:
    """Convert host-specific env/input placeholders to ``{{KEY}}``."""
    return _PLACEHOLDER_PATTERN.sub("{{KEY}}", value)


def _is_sensitive_header(name: str) -> bool:
    """Return whether a header conventionally carries a credential."""
    normalized = name.strip().lower()
    return normalized in _SENSITIVE_HEADER_NAMES or normalized.endswith(
        ("-api-key", "-auth-token", "-access-token")
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    """Return a shallow dict for optional JSON config sections."""
    return dict(value) if isinstance(value, Mapping) else {}


def _first_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for a list of alias keys."""
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", []):
            return value
    return None


def _normalize_scopes(value: Any) -> list[str]:
    """Normalize OAuth scopes supplied as a list or a space/comma string."""
    if isinstance(value, list):
        return [str(scope).strip() for scope in value if str(scope).strip()]
    if isinstance(value, str):
        return [part for part in re.split(r"[\s,]+", value.strip()) if part]
    return []


def _normalize_auth(
    cfg: Mapping[str, Any],
    headers: Mapping[str, str],
    secret_headers: Mapping[str, str],
) -> tuple[Optional[str], bool, dict[str, Any]]:
    """Normalize non-standard auth sections into platform auth metadata."""
    auth_value = _first_value(cfg, "auth", "authentication", "authorization")
    auth = _as_mapping(auth_value)
    oauth = _as_mapping(cfg.get("oauth"))
    if oauth:
        auth = {**auth, **oauth}
    nested_oauth = _as_mapping(auth.get("oauth"))
    if nested_oauth:
        auth = {**auth, **nested_oauth}

    explicit_type = _first_value(
        auth,
        "type",
        "method",
        "kind",
        "auth_type",
        "authType",
    ) or _first_value(cfg, "auth_type", "authType")
    normalized_type = (
        str(explicit_type or "").strip().lower().replace("-", "").replace("_", "")
    )

    auth_url = _first_value(
        auth,
        "auth_url",
        "authorization_url",
        "authorization_endpoint",
        "authorizationEndpoint",
        "authorize_url",
    ) or _first_value(
        cfg,
        "auth_url",
        "authorization_url",
        "authorization_endpoint",
        "authorizationEndpoint",
    )
    token_url = _first_value(
        auth,
        "token_url",
        "token_endpoint",
        "tokenEndpoint",
    ) or _first_value(cfg, "token_url", "token_endpoint", "tokenEndpoint")
    scopes = _normalize_scopes(
        _first_value(auth, "scopes", "scope") or _first_value(cfg, "scopes", "scope")
    )
    auth_config: dict[str, Any] = {}
    if auth_url:
        auth_config["auth_url"] = str(auth_url)
    if token_url:
        auth_config["token_url"] = str(token_url)
    if scopes:
        auth_config["scopes"] = scopes
    provider = _first_value(auth, "provider", "issuer") or _first_value(
        cfg, "oauth_provider", "provider"
    )
    if provider:
        auth_config["provider"] = str(provider)
    client_id = _first_value(auth, "client_id", "clientId") or _first_value(
        cfg, "client_id", "clientId"
    )
    if client_id:
        auth_config["client_id"] = str(client_id)
    redirect_uri = _first_value(auth, "redirect_uri", "redirectUri") or _first_value(
        cfg, "redirect_uri", "redirectUri"
    )
    if redirect_uri:
        auth_config["redirect_uri"] = str(redirect_uri)
    resource = _first_value(auth, "resource", "resource_uri") or _first_value(
        cfg, "resource", "resource_uri"
    )
    if resource:
        auth_config["resource"] = str(resource)
    registration_endpoint = _first_value(
        auth,
        "registration_endpoint",
        "registrationEndpoint",
        "client_registration_endpoint",
    ) or _first_value(
        cfg,
        "registration_endpoint",
        "registrationEndpoint",
        "client_registration_endpoint",
    )
    if registration_endpoint:
        auth_config["registration_endpoint"] = str(registration_endpoint)

    is_oauth = "oauth" in normalized_type or bool(auth_url or token_url) or bool(oauth)
    if is_oauth:
        auth_config["provider"] = auth_config.get("provider", "mcp")
        return "oauth2", True, auth_config

    explicit_requires_auth = _first_value(cfg, "requires_auth", "requiresAuth")
    explicit_api_key = normalized_type in {"apikey", "bearer", "token", "header"}
    is_api_key = (
        explicit_api_key
        or bool(secret_headers)
        or any(_is_sensitive_header(name) for name in headers)
    )
    if is_api_key:
        # A literal platform-owned header is enough to connect without asking
        # the org admin for another key. ``{{KEY}}`` means the org owns it.
        if explicit_requires_auth is not None:
            requires_auth = bool(explicit_requires_auth)
        elif explicit_api_key:
            # An explicit API-key declaration with no platform-owned literal
            # credential still needs an org key. Parsed sensitive headers are
            # canonicalized to ``{{KEY}}`` before this helper runs.
            requires_auth = not secret_headers or any(
                "{{KEY}}" in value for value in secret_headers.values()
            )
        else:
            requires_auth = any("{{KEY}}" in value for value in secret_headers.values())
        auth_config["credential_source"] = "org" if requires_auth else "platform"
        return "api_key", requires_auth, auth_config

    if explicit_requires_auth:
        return "custom", True, auth_config
    return None, False, auth_config


def _entry_url(cfg: Mapping[str, Any]) -> Optional[str]:
    """Extract a remote URL from top-level or nested transport sections."""
    nested = cfg.get("transport") if isinstance(cfg.get("transport"), Mapping) else {}
    http = cfg.get("http") if isinstance(cfg.get("http"), Mapping) else {}
    for source in (cfg, nested, http):
        value = _first_value(source, *_URL_KEYS)
        if value:
            return str(value).strip()
    return None


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
    """Parse a pasted MCP host JSON config into server configs + errors.

    Accepted shapes include a bare single server, Claude Desktop / Cursor /
    Windsurf ``mcpServers`` maps, VS Code-style ``servers`` maps or arrays,
    nested ``mcp`` wrappers, and bare name→config maps. URL and transport
    aliases are normalized into the hosted Streamable HTTP model.

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
            errors=[
                McpServerParseError(name="<root>", message="Configuration is empty")
            ]
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return McpServersParseResult(
            errors=[
                McpServerParseError(name="<root>", message=f"Invalid JSON: {e.msg}")
            ]
        )

    if not isinstance(data, dict):
        return McpServersParseResult(
            errors=[
                McpServerParseError(
                    name="<root>", message="Configuration must be a JSON object"
                )
            ]
        )

    # Normalize into a name→config map. Host files use both ``mcpServers``
    # (Claude/Cursor/Windsurf) and ``servers`` (VS Code). A few tools export an
    # array of named entries, so accept that shape as well.
    servers_collection = _normalize_entries(data)
    if isinstance(servers_collection, list):
        servers_map = {
            str(item.get("name") or item.get("id") or f"mcp-server-{index + 1}"): item
            for index, item in enumerate(servers_collection)
            if isinstance(item, Mapping)
        }
        if not servers_map and servers_collection:
            return McpServersParseResult(
                errors=[
                    McpServerParseError(
                        name="<root>",
                        message="Server list entries must be JSON objects",
                    )
                ]
            )
    elif isinstance(servers_collection, dict):
        servers_map = servers_collection
    else:
        return McpServersParseResult(
            errors=[
                McpServerParseError(
                    name="<root>",
                    message="Server collection must be an object or array",
                )
            ]
        )

    servers: list[McpServerConfig] = []
    errors: list[McpServerParseError] = []
    for key, cfg in servers_map.items():
        name = key or "mcp-server"
        if not isinstance(cfg, dict):
            errors.append(
                McpServerParseError(name=name, message="Entry must be an object")
            )
            continue

        transport_value = cfg.get("transport")
        transport = _transport_name(cfg.get("type") or transport_value)
        has_stdio = "command" in cfg or "args" in cfg or transport == "stdio"
        if has_stdio:
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
        if cfg.get("disabled") is True:
            errors.append(
                McpServerParseError(
                    name=name,
                    message="Entry is disabled in the source configuration",
                )
            )
            continue
        if transport == "sse":
            errors.append(
                McpServerParseError(
                    name=name,
                    message=(
                        "Legacy SSE transport is not supported by the hosted "
                        "runtime — use a Streamable HTTP MCP endpoint"
                    ),
                )
            )
            continue
        if transport != "streamable_http":
            errors.append(
                McpServerParseError(
                    name=name,
                    message=f"Unsupported MCP transport '{transport}'",
                )
            )
            continue

        url = _entry_url(cfg)
        if not url:
            errors.append(McpServerParseError(name=name, message="Entry has no 'url'"))
            continue

        nested_transport = (
            cfg.get("transport") if isinstance(cfg.get("transport"), Mapping) else {}
        )
        raw_headers = cfg.get("headers") or nested_transport.get("headers") or {}
        if not isinstance(raw_headers, dict):
            errors.append(
                McpServerParseError(name=name, message="'headers' must be an object")
            )
            continue

        # Coerce header values to strings, then move credential-bearing
        # placeholders out of public headers. The platform stores those
        # templates encrypted and asks the org admin for a value only when the
        # template actually needs one.
        normalized_headers = {str(k): str(v) for k, v in raw_headers.items()}
        public_headers: dict[str, str] = {}
        secret_headers: dict[str, str] = {}
        for header_name, value in normalized_headers.items():
            if _header_value_has_placeholder(value) or _is_sensitive_header(
                header_name
            ):
                if _header_value_has_placeholder(value):
                    secret_headers[header_name] = _canonicalize_key_placeholder(value)
                elif header_name.strip().lower() == "authorization":
                    # Do not echo a pasted bearer token from the parse API;
                    # retain its scheme so runtime substitution is valid.
                    scheme = value.split(None, 1)[0] if value.split() else "Bearer"
                    secret_headers[header_name] = f"{scheme} {{{{KEY}}}}"
                else:
                    # Never send a real pasted API key back to the browser.
                    secret_headers[header_name] = "{{KEY}}"
            else:
                public_headers[header_name] = value

        auth_type, requires_auth, auth_config = _normalize_auth(
            cfg, public_headers, secret_headers
        )
        # OAuth bearer placeholders are not API-key templates. The runtime
        # injects the OAuth token itself, so discard them rather than asking an
        # org admin to paste an API key into an OAuth integration.
        if auth_type == "oauth2":
            secret_headers = {}

        servers.append(
            McpServerConfig(
                url=url,
                name=str(cfg.get("name") or name),
                headers=public_headers,
                secret_headers=secret_headers,
                transport=transport,
                auth_type=auth_type,
                requires_auth=requires_auth,
                auth_config=auth_config,
            )
        )

    return McpServersParseResult(servers=servers, errors=errors)
