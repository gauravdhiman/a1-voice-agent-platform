"""
Tests for shared Tool Service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from shared.voice_agents.tool_service import ToolService, validate_token_status, get_connection_status
from shared.voice_agents.tool_models import (
    AgentTool,
    PlatformTool,
    AgentToolCreate,
    AgentToolUpdate,
    AuthStatus
)
from shared.common.security import encrypt_data


@pytest.fixture
def tool_service(mock_supabase_client):
    """ToolService with mocked Supabase."""
    from unittest.mock import patch

    with patch('shared.voice_agents.tool_service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True

        service = ToolService()
        service.supabase_config = mock_config
        yield service



@pytest.fixture
def sample_platform_tool():
    """Sample PlatformTool."""
    return PlatformTool(
        id=uuid4(),
        name="Gmail",
        description="Email service",
        config_schema={},
        auth_type="oauth2",
        requires_auth=True,
        auth_config={},
        tool_functions_schema=["read_emails", "send_email"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestToolService:
    """Test cases for ToolService."""

    async def test_validate_token_status_authenticated(self, tool_service):
        """Test token status validation for authenticated token."""
        from shared.common.security import decrypt_data
        from unittest.mock import patch

        sensitive_config = {
            "access_token": "valid_token",
            "expires_at": datetime.now(timezone.utc).timestamp() + 3600  # 1 hour from now
        }

        # Patch decrypt_data to return the sensitive_config
        with patch('shared.voice_agents.tool_service.decrypt_data', return_value=sensitive_config):
            encrypted_config = "encrypted_config"
            status = validate_token_status(encrypted_config)

        assert status == AuthStatus.AUTHENTICATED

    async def test_validate_token_status_expired(self, tool_service):
        """Test token status validation for expired token."""
        from shared.common.security import decrypt_data
        from unittest.mock import patch

        sensitive_config = {
            "access_token": "expired_token",
            "expires_at": datetime.now(timezone.utc).timestamp() - 3600  # 1 hour ago
        }

        # Patch decrypt_data to return the sensitive_config
        with patch('shared.voice_agents.tool_service.decrypt_data', return_value=sensitive_config):
            encrypted_config = "encrypted_config"
            status = validate_token_status(encrypted_config)

        assert status == AuthStatus.EXPIRED

    async def test_validate_token_status_not_authenticated(self, tool_service):
        """Test token status validation for missing token."""
        encrypted_config = None
        status = validate_token_status(encrypted_config)

        assert status == AuthStatus.NOT_AUTHENTICATED

    async def test_upsert_platform_tool_create(self, tool_service, mock_supabase_client):
        """Test creating new platform tool."""
        from shared.voice_agents.tool_models import PlatformToolCreate

        tool_id = uuid4()
        tool_data = PlatformToolCreate(
            name="Test Tool",
            description="Test description",
            auth_type="api_key",
            requires_auth=True,
            auth_config={"client_id": "test"},
            tool_functions_schema={"functions": ["test_func"]},
            is_active=True
        )

        tool_data_with_id = {
            "id": str(tool_id),
            "name": "Test Tool",
            "description": "Test description",
            "config_schema": None,
            "auth_type": "api_key",
            "requires_auth": True,
            "auth_config": {"client_id": "test"},
            "tool_functions_schema": {"functions": ["test_func"]},
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

        # Create separate execute mocks for different calls
        mock_check_response = MagicMock()
        mock_check_response.data = []

        mock_insert_response = MagicMock()
        mock_insert_response.data = [tool_data_with_id]

        # Use side_effect on execute to return different responses
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check_response,
            mock_insert_response
        ]

        result, error = await tool_service.upsert_platform_tool(tool_data)

        assert error is None
        assert result is not None
        assert result.name == "Test Tool"

    async def test_get_platform_tools_all(self, tool_service, mock_supabase_client):
        """Test getting all platform tools."""
        tool_id = uuid4()
        tools_data = [
            {
                "id": str(tool_id),
                "name": "Tool 1",
                "description": "First tool",
                "config_schema": None,
                "auth_type": "api_key",
                "requires_auth": False,
                "auth_config": {},
                "tool_functions_schema": {"functions": ["func1"]},
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]

        mock_response = MagicMock()
        mock_response.data = tools_data
        mock_supabase_client.table.return_value.execute.return_value = mock_response

        tools, error = await tool_service.get_platform_tools(only_active=False)

        assert error is None
        assert len(tools) == 1
        assert tools[0].name == "Tool 1"

    async def test_configure_agent_tool_create(self, tool_service, mock_supabase_client):
        """Test creating new agent tool configuration."""
        from unittest.mock import patch

        agent_tool_id = uuid4()
        tool_id = uuid4()

        agent_tool_data = AgentToolCreate(
            agent_id=agent_tool_id,
            tool_id=tool_id,
            unselected_functions=[],  # No functions excluded
            sensitive_config={"access_token": "token"}
        )

        # Mock responses
        mock_insert_response = MagicMock()
        mock_insert_response.data = [{
            "id": str(agent_tool_id),
            "agent_id": str(agent_tool_data.agent_id),
            "tool_id": str(agent_tool_data.tool_id),
            "unselected_functions": agent_tool_data.unselected_functions,
            "sensitive_config": "encrypted_config",
            "is_enabled": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]

        platform_tool_data = {
            "id": str(tool_id),
            "name": "Gmail",
            "description": "Email tool",
            "config_schema": None,
            "auth_type": "oauth2",
            "requires_auth": True,
            "auth_config": {},
            "tool_functions_schema": {},
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        mock_platform_response = MagicMock()
        mock_platform_response.data = [platform_tool_data]

        mock_check_response = MagicMock()
        mock_check_response.data = []

        # Set side_effect to return different responses in order
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check_response,    # Check for existing
            mock_insert_response,   # Insert agent tool
            mock_platform_response   # Get platform tool for requires_auth
        ]

        # Patch encrypt_data
        with patch('shared.voice_agents.tool_service.encrypt_data', return_value="encrypted_config"):
            result, error = await tool_service.configure_agent_tool(agent_tool_data)

        assert error is None
        assert result is not None

    async def test_get_agent_tools(self, tool_service, mock_supabase_client):
        """Test getting agent tools without sensitive config."""
        agent_id = uuid4()
        tool_id = uuid4()

        # Create a new UUID for agent_tool
        agent_tool_id = uuid4()

        # Mock response with nested structure from LEFT JOIN
        tools_data = [
            {
                "id": str(agent_tool_id),
                "agent_id": str(agent_id),
                "tool_id": str(tool_id),
                "unselected_functions": [],
                "sensitive_config": None,
                "is_enabled": True,
                "tool": {
                    "id": str(tool_id),
                    "name": "Gmail",
                    "description": "Email tool",
                    "config_schema": None,
                    "auth_type": "oauth2",
                    "requires_auth": True,
                    "auth_config": {},
                    "tool_functions_schema": {},
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]

        mock_response = MagicMock()
        mock_response.data = tools_data
        mock_supabase_client.table.return_value.execute.return_value = mock_response

        tools, error = await tool_service.get_agent_tools(agent_id)

        assert error is None
        assert len(tools) == 1
        assert tools[0].tool.name == "Gmail"
        # Note: AgentToolResponse doesn't include sensitive_config by design

    async def test_update_agent_tool(self, tool_service, mock_supabase_client):
        """Test updating agent tool."""
        agent_tool_id = uuid4()
        agent_id = uuid4()
        tool_id = uuid4()

        update_data = AgentToolUpdate(unselected_functions=["read_emails"])

        mock_response = MagicMock()
        mock_response.data = [{
            "id": str(agent_tool_id),
            "agent_id": str(agent_id),
            "tool_id": str(tool_id),
            "unselected_functions": ["read_emails"],
            "sensitive_config": None,
            "is_enabled": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]

        mock_supabase_client.table.return_value.execute.return_value = mock_response

        result, error = await tool_service.update_agent_tool(agent_tool_id, update_data)

        assert error is None
        assert result is not None

    async def test_delete_agent_tool(self, tool_service, mock_supabase_client):
        """Test deleting agent tool."""
        agent_tool_id = uuid4()

        mock_response = MagicMock()
        mock_response.data = [{"id": str(agent_tool_id)}]

        mock_supabase_client.table.return_value.execute.return_value = mock_response

        result, error = await tool_service.delete_agent_tool(agent_tool_id)

        assert error is None
        assert result is True
