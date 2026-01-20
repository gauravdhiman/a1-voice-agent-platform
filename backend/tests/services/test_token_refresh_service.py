"""
Tests for token refresh service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tool_models import AgentTool, PlatformTool
from src.services.token_refresh_service import TokenRefreshService


@pytest.fixture
def tool_service():
    """Mock ToolService."""
    return MagicMock(spec=ToolService)


@pytest.fixture
def token_refresh_service(tool_service):
    """TokenRefreshService with mocked ToolService."""
    return TokenRefreshService(tool_service)


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
        "token_url": "https://oauth.example.com/token"
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

    async def test_check_and_refresh_token_no_sensitive_config(self, token_refresh_service, sample_agent_tool):
        """Test token check with no sensitive config."""
        sample_agent_tool.sensitive_config = None

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_no_expires_at(self, token_refresh_service, sample_agent_tool):
        """Test token check with no expires_at."""
        sample_agent_tool.sensitive_config = {"access_token": "test"}

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_expired(self, token_refresh_service, sample_agent_tool):
        """Test token check with already expired token."""
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(minutes=30)
        sample_agent_tool.sensitive_config["expires_at"] = expired_time.timestamp()

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_valid_long_time(self, token_refresh_service, sample_agent_tool):
        """Test token check with token valid for long time."""
        now = datetime.now(timezone.utc)
        far_future = now + timedelta(hours=2)  # Valid for 2 hours
        sample_agent_tool.sensitive_config["expires_at"] = far_future.timestamp()

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_no_refresh_token(self, token_refresh_service, sample_agent_tool):
        """Test token check with no refresh token."""
        sample_agent_tool.sensitive_config["refresh_token"] = None

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_no_auth_config(self, token_refresh_service, sample_agent_tool):
        """Test token check with no auth config."""
        sample_agent_tool.tool.auth_config = None

        result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
        assert result is False

    async def test_check_and_refresh_token_success(self, token_refresh_service, sample_agent_tool):
        """Test successful token refresh."""
        # Mock the OAuth manager
        with patch('src.services.token_refresh_service.get_oauth_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.extract_oauth_config.return_value = ("google", "https://oauth.example.com/token")
            mock_get_manager.return_value = mock_manager

            # Mock the token refresh
            new_tokens = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600
            }

            with patch.object(token_refresh_service, '_refresh_oauth_token', new_callable=AsyncMock) as mock_refresh:
                mock_refresh.return_value = new_tokens

                with patch.object(token_refresh_service, '_update_agent_tool', new_callable=AsyncMock) as mock_update:
                    result = await token_refresh_service._check_and_refresh_token(sample_agent_tool)
                    assert result is True

                    # Verify refresh was called
                    mock_refresh.assert_called_once()
                    # Verify update was called
                    mock_update.assert_called_once()

    async def test_refresh_oauth_token_success(self, token_refresh_service):
        """Test successful OAuth token refresh."""
        token_url = "https://oauth.example.com/token"
        oauth_data = {
            "grant_type": "refresh_token",
            "refresh_token": "test_refresh_token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }

        expected_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await token_refresh_service._refresh_oauth_token(token_url, oauth_data)
            assert result == expected_response

            mock_client.post.assert_called_once_with(token_url, data=oauth_data)

    async def test_refresh_oauth_token_failure(self, token_refresh_service):
        """Test OAuth token refresh failure."""
        token_url = "https://oauth.example.com/token"
        oauth_data = {"grant_type": "refresh_token"}

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await token_refresh_service._refresh_oauth_token(token_url, oauth_data)
            assert result is None

    async def test_update_agent_tool_success(self, token_refresh_service, tool_service):
        """Test successful agent tool update."""
        agent_tool_id = uuid4()
        sensitive_config = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_at": 1234567890.0
        }
        tool_name = "Test Tool"

        tool_service.update_agent_tool = AsyncMock(return_value=(None, None))

        await token_refresh_service._update_agent_tool(agent_tool_id, sensitive_config, tool_name)

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

        await token_refresh_service._update_agent_tool(agent_tool_id, sensitive_config, tool_name)

        tool_service.update_agent_tool.assert_called_once()

    async def test_get_tools_requiring_auth_success(self, token_refresh_service, tool_service):
        """Test successful retrieval of tools requiring auth."""
        mock_tools = [MagicMock(spec=AgentTool), MagicMock(spec=AgentTool)]
        tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=(mock_tools, None))

        result = await token_refresh_service._get_tools_requiring_auth()
        assert result == mock_tools

        tool_service.get_all_agent_tools_with_auth.assert_called_once()

    async def test_get_tools_requiring_auth_failure(self, token_refresh_service, tool_service):
        """Test retrieval of tools requiring auth failure."""
        tool_service.get_all_agent_tools_with_auth = AsyncMock(return_value=(None, "Database error"))

        result = await token_refresh_service._get_tools_requiring_auth()
        assert result == []