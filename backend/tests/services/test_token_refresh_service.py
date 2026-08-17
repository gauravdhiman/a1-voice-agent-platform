"""
Tests for token refresh service.
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from src.services.token_refresh_service import OAuthRefreshRequest, TokenRefreshService

from shared.voice_agents.tool_models import AgentTool, PlatformTool, ToolSource
from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tools.base.auth_config import GoogleAuthConfig


@pytest.fixture
def tool_service():
    """Mock ToolService."""
    return MagicMock(spec=ToolService)


@pytest.fixture
def token_refresh_service(tool_service):
    """TokenRefreshService with mocked ToolService."""
    return TokenRefreshService(tool_service)


@pytest.fixture(autouse=True)
def allow_test_oauth_hosts(monkeypatch):
    """Keep token-endpoint tests deterministic while exercising DNS checks."""
    monkeypatch.setattr(
        "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
        lambda _host: ["93.184.216.34"],
    )


@pytest.fixture
def sample_agent_tool():
    """Sample AgentTool with OAuth tokens."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=10)  # Expires in 10 minutes

    platform_tool = MagicMock(spec=PlatformTool)
    platform_tool.name = "Test Tool"
    platform_tool.auth_config = {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "token_url": "https://oauth.example.com/token",
    }

    agent_tool = MagicMock(spec=AgentTool)
    agent_tool.id = uuid4()
    agent_tool.tool = platform_tool
    agent_tool.sensitive_config = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": expires_at.timestamp(),
    }

    return agent_tool


