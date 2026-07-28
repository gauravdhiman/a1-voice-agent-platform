"""
Tests for shared Tool Service.
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from shared.voice_agents.tool_service import ToolService, validate_token_status
from shared.voice_agents.tool_models import (
    PlatformTool,
    PlatformToolCreate,
    ToolSource,
    AgentToolCreate,
    AgentToolUpdate,
    AuthStatus
)


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

    async def test_validate_token_status_api_key_authenticated(self, tool_service):
        """Test token status validation for API key auth."""
        from shared.common.security import decrypt_data
        from unittest.mock import patch

        sensitive_config = {
            "api_key": "test_api_key_12345"
        }

        # Patch decrypt_data to return to sensitive_config
        with patch('shared.voice_agents.tool_service.decrypt_data', return_value=sensitive_config):
            encrypted_config = "encrypted_config"
            status = validate_token_status(encrypted_config, auth_type="api_key")

        assert status == AuthStatus.AUTHENTICATED

    async def test_validate_token_status_api_key_not_authenticated(self, tool_service):
        """Test token status validation for missing API key."""
        from shared.common.security import decrypt_data
        from unittest.mock import patch

        sensitive_config = {
            "other_field": "value"
        }

        # Patch decrypt_data to return to sensitive_config
        with patch('shared.voice_agents.tool_service.decrypt_data', return_value=sensitive_config):
            encrypted_config = "encrypted_config"
            status = validate_token_status(encrypted_config, auth_type="api_key")

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


class TestPlatformToolPublishLifecycle:
    """Platform-admin authoring + publish lifecycle (RFC §6.6).

    Custom MCP servers are platform-published = GLOBAL. The listing filters by
    ``is_published`` (org users see published-only; platform admins see drafts
    via ``include_drafts``). Server-level secret headers are a ``{{KEY}}``
    template encrypted at rest. The org-scoped custom tier is retired.
    """

    def _row(self, **over) -> dict:
        base = {
            "id": str(uuid4()),
            "name": "custom-mcp",
            "description": "A custom remote MCP server",
            "config_schema": None,
            "auth_type": None,
            "requires_auth": False,
            "auth_config": None,
            "tool_functions_schema": None,
            "tool_source": "mcp",
            "mcp_server_url": "https://example.com/mcp",
            "mcp_server_headers": None,
            "mcp_server_name": "custom",
            "mcp_server_secret_headers": None,
            "organization_id": None,
            "is_published": True,  # backfilled / published by default
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        base.update(over)
        return base

    async def test_get_platform_tools_filters_to_published_by_default(
        self, tool_service, mock_supabase_client
    ):
        """Default listing (org users) filters to is_published=True."""
        mock_response = MagicMock()
        mock_response.data = [self._row()]
        mock_supabase_client.table.return_value.execute.return_value = mock_response

        tools, error = await tool_service.get_platform_tools(only_active=False)

        assert error is None
        eq_mock = mock_supabase_client.table.return_value.eq
        # is_published=True filter was applied.
        publish_calls = [c for c in eq_mock.call_args_list if c.args == ("is_published", True)]
        assert len(publish_calls) == 1

    async def test_get_platform_tools_include_drafts_skips_published_filter(
        self, tool_service, mock_supabase_client
    ):
        """include_drafts=True (platform admin / internal) skips the
        is_published filter so drafts are returned too."""
        mock_response = MagicMock()
        mock_response.data = [self._row(), self._row(is_published=False, name="draft")]
        mock_supabase_client.table.return_value.execute.return_value = mock_response

        tools, error = await tool_service.get_platform_tools(
            only_active=False, include_drafts=True
        )

        assert error is None
        assert len(tools) == 2
        eq_mock = mock_supabase_client.table.return_value.eq
        publish_calls = [c for c in eq_mock.call_args_list if c.args == ("is_published", True)]
        assert publish_calls == []  # no is_published filter applied

    async def test_get_platform_tools_only_active_adds_is_active_filter(
        self, tool_service, mock_supabase_client
    ):
        """only_active=True adds is_active=True alongside is_published=True."""
        mock_response = MagicMock()
        mock_response.data = [self._row()]
        mock_supabase_client.table.return_value.execute.return_value = mock_response

        await tool_service.get_platform_tools(only_active=True)

        eq_mock = mock_supabase_client.table.return_value.eq
        active_calls = [c for c in eq_mock.call_args_list if c.args == ("is_active", True)]
        publish_calls = [c for c in eq_mock.call_args_list if c.args == ("is_published", True)]
        assert len(active_calls) == 1
        assert len(publish_calls) == 1

    async def test_upsert_encrypts_secret_headers_and_strips_from_response(
        self, tool_service, mock_supabase_client
    ):
        """Plaintext mcp_secret_headers_input must be encrypted before persist
        and the returned model must NOT expose the encrypted blob or plaintext."""
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
            mcp_server_name="custom",
            mcp_secret_headers_input={"X-Api-Key": "secret-value"},
        )

        mock_check = MagicMock()
        mock_check.data = []  # not existing
        mock_insert = MagicMock()
        mock_insert.data = [self._row(mcp_server_secret_headers="encrypted-blob")]
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]

        with patch(
            "shared.voice_agents.tool_service.encrypt_data",
            return_value="encrypted-blob",
        ) as mock_encrypt:
            result, error = await tool_service.upsert_platform_tool(tool_data)

        assert error is None
        assert result is not None
        # Plaintext input was encrypted.
        mock_encrypt.assert_called_once_with({"X-Api-Key": "secret-value"})
        # Encrypted blob was persisted.
        insert_call = mock_supabase_client.table.return_value.insert.call_args
        inserted = insert_call[0][0]
        assert inserted["mcp_server_secret_headers"] == "encrypted-blob"
        assert "mcp_secret_headers_input" not in inserted
        # Response exposes only the configured flag, never the blob.
        assert result.mcp_server_secret_headers is None
        assert result.mcp_secret_headers_configured is True

    async def test_upsert_no_secret_headers_sets_flag_false(
        self, tool_service, mock_supabase_client
    ):
        tool_data = PlatformToolCreate(
            name="no-secret-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
        )
        mock_check = MagicMock()
        mock_check.data = []
        mock_insert = MagicMock()
        mock_insert.data = [self._row(name="no-secret-mcp", mcp_server_secret_headers=None)]
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]

        result, error = await tool_service.upsert_platform_tool(tool_data)

        assert error is None
        assert result.mcp_secret_headers_configured is False
        assert result.mcp_server_secret_headers is None

    async def test_upsert_mcp_forces_global_org_even_when_org_supplied(
        self, tool_service, mock_supabase_client
    ):
        """MCP rows are platform-published = GLOBAL: organization_id is forced
        off even if a payload supplies one (the org-scoped custom tier is
        retired). The persisted payload must also be JSON-serializable
        (``mode="json"``) so postgrest can encode it.
        """
        import json

        org_id = uuid4()
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
            mcp_server_name="custom",
            organization_id=org_id,  # supplied, but must be dropped for MCP rows
        )
        mock_check = MagicMock()
        mock_check.data = []
        mock_insert = MagicMock()
        mock_insert.data = [self._row(name="custom-mcp")]
        mock_supabase_client.table.return_value.execute.side_effect = [
            mock_check,
            mock_insert,
        ]

        result, error = await tool_service.upsert_platform_tool(tool_data)

        assert error is None
        assert result is not None
        insert_call = mock_supabase_client.table.return_value.insert.call_args
        inserted = insert_call[0][0]
        # organization_id must be absent — MCP rows are forced global.
        assert "organization_id" not in inserted
        # The whole payload must round-trip through json.dumps (what postgrest does).
        json.dumps(inserted)

    async def test_get_platform_tools_strips_secret_headers_from_rows(
        self, tool_service, mock_supabase_client
    ):
        """Rows loaded with an encrypted blob must surface only the flag."""
        mock_response = MagicMock()
        mock_response.data = [
            self._row(mcp_server_secret_headers="encrypted-blob"),
            self._row(name="no-secret", mcp_server_secret_headers=None),
        ]
        mock_supabase_client.table.return_value.execute.return_value = mock_response

        tools, error = await tool_service.get_platform_tools(only_active=False)

        assert error is None
        secret_tool = next(t for t in tools if t.name == "custom-mcp")
        plain_tool = next(t for t in tools if t.name == "no-secret")
        assert secret_tool.mcp_server_secret_headers is None
        assert secret_tool.mcp_secret_headers_configured is True
        assert plain_tool.mcp_secret_headers_configured is False

    async def test_publish_platform_tool_flips_is_published(
        self, tool_service, mock_supabase_client
    ):
        """publish_platform_tool sets is_published=True on the row by id."""
        tool_id = uuid4()
        mock_update = MagicMock()
        mock_update.data = [self._row(id=str(tool_id), is_published=True)]
        mock_supabase_client.table.return_value.execute.return_value = mock_update

        result, error = await tool_service.publish_platform_tool(tool_id, True)

        assert error is None
        assert result is not None
        assert result.is_published is True
        update_call = mock_supabase_client.table.return_value.update.call_args
        assert update_call.args[0] == {"is_published": True}
        eq_call = mock_supabase_client.table.return_value.eq.call_args
        assert eq_call.args == ("id", str(tool_id))

    async def test_unpublish_flips_is_published_false(self, tool_service, mock_supabase_client):
        tool_id = uuid4()
        mock_update = MagicMock()
        mock_update.data = [self._row(id=str(tool_id), is_published=False)]
        mock_supabase_client.table.return_value.execute.return_value = mock_update

        result, error = await tool_service.publish_platform_tool(tool_id, False)

        assert error is None
        assert result.is_published is False

    async def test_publish_unknown_tool_returns_not_found(
        self, tool_service, mock_supabase_client
    ):
        """Publishing a non-existent id returns (None, 'not found')."""
        mock_update = MagicMock()
        mock_update.data = []
        mock_supabase_client.table.return_value.execute.return_value = mock_update

        result, error = await tool_service.publish_platform_tool(uuid4(), True)

        assert result is None
        assert error == "Platform tool not found"

    async def test_delete_platform_tool_deletes_by_id(
        self, tool_service, mock_supabase_client
    ):
        tool_id = uuid4()
        mock_delete = MagicMock()
        mock_delete.data = [{"id": str(tool_id)}]
        mock_supabase_client.table.return_value.execute.return_value = mock_delete

        result, error = await tool_service.delete_platform_tool(tool_id)

        assert error is None
        assert result is True
        eq_call = mock_supabase_client.table.return_value.eq.call_args
        assert eq_call.args == ("id", str(tool_id))

    async def test_update_platform_tool_encrypts_and_forces_global(
        self, tool_service, mock_supabase_client
    ):
        """update_platform_tool (PUT by id) mirrors upsert: encrypts secret
        headers and forces organization_id off for MCP rows."""
        tool_id = uuid4()
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
            mcp_server_name="custom",
            organization_id=uuid4(),  # must be dropped
            mcp_secret_headers_input={"Authorization": "Bearer {{KEY}}"},
        )
        mock_update = MagicMock()
        mock_update.data = [self._row(id=str(tool_id), mcp_server_secret_headers="enc")]
        mock_supabase_client.table.return_value.execute.return_value = mock_update

        with patch(
            "shared.voice_agents.tool_service.encrypt_data", return_value="enc"
        ) as mock_encrypt:
            result, error = await tool_service.update_platform_tool(tool_id, tool_data)

        assert error is None
        assert result is not None
        mock_encrypt.assert_called_once_with({"Authorization": "Bearer {{KEY}}"})
        update_call = mock_supabase_client.table.return_value.update.call_args
        updated = update_call.args[0]
        assert updated["mcp_server_secret_headers"] == "enc"
        assert "organization_id" not in updated
        eq_call = mock_supabase_client.table.return_value.eq.call_args
        assert eq_call.args == ("id", str(tool_id))
