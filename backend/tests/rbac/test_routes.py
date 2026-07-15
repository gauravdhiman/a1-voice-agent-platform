"""
Tests for RBAC routes — fix has_permission org-blind dead endpoints (Task #34).

Five GET endpoints in `backend/src/rbac/` use
``user_profile.has_permission("permission:read")`` (or
``has_permission("role:read")``) WITHOUT an ``organization_id``. The
``has_permission`` implementation only returns True for
``platform_admin`` in the org-blind path (see
``UserProfile.has_permission`` in ``backend/src/auth/models.py``), so
in practice these endpoints are accessible only to platform admins
— but the check is fragile and semantically wrong: the endpoints
should be platform-admin-only, not permission-gated.

This change replaces ``has_permission(...)`` with ``has_role(
"platform_admin")`` in:
  - permissions/routes.py:
      GET  /permissions/                          (L97)
      GET  /permissions/{permission_id}           (L64)
      GET  /permissions/roles/{role_id}/...       (L305)
  - roles/routes.py:
      GET  /roles/                                (L88)
      GET  /roles/{role_id}                       (L56)

Contract (each endpoint):
  - platform_admin → 200.
  - org_admin (no platform_admin) → 403.
  - regular user → 403.
  - The underlying service method is NEVER called for a 403 path.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi import HTTPException

TEST_PERMISSION_ID = UUID("00000000-0000-0000-0000-000000000010")
TEST_ROLE_ID = UUID("00000000-0000-0000-0000-000000000020")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000030")


def _make_profile(
    is_platform_admin: bool = False,
    is_org_admin: bool = False,
    has_permission_read: bool = False,
):
    """Build a UserProfile mock.

    `has_role("platform_admin")` returns True iff `is_platform_admin`.
    `has_permission(...)` returns True iff `has_permission_read` — an
    ortho flag modeling a user explicitly granted `permission:read` /
    `role:read` (e.g. via a role grant).

    The two are independent: a user with `has_permission_read=True` but
    `is_platform_admin=False` is the case the refactor protects against.
    A non-platform-admin who happens to hold `permission:read` should NOT
    be able to read the platform-wide permissions catalog. The current
    buggy code lets them through; the fix (use `has_role("platform_admin")`)
    blocks them. Tests with `has_permission_read=True` therefore FAIL
    on the current code (RED) and PASS after the fix (GREEN).
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            role == "platform_admin" and is_platform_admin
        )
    )
    # `has_permission` mirrors the real UserProfile: a platform_admin
    # implicitly holds every permission (the org-blind branch in
    # `UserProfile.has_permission` allows platform_admin through).
    # A non-platform-admin only gets True if they were explicitly
    # granted the permission via `has_permission_read`.
    profile.has_permission = Mock(
        side_effect=lambda perm, org_id=None: (
            is_platform_admin or has_permission_read
        )
    )
    return profile


