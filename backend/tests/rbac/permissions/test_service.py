"""
Tests for RBAC permissions service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.rbac.permissions.models import Permission, PermissionCreate, PermissionUpdate, RolePermission
from src.rbac.permissions.service import PermissionService


@pytest.fixture
def permission_service(mock_supabase_client):
    """PermissionService with mocked Supabase."""
    with patch('src.rbac.permissions.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True

        service = PermissionService()
        service.supabase_config = mock_config
        yield service


@pytest.mark.asyncio
class TestPermissionService:
    """Test cases for PermissionService."""

    async def test_create_permission_success(self, permission_service):
        """Test successful permission creation."""
        perm_id = uuid4()
        test_data = {
            "id": str(perm_id),
            "name": "read:users",
            "description": "Read users permission",
            "resource": "users",
            "action": "read",
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        permission_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        perm_data = PermissionCreate(
            name="read:users",
            description="Read users permission",
            resource="users",
            action="read"
        )
        permission, error = await permission_service.create_permission(perm_data)

        assert error is None
        assert permission is not None
        assert permission.name == "read:users"
        assert permission.description == "Read users permission"
        assert permission.resource == "users"
        assert permission.action == "read"
        assert permission.id == perm_id

    async def test_create_permission_database_error(self, permission_service):
        """Test permission creation with database error."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        perm_data = PermissionCreate(name="read:users", resource="users", action="read")
        permission, error = await permission_service.create_permission(perm_data)

        assert permission is None
        assert error == "Failed to create permission"

    async def test_create_permission_exception(self, permission_service):
        """Test permission creation with exception."""
        permission_service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")

        perm_data = PermissionCreate(name="read:users", resource="users", action="read")
        permission, error = await permission_service.create_permission(perm_data)

        assert permission is None
        assert error == "Database error"

    async def test_get_permission_by_id_success(self, permission_service):
        """Test successful permission retrieval by ID."""
        perm_id = uuid4()
        test_data = {
            "id": str(perm_id),
            "name": "read:users",
            "description": "Read users permission",
            "resource": "users",
            "action": "read",
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        permission_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        permission, error = await permission_service.get_permission_by_id(perm_id)

        assert error is None
        assert permission is not None
        assert permission.id == perm_id
        assert permission.name == "read:users"

    async def test_get_permission_by_id_not_found(self, permission_service):
        """Test permission retrieval by ID when not found."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        permission, error = await permission_service.get_permission_by_id(uuid4())

        assert permission is None
        assert error == "Permission not found"

    async def test_get_permission_by_name_success(self, permission_service):
        """Test successful permission retrieval by name."""
        perm_id = uuid4()
        test_data = {
            "id": str(perm_id),
            "name": "read:users",
            "description": "Read users permission",
            "resource": "users",
            "action": "read",
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        permission_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        permission, error = await permission_service.get_permission_by_name("read:users")

        assert error is None
        assert permission is not None
        assert permission.name == "read:users"
        assert permission.id == perm_id

    async def test_get_permission_by_name_not_found(self, permission_service):
        """Test permission retrieval by name when not found."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        permission, error = await permission_service.get_permission_by_name("nonexistent:perm")

        assert permission is None
        assert error == "Permission not found"

    async def test_get_all_permissions_success(self, permission_service):
        """Test successful retrieval of all permissions."""
        perm_id1 = uuid4()
        perm_id2 = uuid4()
        test_data = [
            {
                "id": str(perm_id1),
                "name": "read:users",
                "description": "Read users",
                "resource": "users",
                "action": "read",
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z",
            },
            {
                "id": str(perm_id2),
                "name": "write:users",
                "description": "Write users",
                "resource": "users",
                "action": "write",
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z",
            }
        ]
        mock_response = MagicMock()
        mock_response.data = test_data
        permission_service.supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        permissions, error = await permission_service.get_all_permissions()

        assert error is None
        assert len(permissions) == 2
        assert permissions[0].name == "read:users"
        assert permissions[1].name == "write:users"
        assert permissions[0].resource == "users"
        assert permissions[1].action == "write"

    async def test_get_all_permissions_empty(self, permission_service):
        """Test retrieval of all permissions when none exist."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        permissions, error = await permission_service.get_all_permissions()

        assert error is None
        assert permissions == []

    async def test_update_permission_success(self, permission_service):
        """Test successful permission update."""
        perm_id = uuid4()
        test_data = {
            "id": str(perm_id),
            "name": "write:users",
            "description": "Updated description",
            "resource": "users",
            "action": "write",
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        permission_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        perm_update = PermissionUpdate(
            name="write:users",
            description="Updated description",
            action="write"
        )
        permission, error = await permission_service.update_permission(perm_id, perm_update)

        assert error is None
        assert permission is not None
        assert permission.id == perm_id
        assert permission.name == "write:users"
        assert permission.description == "Updated description"
        assert permission.action == "write"

    async def test_update_permission_not_found(self, permission_service):
        """Test permission update when permission not found."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        perm_update = PermissionUpdate(name="write:users")
        permission, error = await permission_service.update_permission(uuid4(), perm_update)

        assert permission is None
        assert error == "Permission not found or update failed"

    async def test_delete_permission_success(self, permission_service):
        """Test successful permission deletion."""
        mock_response = MagicMock()
        mock_response.data = [{"id": str(uuid4())}]
        permission_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        success, error = await permission_service.delete_permission(uuid4())

        assert error is None
        assert success is True

    async def test_delete_permission_not_found(self, permission_service):
        """Test permission deletion when permission not found."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        success, error = await permission_service.delete_permission(uuid4())

        assert success is False
        assert error == "Permission not found"

    async def test_assign_permission_to_role_success(self, permission_service):
        """Test successful permission assignment to role."""
        role_id = uuid4()
        perm_id = uuid4()
        rp_id = uuid4()

        test_data = {
            "id": str(rp_id),
            "role_id": str(role_id),
            "permission_id": str(perm_id),
            "created_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        permission_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        role_permission, error = await permission_service.assign_permission_to_role(role_id, perm_id)

        assert error is None
        assert role_permission is not None
        assert role_permission.role_id == role_id
        assert role_permission.permission_id == perm_id

    async def test_assign_permission_to_role_already_assigned(self, permission_service):
        """Test permission assignment when already assigned."""
        permission_service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception("duplicate key value violates unique constraint")

        role_permission, error = await permission_service.assign_permission_to_role(uuid4(), uuid4())

        assert role_permission is None
        assert "duplicate key value violates unique constraint" in error

    async def test_remove_permission_from_role_success(self, permission_service):
        """Test successful permission removal from role."""
        mock_response = MagicMock()
        mock_response.data = [{"id": str(uuid4())}]
        permission_service.supabase.table.return_value.delete.return_value.match.return_value.execute.return_value = mock_response

        success, error = await permission_service.remove_permission_from_role(uuid4(), uuid4())

        assert error is None
        assert success is True

    async def test_remove_permission_from_role_not_assigned(self, permission_service):
        """Test permission removal when not assigned."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.delete.return_value.match.return_value.execute.return_value = mock_response

        success, error = await permission_service.remove_permission_from_role(uuid4(), uuid4())

        assert success is False
        assert error == "Role-permission assignment not found"

    async def test_get_permissions_for_role_success(self, permission_service):
        """Test successful retrieval of permissions for a role."""
        role_id = uuid4()
        perm_id = uuid4()

        test_data = [
            {
                "permissions": {
                    "id": str(perm_id),
                    "name": "read:users",
                    "description": "Read users",
                    "resource": "users",
                    "action": "read",
                    "created_at": "2024-01-01T00:00:00.000Z",
                    "updated_at": "2024-01-01T00:00:00.000Z",
                }
            }
        ]
        mock_response = MagicMock()
        mock_response.data = test_data
        permission_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        permissions, error = await permission_service.get_permissions_for_role(role_id)

        assert error is None
        assert len(permissions) == 1
        assert permissions[0].name == "read:users"
        assert permissions[0].resource == "users"
        assert permissions[0].action == "read"

    async def test_get_permissions_for_role_empty(self, permission_service):
        """Test retrieval of permissions for role with no permissions."""
        mock_response = MagicMock()
        mock_response.data = []
        permission_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        permissions, error = await permission_service.get_permissions_for_role(uuid4())

        assert error is None
        assert permissions == []