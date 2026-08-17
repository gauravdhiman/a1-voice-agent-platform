"""Tests for MCP server config security helpers.

These cover the two pure helpers that gate which remote MCP servers a user can
configure from the UI (``docs/03_implementation/mcp_integration_rfc.md``):

* :func:`validate_mcp_server_url` — SSRF guard. Rejects non-http(s) schemes,
  private/loopback/link-local/metadata IPs, and plain http unless the
  ``MCP_ALLOW_LOCAL_URLS`` dev flag is set.
* :func:`parse_mcp_servers_json` — parses Claude Desktop / VS Code
  ``mcpServers`` JSON into ``McpServerConfig`` objects, rejecting ``stdio``
  (``command``/``args``) entries with a per-entry error (arbitrary subprocess
  execution is not supported in a hosted multi-tenant platform).

Red-green: written FIRST. Both helpers live in
``shared.voice_agents.tools.mcp.security`` which does not exist yet.
"""

from unittest.mock import patch

from shared.voice_agents.tools.mcp.models import McpServerConfig
from shared.voice_agents.tools.mcp.security import (
    McpServersParseResult,
    parse_mcp_servers_json,
    validate_mcp_server_url,
)


def _set_allow_local(value: bool) -> None:
    """Toggle the MCP_ALLOW_LOCAL_URLS env var for a test."""
    import os

    if value:
        os.environ["MCP_ALLOW_LOCAL_URLS"] = "true"
    else:
        os.environ.pop("MCP_ALLOW_LOCAL_URLS", None)


def _patch_resolve(ips):
    """Patch ``_resolve_host`` to return a fixed list of IP strings (offline)."""
    return patch(
        "shared.voice_agents.tools.mcp.security._resolve_host",
        return_value=list(ips),
    )


