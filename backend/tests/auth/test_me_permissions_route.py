"""
Route-level tests for the /me permission embedding.

The /me endpoint embeds the resolved permissions object on the
UserProfile response. These tests verify the integration between the
route, the auth middleware, and the permissions service.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.rbac.roles.models import (
    Permission,
    RoleWithPermissions,
    UserRoleWithPermissions,
)


# --- Helpers ---


def _permission(name: str) -> Permission:
    """Build a minimal Permission pydantic model for tests."""
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


def _role_with_perms(name: str, perms: list[Permission]) -> RoleWithPermissions:
    """Build a minimal RoleWithPermissions pydantic model for tests."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return RoleWithPermissions(
        id=uuid4(),
        name=name,
        description="",
        is_system_role=False,
        created_at=now,
        updated_at=now,
        permissions=perms,
    )


def _user_role(role: RoleWithPermissions, org_id) -> UserRoleWithPermissions:
    """Build a minimal UserRoleWithPermissions pydantic model for tests."""
    return UserRoleWithPermissions(
        user_role_id=uuid4(),
        organization_id=org_id,
        role=role,
    )


def _profile(roles: list[UserRoleWithPermissions]) -> UserProfile:
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


@pytest.fixture
def client():
    """Build a FastAPI TestClient with /me registered.

    Importing the real app pulls in the Supabase client and a lot of
    middleware; we build a minimal FastAPI app and register the /me route
    in isolation to keep the test hermetic.
    """
    from fastapi import APIRouter, Depends, FastAPI

    # Re-import the route module to keep this in sync with the real one.
    from src.auth.routes import get_current_user

    app = FastAPI()
    # Re-mount the route at the same path.
    app.include_router(
        # Build a tiny router that calls the same handler.
        APIRouter(),
    )
    # Register the existing /me route by including the module's router.
    from src.auth.routes import auth_router

    app.include_router(auth_router)
    return TestClient(app)


# --- Tests ---


class TestMeEmbedsPermissions:
    """The /me response embeds resolved permissions for the current org context."""

    def test_me_embeds_wildcard_for_platform_admin(self, client):
        platform_admin = _role_with_perms(
            "platform_admin", [_permission("platform:admin")]
        )
        user = _profile([_user_role(platform_admin, org_id=None)])

        app = client.app
        app.dependency_overrides[get_authenticated_user] = lambda: (user.id, user)

        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["permissions"] == {"*": ["*"]}
        # Platform admin has no current org in the request, so the field
        # reflects the caller's context (None when not provided).
        assert body["current_organization_id"] is None

    def test_me_embeds_org_scoped_permissions(self, client):
        org_id = uuid4()
        member = _role_with_perms(
            "member",
            [
                _permission("agent:read"),
                _permission("agent:write"),
                _permission("phone_number:read"),
                _permission("skill:read"),
                _permission("call_log:read"),
            ],
        )
        user = _profile([_user_role(member, org_id=org_id)])

        app = client.app
        app.dependency_overrides[get_authenticated_user] = lambda: (user.id, user)

        resp = client.get(
            f"/api/v1/auth/me?org_id={org_id}",
            headers={"Authorization": "Bearer fake"},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["current_organization_id"] == str(org_id)
        assert body["permissions"]["agent"] == ["read", "write"]
        assert body["permissions"]["phone_number"] == ["read"]
        assert body["permissions"]["skill"] == ["read"]
        assert body["permissions"]["call_log"] == ["read"]

    def test_me_returns_empty_permissions_when_no_org_query_param(self, client):
        member = _role_with_perms("member", [_permission("agent:read")])
        user = _profile([_user_role(member, org_id=uuid4())])

        app = client.app
        app.dependency_overrides[get_authenticated_user] = lambda: (user.id, user)

        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # No current org context provided -> empty permissions.
        assert body["permissions"] == {}
        assert body["current_organization_id"] is None

    def test_me_returns_401_when_unauthenticated(self, client):
        # Do NOT override get_authenticated_user; the real middleware
        # requires a Bearer token. Without one, it raises 401.
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
