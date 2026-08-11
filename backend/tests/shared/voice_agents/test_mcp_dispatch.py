"""Tests for runtime MCP credential-template resolution."""

from unittest.mock import Mock, patch

from shared.voice_agents.tools.mcp.dispatch import mcp_server_config_from_agent_tool


def _agent_tool(
    *,
    api_key: str | None = None,
    public_headers: dict[str, str] | None = None,
    secret_headers: str | None = None,
) -> Mock:
    """Build a minimal MCP agent-tool double for dispatch tests."""
    agent_tool = Mock()
    agent_tool.tool = Mock(
        mcp_server_url="https://example.com/mcp",
        mcp_server_name="example",
        name="example_mcp",
        mcp_server_headers=public_headers
        or {
            "Authorization": "Bearer {{KEY}}",
            "X-Client": "24x7-ai",
        },
        mcp_server_secret_headers=secret_headers,
    )
    agent_tool.sensitive_config = {"api_key": api_key} if api_key else {}
    return agent_tool


class TestMcpDispatch:
    """Runtime never sends a placeholder or a platform test credential."""

    def test_public_header_placeholder_is_filled_from_org_key(self):
        config = mcp_server_config_from_agent_tool(_agent_tool(api_key="org-key"))

        assert config.headers["Authorization"] == "Bearer org-key"
        assert config.headers["X-Client"] == "24x7-ai"

    def test_missing_org_key_drops_public_placeholder_header(self):
        config = mcp_server_config_from_agent_tool(_agent_tool())

        assert "Authorization" not in config.headers
        assert "{{KEY}}" not in str(config.headers)

    def test_org_key_overrides_literal_platform_api_key(self):
        """An org key wins even when the platform stored a literal fallback."""
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-API-Key": "platform-key"},
        ):
            config = mcp_server_config_from_agent_tool(
                _agent_tool(api_key="org-key", public_headers={}, secret_headers="enc")
            )

        assert config.headers["X-API-Key"] == "org-key"

    def test_platform_literal_is_fallback_without_org_key(self):
        """A configured platform key remains usable when the org has none."""
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.decrypt_data",
            return_value={"X-API-Key": "platform-key"},
        ):
            config = mcp_server_config_from_agent_tool(
                _agent_tool(public_headers={}, secret_headers="enc")
            )

        assert config.headers["X-API-Key"] == "platform-key"
