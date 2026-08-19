"""Tests for runtime MCP credential-template resolution."""

from unittest.mock import Mock, patch

import pytest

from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.mcp.dispatch import mcp_server_config_from_agent_tool


def _agent_tool(
    *,
    api_key: str | None = None,
    public_headers: dict[str, str] | None = None,
    secret_headers: str | None = None,
    access_token: str | None = None,
) -> Mock:
    """Build a minimal MCP agent-tool double for dispatch tests."""
    agent_tool = Mock()
    agent_tool.tool = Mock(
        mcp_server_url="https://example.com/mcp",
        mcp_server_name="example",
        name="example_mcp",
        auth_type="oauth2" if access_token else "api_key",
        mcp_server_headers=public_headers
        or {
            "Authorization": "Bearer {{KEY}}",
            "X-Client": "24x7-ai",
        },
        mcp_server_secret_headers=secret_headers,
    )
    agent_tool.sensitive_config = {"api_key": api_key} if api_key else {}
    if access_token:
        agent_tool.sensitive_config["access_token"] = access_token
    return agent_tool


class TestMcpDispatch:
    """Runtime never sends a placeholder or a platform test credential."""

    @pytest.fixture(autouse=True)
    def mock_mcp_url_validation(self):
        """Keep header-merging tests independent of the test host's DNS."""
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.validate_mcp_server_url",
            return_value=(True, None),
        ):
            yield

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

    def test_oauth_bearer_replaces_stale_static_authorization_header(self):
        """OAuth connections must not silently send an old platform grant."""
        agent_tool = _agent_tool(
            access_token="user-oauth-token",
            public_headers={"Authorization": "Bearer stale-platform-token"},
        )

        config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.headers["Authorization"] == "Bearer user-oauth-token"

    def test_runtime_context_headers_carry_org_scheduling_context(self):
        """MCP receives org context without making it model-facing input."""
        agent_tool = _agent_tool(access_token="user-oauth-token")
        agent_tool.config = {
            "calendar_id": "clinic@example.com",
            "require_email": True,
        }

        config = mcp_server_config_from_agent_tool(
            agent_tool,
            runtime_context=ToolContext(
                organization_id="org-123",
                organization_timezone="America/Phoenix",
                session_id="session-123",
            ),
        )

        assert config.headers["X-247AI-Organization-Timezone"] == "America/Phoenix"
        assert config.headers["X-247AI-Organization-ID"] == "org-123"
        assert config.headers["X-247AI-Session-ID"] == "session-123"
        assert config.headers["X-247AI-Calendar-ID"] == "clinic@example.com"
        assert config.headers["X-247AI-Require-Email"] == "true"

    def test_runtime_ssrf_validation_happens_before_credentials_are_merged(self):
        """A saved MCP URL is rechecked before any bearer/header is decrypted."""
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.validate_mcp_server_url",
            return_value=(False, "URL resolves to a blocked address"),
        ):
            with pytest.raises(ValueError, match="blocked address"):
                mcp_server_config_from_agent_tool(
                    _agent_tool(access_token="user-oauth-token")
                )

    def test_shipped_appointment_connector_can_use_loopback_without_global_local_flag(
        self,
    ):
        """Only the named, shipped connector receives the loopback exception."""
        agent_tool = _agent_tool(access_token="user-oauth-token")
        agent_tool.tool.name = "Google_calendar_appointment_mcp"
        agent_tool.tool.mcp_server_url = "http://127.0.0.1:8733/mcp"
        with patch(
            "shared.voice_agents.tools.mcp.dispatch.validate_mcp_server_url",
            return_value=(False, "loopback blocked"),
        ):
            config = mcp_server_config_from_agent_tool(agent_tool)

        assert config.url == "http://127.0.0.1:8733/mcp"