class TestPermissionsListPlatformAdminOnly:
    """GET /permissions/ → platform_admin only."""

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        from src.rbac.permissions.routes import get_all_permissions

        profile = _make_profile(is_platform_admin=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_all_permissions = AsyncMock(return_value=([], None))

            result = await get_all_permissions(user_auth=(TEST_USER_ID, profile))
            assert result == []
            mock_svc.get_all_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_forbidden(self):
        from src.rbac.permissions.routes import get_all_permissions

        profile = _make_profile(is_org_admin=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_all_permissions = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_all_permissions(user_auth=(TEST_USER_ID, profile))

            assert exc_info.value.status_code == 403
            mock_svc.get_all_permissions.assert_not_called()

    @pytest.mark.asyncio
    async def test_regular_user_forbidden(self):
        from src.rbac.permissions.routes import get_all_permissions

        profile = _make_profile()
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_all_permissions = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_all_permissions(user_auth=(TEST_USER_ID, profile))

            assert exc_info.value.status_code == 403
            mock_svc.get_all_permissions.assert_not_called()

    @pytest.mark.asyncio
    async def test_permission_only_user_forbidden(self):
        """RED discriminator: user with `permission:read` but no
        platform_admin role. The current buggy code uses
        `has_permission("permission:read")` which returns True here,
        letting the user through (BUG). The fix replaces it with
        `has_role("platform_admin")` which returns False → 403."""
        from src.rbac.permissions.routes import get_all_permissions

        profile = _make_profile(has_permission_read=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_all_permissions = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_all_permissions(user_auth=(TEST_USER_ID, profile))

            assert exc_info.value.status_code == 403
            mock_svc.get_all_permissions.assert_not_called()


class TestPermissionGetPlatformAdminOnly:
    """GET /permissions/{permission_id} → platform_admin only."""

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        from src.rbac.permissions.routes import get_permission

        profile = _make_profile(is_platform_admin=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_permission_by_id = AsyncMock(
                return_value=(Mock(), None)
            )

            result = await get_permission(
                permission_id=TEST_PERMISSION_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result is not None
            mock_svc.get_permission_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_forbidden(self):
        from src.rbac.permissions.routes import get_permission

        profile = _make_profile(is_org_admin=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_permission_by_id = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_permission(
                    permission_id=TEST_PERMISSION_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_permission_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_permission_only_user_forbidden(self):
        """RED discriminator — see TestPermissionsListPlatformAdminOnly."""
        from src.rbac.permissions.routes import get_permission

        profile = _make_profile(has_permission_read=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_permission_by_id = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_permission(
                    permission_id=TEST_PERMISSION_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_permission_by_id.assert_not_called()


class TestRolePermissionsPlatformAdminOnly:
    """GET /permissions/roles/{role_id}/permissions → platform_admin only."""

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        from src.rbac.permissions.routes import get_permissions_for_role

        profile = _make_profile(is_platform_admin=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_permissions_for_role = AsyncMock(return_value=([], None))

            result = await get_permissions_for_role(
                role_id=TEST_ROLE_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result == []
            mock_svc.get_permissions_for_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_forbidden(self):
        from src.rbac.permissions.routes import get_permissions_for_role

        profile = _make_profile(is_org_admin=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_permissions_for_role = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_permissions_for_role(
                    role_id=TEST_ROLE_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_permissions_for_role.assert_not_called()

    @pytest.mark.asyncio
    async def test_permission_only_user_forbidden(self):
        """RED discriminator — see TestPermissionsListPlatformAdminOnly."""
        from src.rbac.permissions.routes import get_permissions_for_role

        profile = _make_profile(has_permission_read=True)
        with patch("src.rbac.permissions.routes.permission_service") as mock_svc:
            mock_svc.get_permissions_for_role = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_permissions_for_role(
                    role_id=TEST_ROLE_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_permissions_for_role.assert_not_called()


class TestRolesListPlatformAdminOnly:
    """GET /roles/ → platform_admin only."""

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        from src.rbac.roles.routes import get_all_roles

        profile = _make_profile(is_platform_admin=True)
        with patch("src.rbac.roles.routes.role_service") as mock_svc:
            mock_svc.get_all_roles = AsyncMock(return_value=([], None))

            result = await get_all_roles(user_auth=(TEST_USER_ID, profile))
            assert result == []
            mock_svc.get_all_roles.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_forbidden(self):
        from src.rbac.roles.routes import get_all_roles

        profile = _make_profile(is_org_admin=True)
        with patch("src.rbac.roles.routes.role_service") as mock_svc:
            mock_svc.get_all_roles = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_all_roles(user_auth=(TEST_USER_ID, profile))

            assert exc_info.value.status_code == 403
            mock_svc.get_all_roles.assert_not_called()

    @pytest.mark.asyncio
    async def test_role_read_only_user_forbidden(self):
        """RED discriminator for `role:read` variant."""
        from src.rbac.roles.routes import get_all_roles

        profile = _make_profile(has_permission_read=True)
        with patch("src.rbac.roles.routes.role_service") as mock_svc:
            mock_svc.get_all_roles = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_all_roles(user_auth=(TEST_USER_ID, profile))

            assert exc_info.value.status_code == 403
            mock_svc.get_all_roles.assert_not_called()


class TestRoleGetPlatformAdminOnly:
    """GET /roles/{role_id} → platform_admin only."""

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        from src.rbac.roles.routes import get_role

        profile = _make_profile(is_platform_admin=True)
        with patch("src.rbac.roles.routes.role_service") as mock_svc:
            mock_svc.get_role_by_id = AsyncMock(return_value=(Mock(), None))

            result = await get_role(
                role_id=TEST_ROLE_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result is not None
            mock_svc.get_role_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_forbidden(self):
        from src.rbac.roles.routes import get_role

        profile = _make_profile(is_org_admin=True)
        with patch("src.rbac.roles.routes.role_service") as mock_svc:
            mock_svc.get_role_by_id = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_role(
                    role_id=TEST_ROLE_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_role_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_role_read_only_user_forbidden(self):
        """RED discriminator — see TestRolesListPlatformAdminOnly."""
        from src.rbac.roles.routes import get_role

        profile = _make_profile(has_permission_read=True)
        with patch("src.rbac.roles.routes.role_service") as mock_svc:
            mock_svc.get_role_by_id = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_role(
                    role_id=TEST_ROLE_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_role_by_id.assert_not_called()
