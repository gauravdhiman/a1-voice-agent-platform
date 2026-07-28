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

    def test_merges_encrypted_secret_headers(self):
        """Encrypted server-level secret headers are decrypted and merged in,
        without clobbering the public static headers (secret wins on conflict)."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(
            mcp_server_headers={"X-Public": "pub"},
            mcp_server_secret_headers="encrypted-blob",
        )
        agent_tool = _agent_tool(pt)
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-Secret": "secret-value", "X-Public": "override"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["X-Public"] == "override"  # secret wins
        assert config.headers["X-Secret"] == "secret-value"

    def test_secret_headers_decryption_failure_is_skipped(self):
        """A decryption failure must not crash dispatch — log and skip secrets."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(
            mcp_server_headers={"X-Public": "pub"},
            mcp_server_secret_headers="garbage",
        )
        agent_tool = _agent_tool(pt)
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            side_effect=Exception("bad key"),
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        # Public headers survive; no secret headers added.
        assert config.headers == {"X-Public": "pub"}

    def test_secret_headers_with_bearer_no_authorization_conflict(self):
        """Secret headers + per-user bearer: bearer added only if no
        Authorization is already present (server-level auth wins)."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(mcp_server_secret_headers="encrypted-blob")
        agent_tool = _agent_tool(pt, sensitive_config={"access_token": "user-tok"})
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-Secret": "s"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        # No Authorization in secret headers → bearer injected.
        assert config.headers["Authorization"] == "Bearer user-tok"
        assert config.headers["X-Secret"] == "s"


class TestMcpServerConfigKeyTemplate:
    """``{{KEY}}`` template substitution — the org-level API-key override.

    The publish-lifecycle model (RFC §6.6): a platform admin authors an MCP
    server whose server-level secret headers are a *template* with a
    ``{{KEY}}`` placeholder (e.g. ``{"Authorization": "Bearer {{KEY}}"}``).
    At runtime the placeholder is filled with the **org admin's** API key from
    ``agent_tool.sensitive_config["api_key"]`` — never the platform admin's
    transient test key. Literal values (no ``{{KEY}}``) pass through as fixed
    shared headers.
    """

    def test_template_substituted_with_org_api_key(self):
        """A ``{{KEY}}`` placeholder is filled with the org's API key."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(mcp_server_secret_headers="encrypted-blob")
        agent_tool = _agent_tool(
            pt, sensitive_config={"api_key": "org-key-123"}
        )
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"Authorization": "Bearer {{KEY}}"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["Authorization"] == "Bearer org-key-123"

    def test_template_skipped_without_org_key_no_platform_fallback(self):
        """A ``{{KEY}}`` placeholder with NO org key is dropped — the literal
        ``{{KEY}}`` is never sent, and the platform test key is never used at
        runtime (there is no fallback). The tool is simply in an
        'API key required' state."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(
            mcp_server_headers={"X-Public": "pub"},
            mcp_server_secret_headers="encrypted-blob",
        )
        agent_tool = _agent_tool(pt, sensitive_config={})  # no api_key
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-API-Key": "{{KEY}}"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        # Public header survives; the templated header is dropped entirely.
        assert config.headers == {"X-Public": "pub"}
        assert "X-API-Key" not in config.headers

    def test_literal_secret_header_passes_through_unchanged(self):
        """A secret header value with no ``{{KEY}}`` is used verbatim (the
        optional shared/fixed-key mode — platform admin's responsibility)."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(mcp_server_secret_headers="encrypted-blob")
        agent_tool = _agent_tool(pt)
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-Fixed": "shared-literal"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["X-Fixed"] == "shared-literal"

    def test_template_and_literal_coexist_in_same_secret_headers(self):
        """A mix of templated and literal secret headers resolves each
        independently — the org key fills ``{{KEY}}`` only in its own header."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(mcp_server_secret_headers="encrypted-blob")
        agent_tool = _agent_tool(
            pt, sensitive_config={"api_key": "org-key"}
        )
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-Fixed": "lit", "X-Api-Key": "{{KEY}}"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["X-Fixed"] == "lit"
        assert config.headers["X-Api-Key"] == "org-key"

    def test_template_authorization_suppresses_oauth_bearer(self):
        """When a ``{{KEY}}`` template resolves to an Authorization header, the
        per-user OAuth bearer is NOT injected (the org key wins; bearer only
        added when no Authorization is set)."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(mcp_server_secret_headers="encrypted-blob")
        # Both an org api_key and an OAuth access_token present — the template
        # Authorization must win over the OAuth bearer.
        agent_tool = _agent_tool(
            pt,
            sensitive_config={"api_key": "org-key", "access_token": "user-tok"},
        )
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"Authorization": "Bearer {{KEY}}"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["Authorization"] == "Bearer org-key"

    def test_template_only_substitutes_placeholder_not_full_value(self):
        """Only the ``{{KEY}}`` marker is replaced; surrounding text is
        preserved (e.g. a custom prefix or suffix)."""
        from unittest.mock import patch

        pt = _mcp_platform_tool(mcp_server_secret_headers="encrypted-blob")
        agent_tool = _agent_tool(pt, sensitive_config={"api_key": "K"})
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-Token": "Token {{KEY}} suffix"},
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["X-Token"] == "Token K suffix"


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