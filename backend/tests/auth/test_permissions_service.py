"""
Tests for the permission resolver used by GET /me.

These tests cover the contract from `docs/tw-drafts/navigation-redesign.md`:
the resolver returns a stable map of resource -> [actions] for the current
org, using a stub role-based resolution today (Phase 1) and a real per-role
lookup against the role_permissions table in Phase 2.

Resolution rules (Phase 1 stub):
- platform_admin role -> {"*": ["*"]} wildcard, plus every resource full set
- org_admin role on the current org -> every org-scoped action
- regular org member -> read on every org resource + write on
  agent/phone_number/skill; NOT billing:manage, member:invite,
  organization:update
- user not in any org -> empty permissions
"""
import pytest
from uuid import uuid4

from datetime import datetime, timezone
from uuid import uuid4

from src.auth.permissions_models import MyPermissions
from src.auth.permissions_service import resolve_permissions
from src.auth.models import UserProfile
from src.rbac.roles.models import (
    Permission,
    Role,
    RoleWithPermissions,
    UserRoleWithPermissions,
)


# --- Helpers ---


def _permission(name: str) -> Permission:
    """Build a minimal Permission pydantic model for tests.

    `name` follows the contract format "<resource>:<action>" (e.g.
    "agent:read"). The test helper splits it into the underlying
    `resource` and `action` fields the Permission pydantic model requires.
    """
    resource, _, action = name.partition(":")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Permission(
        id=uuid4(),
        name=name,
        description="",
        resource=resource,
        action=action,
        created_at=now,
        updated_at=now,
    )


def _role(name: str, permissions: list[Permission]) -> RoleWithPermissions:
    """Build a minimal RoleWithPermissions pydantic model for tests."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return RoleWithPermissions(
        id=uuid4(),
        name=name,
        description="",
        is_system_role=False,
        created_at=now,
        updated_at=now,
        permissions=permissions,
    )


def _user_role(
    role: RoleWithPermissions,
    organization_id=None,
) -> UserRoleWithPermissions:
    """Build a minimal UserRoleWithPermissions pydantic model for tests."""
    return UserRoleWithPermissions(
        user_role_id=uuid4(),
        organization_id=organization_id,
        role=role,
    )


def _profile_with_roles(roles: list[UserRoleWithPermissions]) -> UserProfile:
    """Build a minimal UserProfile pydantic model for tests."""
    return UserProfile(
        id=uuid4(),
        email="u@example.com",
        first_name="U",
        last_name="X",
        email_confirmed_at=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        has_organizations=bool(roles),
        roles=roles,
    )


# --- Tests ---


class TestResolvePermissionsPlatformAdmin:
    """Platform admins get every action on every resource (wildcard)."""

    def test_platform_admin_gets_wildcard(self):
        platform_admin_role = _role(
            "platform_admin", [_permission("platform:admin")]
        )
        profile = _profile_with_roles(
            [_user_role(platform_admin_role, organization_id=None)]
        )

        result = resolve_permissions(profile, current_organization_id=None)

        assert isinstance(result, MyPermissions)
        # Wildcard: every action on every resource is implied.
        assert result.permissions.get("*") == ["*"]

    def test_platform_admin_with_org_still_wildcard(self):
        """Platform admin's permissions are org-agnostic."""
        org_id = uuid4()
        platform_admin_role = _role(
            "platform_admin", [_permission("platform:admin")]
        )
        profile = _profile_with_roles(
            [_user_role(platform_admin_role, organization_id=None)]
        )

        result = resolve_permissions(profile, current_organization_id=org_id)

        assert result.permissions.get("*") == ["*"]


class TestResolvePermissionsOrgAdmin:
    """Org admins on the current org get every org-scoped action."""

    def test_org_admin_gets_full_org_scoped_set(self):
        org_id = uuid4()
        org_admin_role = _role(
            "org_admin",
            [_permission(f"{r}:{a}") for r in (
                "agent", "phone_number", "skill", "call_log",
                "member", "billing", "organization",
            ) for a in ("read", "write", "delete", "invite", "remove", "manage", "update")],
        )
        profile = _profile_with_roles(
            [_user_role(org_admin_role, organization_id=org_id)]
        )

        result = resolve_permissions(profile, current_organization_id=org_id)

        # All resources from the contract are present.
        for resource in (
            "agent", "phone_number", "skill", "call_log",
            "member", "billing", "organization",
        ):
            assert resource in result.permissions, (
                f"org_admin should have {resource} in permissions"
            )
        # write/delete/invite/remove/manage/update are present
        for action in ("write", "delete", "invite", "remove", "manage", "update"):
            assert any(
                action in actions
                for actions in result.permissions.values()
            ), f"org_admin should have {action} somewhere"

    def test_org_admin_role_on_different_org_does_not_apply(self):
        """An org_admin role on a different org does NOT grant the current org's perms."""
        current_org = uuid4()
        other_org = uuid4()
        org_admin_role = _role("org_admin", [_permission("agent:read")])
        profile = _profile_with_roles(
            [_user_role(org_admin_role, organization_id=other_org)]
        )

        result = resolve_permissions(profile, current_organization_id=current_org)

        # No permissions granted: the org_admin role is scoped to other_org.
        assert result.permissions == {}