class TestValidateMcpServerUrl:
    """SSRF guard for MCP server URLs."""

    def test_accepts_public_https_url(self):
        with _patch_resolve(["93.184.216.34"]):
            ok, reason = validate_mcp_server_url("https://example.com/mcp")
        assert ok is True
        assert reason == ""

    def test_rejects_non_http_scheme(self):
        # file:// / ftp:// etc. must never be accepted.
        ok, reason = validate_mcp_server_url("file:///etc/passwd")
        assert ok is False
        assert "http" in reason.lower()

    def test_rejects_url_userinfo_and_fragments(self):
        """MCP URLs cannot smuggle credentials or opaque metadata in the URL."""
        with _patch_resolve(["93.184.216.34"]):
            userinfo_ok, userinfo_reason = validate_mcp_server_url(
                "https://user:password@example.com/mcp"
            )
            fragment_ok, fragment_reason = validate_mcp_server_url(
                "https://example.com/mcp#token"
            )

        assert userinfo_ok is False
        assert "userinfo" in userinfo_reason.lower()
        assert fragment_ok is False
        assert "fragment" in fragment_reason.lower()

    def test_rejects_empty_and_none(self):
        assert validate_mcp_server_url("")[0] is False
        assert validate_mcp_server_url(None)[0] is False  # type: ignore[arg-type]

    def test_rejects_unresolvable_host(self):
        with patch(
            "shared.voice_agents.tools.mcp.security._resolve_host",
            side_effect=socket_gaierror(),
        ):
            ok, reason = validate_mcp_server_url("https://nonexistent.invalid/mcp")
        assert ok is False
        assert "resolve" in reason.lower()

    def test_rejects_private_ipv4(self):
        for ip in ("10.0.0.5", "172.16.0.1", "192.168.1.1"):
            with _patch_resolve([ip]):
                ok, reason = validate_mcp_server_url(f"https://{ip}/mcp")
            assert ok is False, f"{ip} should be blocked"
            assert "blocked" in reason.lower() or "private" in reason.lower()

    def test_rejects_loopback_without_flag(self):
        with _patch_resolve(["127.0.0.1"]):
            ok, reason = validate_mcp_server_url("https://127.0.0.1/mcp")
        assert ok is False
        assert "blocked" in reason.lower()

    def test_rejects_link_local_metadata_ip(self):
        # 169.254.169.254 is the cloud metadata endpoint — must never be
        # reachable from a user-configured server (SSRF → credential theft).
        with _patch_resolve(["169.254.169.254"]):
            ok, _ = validate_mcp_server_url("https://169.254.169.254/latest/meta-data/")
        assert ok is False

    def test_rejects_ipv6_loopback(self):
        with _patch_resolve(["::1"]):
            ok, _ = validate_mcp_server_url("https://[::1]/mcp")
        assert ok is False

    def test_rejects_plain_http_without_local_flag(self):
        _set_allow_local(False)
        with _patch_resolve(["93.184.216.34"]):
            ok, reason = validate_mcp_server_url("http://example.com/mcp")
        assert ok is False
        assert "http" in reason.lower() or "loopback" in reason.lower()

    def test_allows_http_to_loopback_with_local_flag(self):
        _set_allow_local(True)
        try:
            with _patch_resolve(["127.0.0.1"]):
                ok, reason = validate_mcp_server_url("http://127.0.0.1:8080/mcp")
            assert ok is True, reason
        finally:
            _set_allow_local(False)

    def test_local_http_flag_is_ignored_in_staging(self, monkeypatch):
        """The dev-only local URL escape hatch cannot be enabled in staging."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        _set_allow_local(True)
        try:
            with _patch_resolve(["127.0.0.1"]):
                ok, reason = validate_mcp_server_url("http://127.0.0.1:8080/mcp")
            assert ok is False
            assert "blocked" in reason.lower() or "http" in reason.lower()
        finally:
            _set_allow_local(False)

    def test_rejects_http_to_public_host_even_with_local_flag(self):
        # The local flag only unlocks loopback for dev/test, never public http.
        _set_allow_local(True)
        try:
            with _patch_resolve(["93.184.216.34"]):
                ok, _ = validate_mcp_server_url("http://example.com/mcp")
            assert ok is False
        finally:
            _set_allow_local(False)

    def test_rejects_dns_rebinding_to_private_ip(self):
        # A public-looking hostname that resolves to a private IP must be
        # blocked (best-effort rebinding re-check at resolve time).
        with _patch_resolve(["10.1.2.3"]):
            ok, _ = validate_mcp_server_url("https://rebinding.attacker.com/mcp")
        assert ok is False


class socket_gaierror(Exception):
    """Stand-in for socket.gaierror so the test stays offline-clean."""

    pass


class TestParseMcpServersJson:
    """Parse Claude Desktop / VS Code ``mcpServers`` JSON."""

    def test_accepts_bare_single_server_object(self):
        raw = '{"url": "https://example.com/mcp", "headers": {"X-Key": "v"}}'
        result = parse_mcp_servers_json(raw)
        assert isinstance(result, McpServersParseResult)
        assert len(result.servers) == 1
        assert result.errors == []
        cfg = result.servers[0]
        assert cfg.url == "https://example.com/mcp"
        assert cfg.headers == {"X-Key": "v"}

    def test_accepts_mcp_servers_map(self):
        raw = (
            '{"mcpServers": {'
            '  "calendar": {"url": "https://cal.example.com/mcp"},'
            '  "weather": {"url": "https://wx.example.com/mcp", "headers": {"Auth": "x"}}'
            "}}"
        )
        result = parse_mcp_servers_json(raw)
        assert len(result.servers) == 2
        assert {s.name for s in result.servers} == {"calendar", "weather"}
        wx = next(s for s in result.servers if s.name == "weather")
        assert wx.headers == {"Auth": "x"}

    def test_rejects_stdio_entries_with_per_entry_error(self):
        raw = (
            '{"mcpServers": {'
            '  "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-fs"]},'
            '  "calendar": {"url": "https://cal.example.com/mcp"}'
            "}}"
        )
        result = parse_mcp_servers_json(raw)
        # The HTTP server is still returned; the stdio server is reported as an error.
        assert len(result.servers) == 1
        assert result.servers[0].name == "calendar"
        assert len(result.errors) == 1
        assert result.errors[0].name == "filesystem"
        assert "stdio" in result.errors[0].message.lower()

    def test_rejects_entry_without_url(self):
        raw = '{"mcpServers": {"broken": {"headers": {"x": "y"}}}}'
        result = parse_mcp_servers_json(raw)
        assert result.servers == []
        assert len(result.errors) == 1
        assert "url" in result.errors[0].message.lower()

    def test_rejects_malformed_json(self):
        result = parse_mcp_servers_json("{not valid json")
        assert result.servers == []
        assert len(result.errors) == 1
        assert "json" in result.errors[0].message.lower()

    def test_rejects_non_object_json(self):
        result = parse_mcp_servers_json('["a", "b"]')
        assert result.servers == []
        assert len(result.errors) == 1

    def test_server_name_defaults_when_unnamed(self):
        raw = '{"url": "https://example.com/mcp"}'
        result = parse_mcp_servers_json(raw)
        assert len(result.servers) == 1
        # Bare object has no key to derive a name from; must still be non-empty.
        assert result.servers[0].name

    def test_headers_values_coerced_to_strings(self):
        raw = '{"url": "https://example.com/mcp", "headers": {"X-Count": 3}}'
        result = parse_mcp_servers_json(raw)
        assert result.servers[0].headers == {"X-Count": "3"}

    def test_returns_mcp_server_config_instances(self):
        raw = '{"url": "https://example.com/mcp"}'
        result = parse_mcp_servers_json(raw)
        assert isinstance(result.servers[0], McpServerConfig)

    def test_accepts_vscode_servers_and_server_url_aliases(self):
        """Parse VS Code-style ``servers`` entries and vendor URL aliases."""
        raw = (
            '{"servers": {'
            '"remote": {"type": "http", "url": "https://remote.example/mcp"},'
            '"named": {"type": "streamableHttp", "serverUrl": "https://named.example/mcp"}'
            "}}"
        )

        result = parse_mcp_servers_json(raw)

        assert result.errors == []
        assert {server.name for server in result.servers} == {"remote", "named"}
        assert {server.url for server in result.servers} == {
            "https://remote.example/mcp",
            "https://named.example/mcp",
        }

    def test_normalizes_api_key_placeholders_without_requiring_a_platform_key(self):
        """Credential placeholders become org-owned secret templates."""
        raw = (
            '{"mcpServers": {"weather": {'
            '"url": "https://weather.example/mcp",'
            '"headers": {"X-API-Key": "${input:weather_key}"}'
            "}}}"
        )

        result = parse_mcp_servers_json(raw)

        server = result.servers[0]
        assert server.auth_type == "api_key"
        assert server.requires_auth is True
        assert server.headers == {}
        assert server.secret_headers == {"X-API-Key": "{{KEY}}"}

    def test_requires_org_key_for_explicit_api_key_auth_without_header(self):
        """An auth declaration alone must not make an API key optional."""
        raw = (
            '{"servers": {"weather": {'
            '"url": "https://weather.example/mcp",'
            '"authentication": {"type": "api_key", "header": "X-API-Key"}'
            "}}}"
        )

        server = parse_mcp_servers_json(raw).servers[0]

        assert server.auth_type == "api_key"
        assert server.requires_auth is True

    def test_redacts_literal_api_key_from_parse_result(self):
        """Pasting a real key must not echo it back to the browser."""
        raw = (
            '{"mcpServers": {"weather": {'
            '"url": "https://weather.example/mcp",'
            '"headers": {"X-API-Key": "real-secret"}'
            "}}}"
        )

        server = parse_mcp_servers_json(raw).servers[0]

        assert server.secret_headers == {"X-API-Key": "{{KEY}}"}
        assert server.requires_auth is True

    def test_accepts_nested_mcp_servers_wrapper(self):
        """Handle host exports that nest their server collection under mcp."""
        raw = (
            '{"mcp": {"servers": {"calendar": {'
            '"endpoint": "https://calendar.example/mcp"'
            "}}}}"
        )

        result = parse_mcp_servers_json(raw)

        assert result.errors == []
        assert result.servers[0].name == "calendar"
        assert result.servers[0].url == "https://calendar.example/mcp"

    def test_extracts_mcp_oauth_configuration_from_host_config(self):
        """Normalize common non-standard OAuth config aliases for persistence."""
        raw = (
            '{"mcpServers": {"calendar": {'
            '"url": "https://calendar.example/mcp",'
            '"auth": {"type": "oauth2",'
            '"authorization_endpoint": "https://auth.example/authorize",'
            '"token_endpoint": "https://auth.example/token",'
            '"scopes": "calendar.read calendar.write"}'
            "}}}"
        )

        result = parse_mcp_servers_json(raw)

        server = result.servers[0]
        assert server.auth_type == "oauth2"
        assert server.requires_auth is True
        assert server.auth_config == {
            "provider": "mcp",
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "scopes": ["calendar.read", "calendar.write"],
        }

    def test_extracts_oauth_client_and_registration_metadata(self):
        """Preserve public-client and DCR metadata from nested OAuth blocks."""
        raw = (
            '{"servers": {"calendar": {'
            '"url": "https://calendar.example/mcp",'
            '"oauth": {"type": "oauth2", "clientId": "public-client",'
            '"tokenEndpointAuthMethod": "client_secret_basic",'
            '"oauthMode": "generic",'
            '"registrationEndpoint": "https://auth.example/register",'
            '"resource_uri": "https://calendar.example/resource"}'
            "}}}"
        )

        server = parse_mcp_servers_json(raw).servers[0]

        assert server.auth_config["client_id"] == "public-client"
        assert server.auth_config["token_endpoint_auth_method"] == "client_secret_basic"
        assert server.auth_config["oauth_mode"] == "generic"
        assert (
            server.auth_config["registration_endpoint"]
            == "https://auth.example/register"
        )
        assert server.auth_config["resource"] == "https://calendar.example/resource"

    def test_reports_disabled_and_unsupported_transport_entries_individually(self):
        """A mixed paste reports non-runnable entries without dropping valid ones."""
        raw = (
            '{"mcpServers": {'
            '"disabled": {"url": "https://disabled.example/mcp", "disabled": true},'
            '"local": {"type": "stdio", "command": "npx", "args": ["server"]},'
            '"valid": {"url": "https://valid.example/mcp"}'
            "}}"
        )

        result = parse_mcp_servers_json(raw)

        assert [server.name for server in result.servers] == ["valid"]
        assert {error.name for error in result.errors} == {"disabled", "local"}
        assert any("disabled" in error.message.lower() for error in result.errors)
        assert any("stdio" in error.message.lower() for error in result.errors)