@pytest.mark.asyncio
class TestTokenRefreshService:
    """Test cases for TokenRefreshService."""

    async def test_init(self, tool_service):
        """Test service initialization."""
        service = TokenRefreshService(tool_service)
        assert service.tool_service == tool_service
        assert service.running is False
        assert service.task is None

    async def test_start_service_not_running(self, token_refresh_service):
        """Test starting service when not running."""
        await token_refresh_service.start()
        assert token_refresh_service.running is True
        assert token_refresh_service.task is not None
        assert not token_refresh_service.task.done()

        # Clean up
        await token_refresh_service.stop()

    async def test_start_service_already_running(self, token_refresh_service):
        """Test starting service when already running."""
        await token_refresh_service.start()
        assert token_refresh_service.running is True

        # Try to start again
        await token_refresh_service.start()
        assert token_refresh_service.running is True

    async def test_stop_service_running(self, token_refresh_service):
        """Test stopping service when running."""
        await token_refresh_service.start()
        assert token_refresh_service.running is True

        await token_refresh_service.stop()
        assert token_refresh_service.running is False
        assert token_refresh_service.task.cancelled()

    async def test_stop_service_not_running(self, token_refresh_service):
        """Test stopping service when not running."""
        await token_refresh_service.stop()
        assert token_refresh_service.running is False

    async def test_check_and_refresh_token_no_sensitive_config(
        self, token_refresh_service, sample_agent_tool
    ):
        """Test token check with no sensitive config."""
        sample_agent_tool.sensitive_config = None

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_no_expires_at(
        self, token_refresh_service, sample_agent_tool
    ):
        """Test token check with no expires_at."""
        sample_agent_tool.sensitive_config = {"access_token": "test"}

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_missing_expiry_with_refresh_token_is_recovered(
        self, token_refresh_service, sample_agent_tool
    ):
        """Legacy connections without expiry metadata get one refresh attempt."""
        sample_agent_tool.sensitive_config = {
            "access_token": "test",
            "refresh_token": "refresh",
        }

        needs_refresh, minutes_until_expiry = token_refresh_service._is_token_expiring(
            sample_agent_tool
        )

        assert needs_refresh is True
        assert minutes_until_expiry is None

    async def test_check_and_refresh_token_expired(
        self, token_refresh_service, sample_agent_tool
    ):
        """Attempt refresh for an expired token when a refresh token exists."""
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(minutes=30)
        sample_agent_tool.sensitive_config["expires_at"] = expired_time.timestamp()

        needs_refresh, minutes_until_expiry = token_refresh_service._is_token_expiring(
            sample_agent_tool
        )
        assert needs_refresh is True
        assert minutes_until_expiry is not None
        assert minutes_until_expiry < 0

    async def test_check_and_refresh_token_valid_long_time(
        self, token_refresh_service, sample_agent_tool
    ):
        """Test token check with token valid for long time."""
        now = datetime.now(timezone.utc)
        far_future = now + timedelta(hours=2)  # Valid for 2 hours
        sample_agent_tool.sensitive_config["expires_at"] = far_future.timestamp()

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_no_refresh_token(
        self, token_refresh_service, sample_agent_tool
    ):
        """Test token check with no refresh token."""
        sample_agent_tool.sensitive_config["refresh_token"] = None
        sample_agent_tool.sensitive_config["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).timestamp()

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_no_auth_config(
        self, token_refresh_service, sample_agent_tool
    ):
        """Test token check with no auth config."""
        sample_agent_tool.tool.auth_config = None

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_unexpected_refresh_errors_do_not_log_exception_details(
        self, token_refresh_service, sample_agent_tool, caplog
    ):
        """Unexpected provider/config errors cannot leak token-like text."""
        with patch.object(
            token_refresh_service,
            "_resolve_oauth_config",
            side_effect=RuntimeError("access_token=do-not-log"),
        ):
            result = await token_refresh_service._check_and_refresh_token(
                sample_agent_tool
            )

        assert result is False
        assert "do-not-log" not in caplog.text

    async def test_refresh_batch_does_not_log_worker_exception_details(
        self, token_refresh_service, sample_agent_tool, caplog
    ):
        """A failed concurrent refresh cannot echo provider exception text."""
        token_refresh_service._get_tools_requiring_auth = AsyncMock(
            return_value=[sample_agent_tool]
        )
        token_refresh_service._check_and_refresh_token = AsyncMock(
            side_effect=RuntimeError("refresh_token=do-not-log")
        )

        await token_refresh_service._refresh_expired_tokens()

        assert "do-not-log" not in caplog.text

    async def test_check_and_refresh_token_success(
        self, token_refresh_service, sample_agent_tool
    ):
        """Test successful token refresh."""
        # Mock the distributed refresh lock (acquired -> refresh proceeds -> released).
        token_refresh_service.tool_service.claim_refresh_lock = AsyncMock(
            return_value="claim-1"
        )
        token_refresh_service.tool_service.release_refresh_lock = AsyncMock(
            return_value=True
        )

        # Mock the OAuth manager
        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            mock_get_manager.return_value = mock_manager

            # Mock the token refresh
            new_tokens = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
            }

            with patch.object(
                token_refresh_service, "_refresh_oauth_token", new_callable=AsyncMock
            ) as mock_refresh:
                mock_refresh.return_value = new_tokens

                with patch.object(
                    token_refresh_service, "_update_agent_tool", new_callable=AsyncMock
                ) as mock_update:
                    result = await token_refresh_service._check_and_refresh_token(
                        sample_agent_tool
                    )
                    assert result is True

                    # Verify refresh was called
                    mock_refresh.assert_called_once()
                    # Verify update was called
                    mock_update.assert_called_once()
                    # Lock acquired before refresh and released after.
                    token_refresh_service.tool_service.claim_refresh_lock.assert_awaited_once()
                    token_refresh_service.tool_service.release_refresh_lock.assert_awaited_once()

    async def test_resolve_mcp_oauth_refresh_config(self, token_refresh_service):
        """Build a generic MCP refresh request without provider credentials."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Generic MCP"
        platform_tool.mcp_server_url = "https://mcp.example.com"
        platform_tool.auth_config = {
            "provider": "mcp",
            "client_id": "registered-client",
            "token_url": "https://mcp.example.com/oauth/token",
            "resource": "https://mcp.example.com",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {
            "refresh_token": "refresh-token",
            "oauth_client_id": "stored-client",
            "resource": "https://mcp.example.com/resource",
        }

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://mcp.example.com/oauth/token",
            )
            manager.get_credentials.side_effect = ValueError(
                "MCP uses dynamic credentials"
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.token_url == "https://mcp.example.com/oauth/token"
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "refresh-token",
            "client_id": "stored-client",
            "resource": "https://mcp.example.com/resource",
        }

    async def test_resolve_mcp_oauth_refresh_config_ignores_vendor_provider_name(
        self, token_refresh_service
    ):
        """MCP refresh works when host metadata names the vendor provider."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Linear"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.mcp_server_url = "https://mcp.linear.app/mcp"
        platform_tool.auth_config = {
            "provider": "linear",
            "token_url": "https://mcp.linear.app/oauth/token",
            "resource": "https://mcp.linear.app/mcp",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {
            "refresh_token": "refresh-token",
            "oauth_client_id": "registered-client",
            "resource": "https://mcp.linear.app/mcp",
        }

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "linear",
                "https://mcp.linear.app/oauth/token",
            )
            manager.get_credentials.side_effect = ValueError(
                "Linear is not a native provider"
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.token_url == "https://mcp.linear.app/oauth/token"
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "refresh-token",
            "client_id": "registered-client",
            "resource": "https://mcp.linear.app/mcp",
        }
        manager.get_auth_data.assert_not_called()

    async def test_resolve_discovered_mcp_metadata_from_encrypted_connection_state(
        self, token_refresh_service
    ):
        """Refresh still works when discovery metadata was absent at authoring time."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Discovered MCP"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.mcp_server_url = "https://mcp.example.com"
        platform_tool.auth_config = {"provider": "mcp"}
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {
            "refresh_token": "refresh-token",
            "oauth_client_id": "registered-client",
            "oauth_token_url": "https://mcp.example.com/oauth/token",
            "oauth_token_endpoint_auth_method": "none",
            "resource": "https://mcp.example.com",
        }

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = ("mcp", "")
            manager.get_credentials.side_effect = ValueError("generic MCP")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.token_url == "https://mcp.example.com/oauth/token"
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "refresh-token",
            "client_id": "registered-client",
            "resource": "https://mcp.example.com",
        }

    async def test_resolve_unknown_native_provider_from_auth_config(
        self, token_refresh_service
    ):
        """An OAuth provider need not be registered in the native provider map."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Salesforce"
        platform_tool.tool_source = ToolSource.LEGACY
        platform_tool.auth_config = {
            "provider": "salesforce",
            "client_id": "salesforce-client",
            "client_secret": "salesforce-secret",
            "token_url": "https://login.salesforce.com/services/oauth2/token",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "salesforce-refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "salesforce",
                "https://login.salesforce.com/services/oauth2/token",
            )
            manager.get_credentials.side_effect = ValueError(
                "Salesforce is not a native provider"
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert isinstance(request, OAuthRefreshRequest)
        assert request.token_url == (
            "https://login.salesforce.com/services/oauth2/token"
        )
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "salesforce-refresh",
            "client_id": "salesforce-client",
            "client_secret": "salesforce-secret",
        }

    async def test_resolve_registered_provider_from_tool_metadata_when_env_is_missing(
        self, token_refresh_service
    ):
        """A registered provider can use row metadata when deployment credentials are absent."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Google-compatible tool"
        platform_tool.tool_source = ToolSource.LEGACY
        platform_tool.auth_config = {
            "provider": "google",
            "client_id": "row-client",
            "client_secret": "row-secret",
            "token_url": "https://oauth.example.com/token",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "row-refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.return_value = MagicMock(
                client_id=None, client_secret=None
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.data["client_id"] == "row-client"
        assert request.data["client_secret"] == "row-secret"
        manager.get_auth_data.assert_not_called()

    async def test_resolve_registered_provider_prefers_encrypted_tool_secret(
        self, token_refresh_service
    ):
        """A per-tool encrypted secret must beat a shared provider secret."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Google-compatible tool"
        platform_tool.tool_source = ToolSource.LEGACY
        platform_tool.oauth_client_secret_encrypted = "encrypted-tool-secret"
        platform_tool.auth_config = {
            "provider": "google",
            "token_url": "https://oauth.example.com/token",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "row-refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager, patch(
            "src.services.token_refresh_service.decrypt_data",
            return_value={"client_secret": "encrypted-tool-secret-value"},
        ):
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.return_value = MagicMock(
                client_id="env-client", client_secret="env-secret"
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "row-refresh",
            "client_id": "env-client",
            "client_secret": "encrypted-tool-secret-value",
        }
        manager.get_auth_data.assert_not_called()

    async def test_resolve_native_provider_without_any_client_id_returns_none(
        self, token_refresh_service
    ):
        """Do not send a refresh request with a null native client identifier."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Google-compatible tool"
        platform_tool.tool_source = ToolSource.LEGACY
        platform_tool.auth_config = {
            "provider": "google",
            "token_url": "https://oauth.example.com/token",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.return_value = MagicMock(
                client_id=None, client_secret=None
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is None

    async def test_resolve_public_generic_client(self, token_refresh_service):
        """Public OAuth clients send a client_id without a client secret."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Public MCP"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.auth_config = {
            "provider": "mcp",
            "client_id": "public-client",
            "token_url": "https://mcp.example.com/oauth/token",
            "token_endpoint_auth_method": "none",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://mcp.example.com/oauth/token",
            )
            manager.get_credentials.side_effect = ValueError("generic MCP")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "refresh",
            "client_id": "public-client",
        }

    async def test_auth_config_value_reads_pydantic_oauth_config(
        self, token_refresh_service
    ):
        """Read OAuth metadata from the native Pydantic config representation."""
        auth_config = GoogleAuthConfig(
            scopes=["scope"],
            auth_url="https://oauth.example.com/authorize",
            token_url="https://oauth.example.com/token",
        )

        assert (
            token_refresh_service._auth_config_value(auth_config, "provider")
            == "google"
        )

    async def test_resolve_native_provider_handles_auth_data_error(
        self, token_refresh_service
    ):
        """Return no request when a native manager cannot build its payload."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Google-compatible tool"
        platform_tool.tool_source = ToolSource.LEGACY
        platform_tool.auth_config = {
            "provider": "google",
            "token_url": "https://oauth.example.com/token",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "google",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.return_value = MagicMock(client_id="id")
            manager.get_auth_data.side_effect = ValueError("invalid credentials")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is None

    async def test_resolve_mcp_client_secret_basic_auth(self, token_refresh_service):
        """MCP refresh supports OAuth clients authenticated with HTTP Basic."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Private MCP"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.mcp_server_url = "https://mcp.example.com/mcp"
        platform_tool.auth_config = {
            "provider": "mcp",
            "client_id": "mcp-client",
            "client_secret": "mcp-secret",
            "token_url": "https://mcp.example.com/oauth/token",
            "resource": "https://mcp.example.com/mcp",
            "token_endpoint_auth_method": "client_secret_basic",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "mcp-refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://mcp.example.com/oauth/token",
            )
            manager.get_credentials.side_effect = ValueError(
                "MCP uses dynamic credentials"
            )
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        expected_basic = base64.b64encode(b"mcp-client:mcp-secret").decode()
        assert request is not None
        assert request.data == {
            "grant_type": "refresh_token",
            "refresh_token": "mcp-refresh",
            "resource": "https://mcp.example.com/mcp",
        }
        assert request.headers["Authorization"] == f"Basic {expected_basic}"

    async def test_resolve_generic_oauth_without_client_id_returns_none(
        self, token_refresh_service
    ):
        """Generic OAuth cannot refresh without a stable client identifier."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Incomplete MCP"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.mcp_server_url = "https://mcp.example.com/mcp"
        platform_tool.auth_config = {
            "provider": "mcp",
            "token_url": "https://mcp.example.com/oauth/token",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager, patch.dict("os.environ", {}, clear=True):
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://mcp.example.com/oauth/token",
            )
            manager.get_credentials.side_effect = ValueError("generic MCP")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is None

    async def test_resolve_basic_client_without_secret_returns_none(
        self, token_refresh_service
    ):
        """HTTP Basic token endpoints require a client secret."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Private MCP"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.auth_config = {
            "provider": "mcp",
            "client_id": "client",
            "token_url": "https://mcp.example.com/oauth/token",
            "token_endpoint_auth_method": "client_secret_basic",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://mcp.example.com/oauth/token",
            )
            manager.get_credentials.side_effect = ValueError("generic MCP")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is None

    async def test_resolve_unknown_client_auth_method_returns_none(
        self, token_refresh_service
    ):
        """Reject proprietary token endpoint authentication until supported."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Custom OAuth"
        platform_tool.tool_source = ToolSource.LEGACY
        platform_tool.auth_config = {
            "provider": "custom",
            "client_id": "client",
            "client_secret": "secret",
            "token_url": "https://oauth.example.com/token",
            "token_endpoint_auth_method": "private_key_jwt",
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "custom",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.side_effect = ValueError("custom provider")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is None

    async def test_resolve_only_unsupported_advertised_auth_returns_none(
        self, token_refresh_service
    ):
        """Do not fall back to client_secret_post for proprietary server metadata."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Custom OAuth"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.auth_config = {
            "provider": "mcp",
            "client_id": "client",
            "client_secret": "secret",
            "token_url": "https://oauth.example.com/token",
            "token_endpoint_auth_methods_supported": ["private_key_jwt"],
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.side_effect = ValueError("custom provider")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is None

    async def test_resolve_prefers_supported_advertised_auth_method(
        self, token_refresh_service
    ):
        """Generic refresh chooses a supported method from mixed capabilities."""
        platform_tool = MagicMock(spec=PlatformTool)
        platform_tool.name = "Mixed OAuth"
        platform_tool.tool_source = ToolSource.MCP
        platform_tool.auth_config = {
            "provider": "mcp",
            "client_id": "client",
            "client_secret": "secret",
            "token_url": "https://oauth.example.com/token",
            "token_endpoint_auth_methods_supported": [
                "private_key_jwt",
                "client_secret_basic",
            ],
        }
        agent_tool = MagicMock(spec=AgentTool)
        agent_tool.tool = platform_tool
        agent_tool.sensitive_config = {"refresh_token": "refresh"}

        with patch(
            "src.services.token_refresh_service.get_oauth_manager"
        ) as get_manager:
            manager = MagicMock()
            manager.extract_oauth_config.return_value = (
                "mcp",
                "https://oauth.example.com/token",
            )
            manager.get_credentials.side_effect = ValueError("custom provider")
            get_manager.return_value = manager

            request = token_refresh_service._resolve_oauth_config(agent_tool)

        assert request is not None
        assert request.headers["Authorization"].startswith("Basic ")
        assert "client_secret" not in request.data

    async def test_refresh_oauth_token_success(self, token_refresh_service):
        """Test successful OAuth token refresh."""
        token_url = "https://oauth.example.com/token"
        oauth_data = {
            "grant_type": "refresh_token",
            "refresh_token": "test_refresh_token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
        }

        expected_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await token_refresh_service._refresh_oauth_token(
                token_url, oauth_data
            )
            assert result == expected_response

            mock_client.post.assert_called_once_with(token_url, data=oauth_data)

    async def test_refresh_oauth_token_failure(self, token_refresh_service):
        """Test OAuth token refresh failure."""
        token_url = "https://oauth.example.com/token"
        oauth_data = {"grant_type": "refresh_token"}

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await token_refresh_service._refresh_oauth_token(
                token_url, oauth_data
            )
            assert result is None

    async def test_refresh_oauth_token_rejects_private_dns_target(
        self, token_refresh_service
    ):
        """A token endpoint cannot resolve into a private network at refresh time."""
        with patch(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            return_value=["10.20.30.40"],
        ), patch("httpx.AsyncClient") as async_client:
            result = await token_refresh_service._refresh_oauth_token(
                "https://oauth.example.com/token",
                {"grant_type": "refresh_token"},
            )

        assert result is None
        async_client.assert_not_called()

    async def test_refresh_oauth_token_retries_transient_provider_failure(
        self, token_refresh_service
    ):
        """Retry transport and 5xx failures without retrying client errors."""
        token_url = "https://oauth.example.com/token"
        oauth_data = {"grant_type": "refresh_token", "refresh_token": "r"}

        failed_response = MagicMock(status_code=503, text="temporarily unavailable")
        success_response = MagicMock(status_code=200)
        success_response.json.return_value = {
            "access_token": "new",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = [failed_response, success_response]
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            with patch(
                "src.services.token_refresh_service.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await token_refresh_service._refresh_oauth_token(
                    token_url, oauth_data
                )

        assert result == {"access_token": "new", "expires_in": 3600}
        assert mock_client.post.await_count == 2
        sleep.assert_awaited_once()

    async def test_refresh_oauth_token_sends_client_auth_headers(
        self, token_refresh_service
    ):
        """Send the configured client-auth headers to the token endpoint."""
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"access_token": "new"}
        headers = {"Authorization": "Basic abc"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await token_refresh_service._refresh_oauth_token(
                "https://oauth.example.com/token",
                {"grant_type": "refresh_token"},
                headers=headers,
            )

        mock_client.post.assert_awaited_once_with(
            "https://oauth.example.com/token",
            data={"grant_type": "refresh_token"},
            headers=headers,
        )

    async def test_refresh_oauth_token_retries_transport_failures(
        self, token_refresh_service
    ):
        """Retry an HTTP transport failure before returning the provider response."""
        success_response = MagicMock(status_code=200)
        success_response.json.return_value = {"access_token": "new"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = [
                httpx.ConnectError("temporary failure"),
                success_response,
            ]
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            with patch(
                "src.services.token_refresh_service.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await token_refresh_service._refresh_oauth_token(
                    "https://oauth.example.com/token",
                    {"grant_type": "refresh_token"},
                )

        assert result == {"access_token": "new"}
        assert mock_client.post.await_count == 2
        sleep.assert_awaited_once()

    async def test_refresh_oauth_token_returns_none_after_transport_retries(
        self, token_refresh_service
    ):
        """Stop after the bounded number of transport retries."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = [httpx.ConnectError("temporary failure")] * 3
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            with patch(
                "src.services.token_refresh_service.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await token_refresh_service._refresh_oauth_token(
                    "https://oauth.example.com/token",
                    {"grant_type": "refresh_token"},
                )

        assert result is None
        assert mock_client.post.await_count == 3
        assert sleep.await_count == 2

    async def test_refresh_oauth_token_rejects_invalid_json_without_logging_body(
        self, token_refresh_service, caplog
    ):
        """Reject a successful HTTP response that is not valid JSON."""
        response = MagicMock(status_code=200)
        response.json.side_effect = ValueError(
            "refresh_token=do-not-log-in-provider-error"
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await token_refresh_service._refresh_oauth_token(
                "https://oauth.example.com/token", {"grant_type": "refresh_token"}
            )

        assert result is None
        assert "do-not-log-in-provider-error" not in caplog.text

    async def test_refresh_transport_logs_do_not_include_endpoint_query_data(
        self, token_refresh_service, caplog
    ):
        """Token endpoint URLs are not safe to include in retry log records."""
        token_url = "https://oauth.example.com/token?client_secret=do-not-log"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("temporary failure")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            with patch(
                "src.services.token_refresh_service.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                await token_refresh_service._refresh_oauth_token(
                    token_url, {"grant_type": "refresh_token"}
                )

        assert "do-not-log" not in caplog.text

    async def test_refresh_oauth_token_rejects_non_object_json(
        self, token_refresh_service
    ):
        """Reject a successful HTTP response whose JSON body is a list."""
        response = MagicMock(status_code=200)
        response.json.return_value = ["not", "a", "token", "object"]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await token_refresh_service._refresh_oauth_token(
                "https://oauth.example.com/token", {"grant_type": "refresh_token"}
            )

        assert result is None

    async def test_perform_refresh_defaults_expiry_when_provider_omits_expires_in(
        self, token_refresh_service, tool_service, sample_agent_tool
    ):
        """A successful response without expires_in remains refreshable."""
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)
        at = sample_agent_tool
        at.sensitive_config["expires_at"] = datetime.now(timezone.utc).timestamp()

        with patch.object(
            token_refresh_service,
            "_refresh_oauth_token",
            new_callable=AsyncMock,
            return_value={
                "access_token": "new-access",
                "refresh_token": "rotated-refresh",
            },
        ), patch.object(
            token_refresh_service,
            "_update_agent_tool",
            new_callable=AsyncMock,
            return_value=True,
        ) as update:
            result = await token_refresh_service._perform_token_refresh(
                at,
                {"grant_type": "refresh_token"},
                "https://oauth.example.com/token",
            )

        assert result is True
        updated_config = update.await_args.kwargs["sensitive_config"]
        assert updated_config["access_token"] == "new-access"
        assert updated_config["refresh_token"] == "rotated-refresh"
        assert updated_config["expires_at"] > datetime.now(timezone.utc).timestamp()

    async def test_perform_refresh_preserves_refresh_token_when_provider_returns_null(
        self, token_refresh_service, tool_service, sample_agent_tool
    ):
        """Do not destroy a usable refresh token when a provider omits rotation."""
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)

        with patch.object(
            token_refresh_service,
            "_refresh_oauth_token",
            new_callable=AsyncMock,
            return_value={"access_token": "new-access", "refresh_token": None},
        ), patch.object(
            token_refresh_service,
            "_update_agent_tool",
            new_callable=AsyncMock,
            return_value=True,
        ) as update:
            result = await token_refresh_service._perform_token_refresh(
                sample_agent_tool,
                {"grant_type": "refresh_token"},
                "https://oauth.example.com/token",
            )

        assert result is True
        updated_config = update.await_args.kwargs["sensitive_config"]
        assert updated_config["refresh_token"] == "test_refresh_token"

    async def test_perform_refresh_defaults_expiry_for_non_positive_expires_in(
        self, token_refresh_service, tool_service, sample_agent_tool
    ):
        """Treat zero or negative provider lifetimes as an omitted expiry."""
        tool_service.claim_refresh_lock = AsyncMock(return_value="claim-1")
        tool_service.release_refresh_lock = AsyncMock(return_value=True)

        with patch.object(
            token_refresh_service,
            "_refresh_oauth_token",
            new_callable=AsyncMock,
            return_value={"access_token": "new-access", "expires_in": 0},
        ), patch.object(
            token_refresh_service,
            "_update_agent_tool",
            new_callable=AsyncMock,
            return_value=True,
        ) as update:
            result = await token_refresh_service._perform_token_refresh(
                sample_agent_tool,
                {"grant_type": "refresh_token"},
                "https://oauth.example.com/token",
            )

        assert result is True
        assert update.await_args.kwargs["sensitive_config"]["expires_at"] > (
            datetime.now(timezone.utc).timestamp()
        )

    async def test_update_agent_tool_success(self, token_refresh_service, tool_service):
        """Test successful agent tool update."""
        agent_tool_id = uuid4()
        sensitive_config = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_at": 1234567890.0,
        }
        tool_name = "Test Tool"

        tool_service.update_agent_tool = AsyncMock(return_value=(None, None))

        await token_refresh_service._update_agent_tool(
            agent_tool_id, sensitive_config, tool_name
        )

        tool_service.update_agent_tool.assert_called_once()
        call_args = tool_service.update_agent_tool.call_args
        assert call_args[1]["agent_tool_id"] == agent_tool_id
        assert call_args[1]["update_data"].sensitive_config == sensitive_config
        assert call_args[1]["update_data"].last_refreshed_at is not None

    async def test_update_agent_tool_failure(self, token_refresh_service, tool_service):
        """Test agent tool update failure."""
        agent_tool_id = uuid4()
        sensitive_config = {"access_token": "new_token"}
        tool_name = "Test Tool"

        tool_service.update_agent_tool = AsyncMock(return_value=(None, "Update failed"))

        await token_refresh_service._update_agent_tool(
            agent_tool_id, sensitive_config, tool_name
        )

        tool_service.update_agent_tool.assert_called_once()

    async def test_get_tools_requiring_auth_success(
        self, token_refresh_service, tool_service
    ):
        """Test successful retrieval of tools requiring auth."""
        mock_tools = [MagicMock(spec=AgentTool), MagicMock(spec=AgentTool)]
        tool_service.get_all_agent_tools_with_auth = AsyncMock(
            return_value=(mock_tools, None)
        )

        result = await token_refresh_service._get_tools_requiring_auth()
        assert result == mock_tools

        tool_service.get_all_agent_tools_with_auth.assert_called_once()

    async def test_get_tools_requiring_auth_failure(
        self, token_refresh_service, tool_service
    ):
        """Test retrieval of tools requiring auth failure."""
        tool_service.get_all_agent_tools_with_auth = AsyncMock(
            return_value=(None, "Database error")
        )

        result = await token_refresh_service._get_tools_requiring_auth()
        assert result == []