class TestResolvePermissionsRegularMember:
    """Regular org members get read on every resource, plus write on agent/phone_number/skill."""

    def test_regular_member_gets_read_and_specific_writes(self):
        org_id = uuid4()
        member_role = _role(
            "member",
            [
                _permission("agent:read"),
                _permission("agent:write"),
                _permission("phone_number:read"),
                _permission("phone_number:write"),
                _permission("skill:read"),
                _permission("skill:write"),
                _permission("call_log:read"),
                _permission("member:read"),
                _permission("organization:read"),
            ],
        )
        profile = _profile_with_roles(
            [_user_role(member_role, organization_id=org_id)]
        )

        result = resolve_permissions(profile, current_organization_id=org_id)

        perms = result.permissions
        assert perms.get("agent") == ["read", "write"]
        assert perms.get("phone_number") == ["read", "write"]
        assert perms.get("skill") == ["read", "write"]
        assert perms.get("call_log") == ["read"]
        assert perms.get("member") == ["read"]
        assert perms.get("organization") == ["read"]
        # The member role does NOT grant these:
        assert "billing" not in perms
        assert "delete" not in perms.get("agent", [])
        assert "invite" not in perms.get("member", [])
        assert "update" not in perms.get("organization", [])


class TestResolvePermissionsDefensive:
    """Defensive branches: non-platform roles with no org scope are skipped."""

    def test_non_platform_role_with_no_org_scope_is_skipped(self):
        """A role with no organization_id that isn't platform_admin doesn't grant
        any permissions (the resolver can't scope them to the current org)."""
        org_id = uuid4()
        # Build a non-platform role with no org scope. This is unusual but
        # permitted by the data model. The resolver must skip it.
        weird_role = _role("weird_global", [_permission("agent:read")])
        good_member = _role("member", [_permission("agent:read")])
        profile = _profile_with_roles(
            [
                _user_role(weird_role, organization_id=None),
                _user_role(good_member, organization_id=org_id),
            ]
        )

        result = resolve_permissions(profile, current_organization_id=org_id)

        # Only the org-scoped role grants; the weird global role is ignored.
        assert result.permissions == {"agent": ["read"]}

    def test_org_admin_helper_returns_true_for_matching_role(self):
        """Sanity: org_admin helper is exercised directly (not used by resolver)."""
        from src.auth.permissions_service import _has_org_admin_on

        org_id = uuid4()
        other_org = uuid4()
        admin_role = _role("org_admin", [_permission("agent:read")])
        profile = _profile_with_roles(
            [_user_role(admin_role, organization_id=org_id)]
        )

        assert _has_org_admin_on(profile, org_id) is True
        assert _has_org_admin_on(profile, other_org) is False

    def test_service_class_wrapper_delegates_to_function(self):
        """`MyPermissionsService.resolve` is the public class-style API;
        tests should pin its behavior to the underlying function."""
        from src.auth.permissions_service import my_permissions_service

        org_id = uuid4()
        member_role = _role("member", [_permission("agent:read")])
        profile = _profile_with_roles(
            [_user_role(member_role, organization_id=org_id)]
        )

        # Both call paths must return the same shape.
        via_class = my_permissions_service.resolve(profile, current_organization_id=org_id)
        via_func = resolve_permissions(profile, current_organization_id=org_id)
        assert via_class.permissions == via_func.permissions
        assert via_class.current_organization_id == via_func.current_organization_id


class TestResolvePermissionsNoOrg:
    """Users not in any org get an empty permissions object."""

    def test_no_org_returns_empty(self):
        member_role = _role("member", [_permission("agent:read")])
        profile = _profile_with_roles(
            [_user_role(member_role, organization_id=uuid4())]
        )

        result = resolve_permissions(profile, current_organization_id=None)

        assert result.permissions == {}

    def test_no_roles_at_all_returns_empty(self):
        profile = _profile_with_roles([])

        result = resolve_permissions(profile, current_organization_id=uuid4())

        assert result.permissions == {}
