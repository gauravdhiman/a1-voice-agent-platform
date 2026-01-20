"""
Tests for RBAC user roles service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.rbac.user_roles.models import UserRole, UserRoleCreate, UserRoleUpdate, UserWithRoles
from src.rbac.user_roles.service import UserRoleService


@pytest.fixture
def user_role_service(mock_supabase_client):
    """UserRoleService with mocked Supabase."""
    with patch('src.rbac.user_roles.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True

        service = UserRoleService()
        service.supabase_config = mock_config
        yield service


@pytest.mark.asyncio
class TestUserRoleService:
    """Test cases for UserRoleService."""

    async def test_assign_role_to_user_success(self, user_role_service):
        """Test successful role assignment to user."""
        user_id = uuid4()
        role_id = uuid4()
        org_id = uuid4()
        ur_id = uuid4()

        test_data = {
            "id": str(ur_id),
            "user_id": str(user_id),
            "role_id": str(role_id),
            "organization_id": str(org_id),
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        user_role_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        user_role_data = UserRoleCreate(
            user_id=user_id,
            role_id=role_id,
            organization_id=org_id
        )
        user_role, error = await user_role_service.assign_role_to_user(user_role_data)

        assert error is None
        assert user_role is not None
        assert user_role.user_id == user_id
        assert user_role.role_id == role_id
        assert user_role.organization_id == org_id

    async def test_assign_role_to_user_database_error(self, user_role_service):
        """Test role assignment with database error."""
        mock_response = MagicMock()
        mock_response.data = []
        user_role_service.supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        user_role_data = UserRoleCreate(
            user_id=uuid4(),
            role_id=uuid4(),
            organization_id=uuid4()
        )
        user_role, error = await user_role_service.assign_role_to_user(user_role_data)

        assert user_role is None
        assert error == "Failed to assign role to user"

    async def test_assign_role_to_user_exception(self, user_role_service):
        """Test role assignment with exception."""
        user_role_service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")

        user_role_data = UserRoleCreate(
            user_id=uuid4(),
            role_id=uuid4(),
            organization_id=uuid4()
        )
        user_role, error = await user_role_service.assign_role_to_user(user_role_data)

        assert user_role is None
        assert error == "Database error"

    async def test_update_user_role_success(self, user_role_service):
        """Test successful user role update."""
        ur_id = uuid4()
        new_role_id = uuid4()
        new_org_id = uuid4()

        test_data = {
            "id": str(ur_id),
            "user_id": str(uuid4()),
            "role_id": str(new_role_id),
            "organization_id": str(new_org_id),
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        user_role_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        update_data = UserRoleUpdate(
            role_id=new_role_id,
            organization_id=new_org_id
        )
        user_role, error = await user_role_service.update_user_role(ur_id, update_data)

        assert error is None
        assert user_role is not None
        assert user_role.id == ur_id
        assert user_role.role_id == new_role_id
        assert user_role.organization_id == new_org_id

    async def test_update_user_role_not_found(self, user_role_service):
        """Test user role update when not found."""
        mock_response = MagicMock()
        mock_response.data = []
        user_role_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        update_data = UserRoleUpdate(role_id=uuid4())
        user_role, error = await user_role_service.update_user_role(uuid4(), update_data)

        assert user_role is None
        assert error == "User role assignment not found"

    async def test_remove_role_from_user_success(self, user_role_service):
        """Test successful role removal from user."""
        mock_response = MagicMock()
        mock_response.data = [{"id": str(uuid4())}]
        user_role_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        success, error = await user_role_service.remove_role_from_user(uuid4())

        assert error is None
        assert success is True

    async def test_remove_role_from_user_not_found(self, user_role_service):
        """Test role removal when assignment not found."""
        mock_response = MagicMock()
        mock_response.data = []
        user_role_service.supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        success, error = await user_role_service.remove_role_from_user(uuid4())

        assert success is False
        assert error == "User role assignment not found"

    async def test_get_user_role_by_id_success(self, user_role_service):
        """Test successful user role retrieval by ID."""
        ur_id = uuid4()
        test_data = {
            "id": str(ur_id),
            "user_id": str(uuid4()),
            "role_id": str(uuid4()),
            "organization_id": str(uuid4()),
            "created_at": "2024-01-01T00:00:00.000Z",
            "updated_at": "2024-01-01T00:00:00.000Z",
        }
        mock_response = MagicMock()
        mock_response.data = [test_data]
        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        user_role, error = await user_role_service.get_user_role_by_id(ur_id)

        assert error is None
        assert user_role is not None
        assert user_role.id == ur_id

    async def test_get_user_role_by_id_not_found(self, user_role_service):
        """Test user role retrieval by ID when not found."""
        mock_response = MagicMock()
        mock_response.data = []
        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        user_role, error = await user_role_service.get_user_role_by_id(uuid4())

        assert user_role is None
        assert error == "User role assignment not found"

    async def test_get_user_roles_success(self, user_role_service):
        """Test successful retrieval of user roles."""
        user_id = uuid4()
        role_data = [
            {
                "roles": {
                    "id": str(uuid4()),
                    "name": "Admin",
                    "description": "Administrator role",
                    "is_system_role": False,
                    "created_at": "2024-01-01T00:00:00.000Z",
                    "updated_at": "2024-01-01T00:00:00.000Z",
                }
            },
            {
                "roles": {
                    "id": str(uuid4()),
                    "name": "User",
                    "description": "Regular user role",
                    "is_system_role": False,
                    "created_at": "2024-01-01T00:00:00.000Z",
                    "updated_at": "2024-01-01T00:00:00.000Z",
                }
            }
        ]
        mock_response = MagicMock()
        mock_response.data = role_data
        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.order.return_value.execute.return_value = mock_response

        roles, error = await user_role_service.get_user_roles(user_id)

        assert error is None
        assert len(roles) == 2
        assert roles[0].name == "Admin"
        assert roles[1].name == "User"

    async def test_get_user_roles_empty(self, user_role_service):
        """Test retrieval of user roles when none exist."""
        mock_response = MagicMock()
        mock_response.data = []
        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        user_roles, error = await user_role_service.get_user_roles(uuid4())

        assert error is None
        assert user_roles == []

    async def test_user_has_permission_success(self, user_role_service):
        """Test successful permission check for user."""
        user_id = uuid4()
        permission_name = "read:users"
        perm_id = uuid4()
        role_id = uuid4()

        # Mock permission lookup
        mock_perm_response = MagicMock()
        mock_perm_response.data = [{"id": str(perm_id), "name": permission_name}]

        # Mock role lookup (get_user_roles call)
        from src.rbac.roles.models import Role
        mock_role = Role(
            id=role_id,
            name="Admin",
            description="Admin role",
            is_system_role=False,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

        # Mock role_permissions check
        mock_rp_response = MagicMock()
        mock_rp_response.data = [{"role_id": str(role_id), "permission_id": str(perm_id)}]

        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_perm_response,  # Permission lookup
            MagicMock(data=[{"roles": mock_role.model_dump()}]),  # get_user_roles
            mock_rp_response  # role_permissions check
        ]

        has_permission, error = await user_role_service.user_has_permission(user_id, permission_name)

        assert error is None
        assert has_permission is True

    async def test_user_has_permission_false(self, user_role_service):
        """Test permission check when user doesn't have permission."""
        user_id = uuid4()
        permission_name = "write:users"
        perm_id = uuid4()

        # Mock permission lookup and permission check
        mock_perm_response = MagicMock()
        mock_perm_response.data = [{"id": str(perm_id), "name": permission_name}]
        mock_count_response = MagicMock()
        mock_count_response.data = [{"count": 0}]
        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_perm_response,  # First call gets permission
            mock_count_response  # Second call checks if user has permission
        ]

        has_permission, error = await user_role_service.user_has_permission(user_id, permission_name)

        assert error is None
        assert has_permission is False

    async def test_user_has_role_success(self, user_role_service):
        """Test successful role check for user."""
        user_id = uuid4()
        role_name = "Admin"
        role_id = uuid4()

        # Mock role lookup
        mock_role_response = MagicMock()
        mock_role_response.data = [{"id": str(role_id), "name": role_name}]

        # Mock user_roles check
        mock_user_role_response = MagicMock()
        mock_user_role_response.data = [{"user_id": str(user_id), "role_id": str(role_id)}]

        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_role_response,  # Role lookup
        ]
        user_role_service.supabase.table.return_value.select.return_value.match.return_value.is_.return_value.execute.return_value = mock_user_role_response

        has_role, error = await user_role_service.user_has_role(user_id, role_name)

        assert error is None
        assert has_role is True

    async def test_user_has_role_false(self, user_role_service):
        """Test role check when user doesn't have role."""
        user_id = uuid4()
        role_name = "User"
        role_id = uuid4()

        # Mock role lookup and role check
        mock_role_response = MagicMock()
        mock_role_response.data = [{"id": str(role_id), "name": role_name}]
        mock_count_response = MagicMock()
        mock_count_response.data = [{"count": 0}]
        user_role_service.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_role_response,  # First call gets role
            mock_count_response  # Second call checks if user has role
        ]

        has_role, error = await user_role_service.user_has_role(user_id, role_name)

        assert error is None
        assert has_role is False