"""
Tests for RBAC roles service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.rbac.roles.models import Role, RoleCreate, RoleUpdate, RoleWithPermissions
from src.rbac.roles.service import RoleService


@pytest.fixture
def role_service(mock_supabase_client):
    """RoleService with mocked Supabase."""
    with patch('src.rbac.roles.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True

        service = RoleService()
        service.supabase_config = mock_config
        yield service


@pytest.mark.asyncio
class TestRoleService:
    """Test cases for RoleService."""

    async def test_create_role_success(self, role_service):
        """Test successful role creation."""
        role_id = uuid4()
        test_data = {
            "id": str(role_id),
            "name": "Test Role",
            "description": "Test role description",
            "is_system_role": False,
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        role_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        role_data = RoleCreate(name="Test Role", description="Test role description")
        role, error = await role_service.create_role(role_data)

        assert error is None
        assert role is not None
        assert role.name == "Test Role"
        assert role.description == "Test role description"
        assert role.is_system_role is False
        assert role.id == role_id

    async def test_create_role_database_error(self, role_service):
        """Test role creation with database error."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        role_data = RoleCreate(name="Test Role")
        role, error = await role_service.create_role(role_data)

        assert role is None
        assert error == "Failed to create role"

    async def test_create_role_exception(self, role_service):
        """Test role creation with exception."""
        role_service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")

        role_data = RoleCreate(name="Test Role")
        role, error = await role_service.create_role(role_data)

        assert role is None
        assert error == "Database error"

    async def test_get_role_by_id_success(self, role_service):
        """Test successful role retrieval by ID."""
        role_id = uuid4()
        test_data = {
            "id": str(role_id),
            "name": "Test Role",
            "description": "Test role description",
            "is_system_role": False,
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        role, error = await role_service.get_role_by_id(role_id)

        assert error is None
        assert role is not None
        assert role.id == role_id
        assert role.name == "Test Role"

    async def test_get_role_by_id_not_found(self, role_service):
        """Test role retrieval by ID when not found."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        role, error = await role_service.get_role_by_id(uuid4())

        assert role is None
        assert error == "Role not found"

    async def test_get_role_by_name_success(self, role_service):
        """Test successful role retrieval by name."""
        role_id = uuid4()
        test_data = {
            "id": str(role_id),
            "name": "Test Role",
            "description": "Test role description",
            "is_system_role": False,
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        role, error = await role_service.get_role_by_name("Test Role")

        assert error is None
        assert role is not None
        assert role.name == "Test Role"
        assert role.id == role_id

    async def test_get_role_by_name_not_found(self, role_service):
        """Test role retrieval by name when not found."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        role, error = await role_service.get_role_by_name("Nonexistent Role")

        assert role is None
        assert error == "Role not found"

    async def test_get_all_roles_success(self, role_service):
        """Test successful retrieval of all roles."""
        role_id1 = uuid4()
        role_id2 = uuid4()
        test_data = [
            {
                "id": str(role_id1),
                "name": "Role 1",
                "description": "First role",
                "is_system_role": False,
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z",
            },
            {
                "id": str(role_id2),
                "name": "Role 2",
                "description": "Second role",
                "is_system_role": True,
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z",
            }
        ]
        mock_response = MagicMock()
        mock_response.data = test_data
        role_service.supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        roles, error = await role_service.get_all_roles()

        assert error is None
        assert len(roles) == 2
        assert roles[0].name == "Role 1"
        assert roles[1].name == "Role 2"
        assert roles[0].is_system_role is False
        assert roles[1].is_system_role is True

    async def test_get_all_roles_empty(self, role_service):
        """Test retrieval of all roles when none exist."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        roles, error = await role_service.get_all_roles()

        assert error is None
        assert roles == []

    async def test_update_role_success(self, role_service):
        """Test successful role update."""
        role_id = uuid4()
        test_data = {
            "id": str(role_id),
            "name": "Updated Role",
            "description": "Updated description",
            "is_system_role": False,
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        role_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        role_update = RoleUpdate(
            name="Updated Role",
            description="Updated description"
        )
        role, error = await role_service.update_role(role_id, role_update)

        assert error is None
        assert role is not None
        assert role.id == role_id
        assert role.name == "Updated Role"
        assert role.description == "Updated description"

    async def test_update_role_not_found(self, role_service):
        """Test role update when role not found."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        role_update = RoleUpdate(name="Updated Role")
        role, error = await role_service.update_role(uuid4(), role_update)

        assert role is None
        assert error == "Role not found or update failed"

    async def test_delete_role_success(self, role_service):
        """Test successful role deletion."""
        mock_response = MagicMock()
        mock_response.data = [{"id": str(uuid4())}]
        role_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        success, error = await role_service.delete_role(uuid4())

        assert error is None
        assert success is True

    async def test_delete_role_not_found(self, role_service):
        """Test role deletion when role not found."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        success, error = await role_service.delete_role(uuid4())

        assert success is False
        assert error == "Role not found"

    async def test_get_role_with_permissions_success(self, role_service):
        """Test successful role retrieval with permissions."""
        role_id = uuid4()
        permission_id = uuid4()

        role_data = {
            "id": str(role_id),
            "name": "Test Role",
            "description": "Test role description",
            "is_system_role": False,
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        permission_data = {
            "id": str(permission_id),
            "name": "read:users",
            "resource": "users",
            "action": "read",
            "description": "Read users",
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }

        # Mock role query
        mock_role_response = MagicMock()
        mock_role_response.data = [role_data]
        role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_role_response

        # Mock permission service call
        from src.rbac.permissions.models import Permission
        mock_permission = Permission(**permission_data)

        with patch('src.rbac.roles.service.permission_service') as mock_perm_service:
            mock_perm_service.get_permissions_for_role = AsyncMock(return_value=([mock_permission], None))

            role_with_permissions, error = await role_service.get_role_with_permissions(role_id)

        assert error is None
        assert role_with_permissions is not None
        assert role_with_permissions.name == "Test Role"
        assert len(role_with_permissions.permissions) == 1
        assert role_with_permissions.permissions[0].name == "read:users"

    async def test_get_role_with_permissions_role_not_found(self, role_service):
        """Test role with permissions retrieval when role not found."""
        mock_response = MagicMock()
        mock_response.data = []
        role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        role_with_permissions, error = await role_service.get_role_with_permissions(uuid4())

        assert role_with_permissions is None
        assert error == "Role not found"