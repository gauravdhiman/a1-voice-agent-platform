"""
Tests for the require_permission / require_role FastAPI dependency
factories (Task #22 — Phase 5).

The factory expresses the same "check the caller's right" pattern
that today appears inline in every route. Two shapes:

    @router.post("/...")
    async def create_agent(
        agent_data: VoiceAgentCreate,
        _=Depends(require_permission("agent", "create", org_id_source="body",
                                     body_field="organization_id")),
    ):
        ...

    @router.delete("/organizations/{org_id}/members/{member_id}")
    async def remove_member(
        org_id: UUID,
        _=Depends(require_role("org_admin", org_id_source="path")),
    ):
        ...

Tests are split into two layers:

  1. `TestCheckAccessRole` / `TestCheckAccessPermission` — pure unit
     tests against the dependency-agnostic `_check_access` function.
     These pin the role/permission logic without involving FastAPI.

  2. `TestRequireRoleFactory` — construction-time tests for the
     `require_role` / `require_permission` factories. Verifies that
     unsupported `org_id_source` values raise at construction time
     (not at request time, so misconfiguration surfaces during app
     startup or test collection).

Integration with FastAPI dependency injection (the actual end-to-end
behavior of `Depends(require_permission(...))`) is covered separately
by `TestCreateAgentDeclarativePermission` in
`tests/voice_agents/test_agent_routes.py`.
"""
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException

TEST_ORG_A = UUID("00000000-0000-0000-0000-0000000000a1")
TEST_ORG_B = UUID("00000000-0000-0000-0000-0000000000b2")


def _make_profile(
    is_platform_admin: bool = False,
    role_for_org_a: str | None = None,
    role_for_org_b: str | None = None,
    has_perm_a: str | None = None,
    has_perm_b: str | None = None,
):
    """Build a UserProfile mock.

    - is_platform_admin: grants platform_admin role (org-agnostic).
    - role_for_org_a/b: the org-scoped role for that org (e.g. "org_admin").
    - has_perm_a/b: a permission name the user holds on that org
      (e.g. "agent:create").
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == role_for_org_a and org_id == str(TEST_ORG_A))
            or (role == role_for_org_b and org_id == str(TEST_ORG_B))
        )
    )
    profile.has_permission = Mock(
        side_effect=lambda perm, org_id=None: (
            (perm == has_perm_a and org_id == str(TEST_ORG_A))
            or (perm == has_perm_b and org_id == str(TEST_ORG_B))
        )
    )
    return profile


class TestCheckAccessRole:
    """Unit tests for the pure `_check_access` function — the
    dependency-agnostic core of the factory. These run as pure
    Python (no FastAPI TestClient needed) and pin the role/permission
    logic in isolation.

    Integration of `_check_access` with FastAPI dependency injection
    is covered by `TestCreateAgentDeclarativePermission` in
    `tests/voice_agents/test_agent_routes.py`.
    """

    def test_platform_admin_passes(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile(is_platform_admin=True)
        # Should NOT raise.
        _check_access(
            user_profile=profile,
            check_kind="role",
            check_arg="org_admin",
            org_id=TEST_ORG_A,
            error_message="nope",
        )

    def test_org_admin_on_target_org_passes(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile(role_for_org_a="org_admin")
        _check_access(
            user_profile=profile,
            check_kind="role",
            check_arg="org_admin",
            org_id=TEST_ORG_A,
            error_message="nope",
        )

    def test_org_admin_on_other_org_forbidden(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile(role_for_org_b="org_admin")
        with pytest.raises(HTTPException) as exc_info:
            _check_access(
                user_profile=profile,
                check_kind="role",
                check_arg="org_admin",
                org_id=TEST_ORG_A,
                error_message="nope",
            )
        assert exc_info.value.status_code == 403

    def test_user_with_no_role_forbidden(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            _check_access(
                user_profile=profile,
                check_kind="role",
                check_arg="org_admin",
                org_id=TEST_ORG_A,
                error_message="nope",
            )
        assert exc_info.value.status_code == 403


class TestCheckAccessPermission:
    """Permission variant of _check_access."""

    def test_user_with_perm_on_target_org_passes(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile(has_perm_a="agent:create")
        _check_access(
            user_profile=profile,
            check_kind="permission",
            check_arg="agent:create",
            org_id=TEST_ORG_A,
            error_message="nope",
        )

    def test_user_with_perm_on_other_org_forbidden(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile(has_perm_b="agent:create")
        with pytest.raises(HTTPException) as exc_info:
            _check_access(
                user_profile=profile,
                check_kind="permission",
                check_arg="agent:create",
                org_id=TEST_ORG_A,
                error_message="nope",
            )
        assert exc_info.value.status_code == 403

    def test_user_with_no_perm_forbidden(self):
        from src.auth.dependencies import _check_access

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            _check_access(
                user_profile=profile,
                check_kind="permission",
                check_arg="agent:create",
                org_id=TEST_ORG_A,
                error_message="nope",
            )
        assert exc_info.value.status_code == 403


class TestRequireRoleFactory:
    """The `require_role` factory itself — not the check logic.
    Verifies that constructing a factory with valid args succeeds
    and that unsupported sources raise."""

    def test_query_source_not_implemented(self):
        from src.auth.dependencies import require_role

        with pytest.raises(NotImplementedError):
            require_role("org_admin", org_id_source="query")

    def test_header_source_not_implemented(self):
        from src.auth.dependencies import require_permission

        with pytest.raises(NotImplementedError):
            require_permission("agent", "read", org_id_source="header")

    def test_require_permission_body_requires_body_field(self):
        from src.auth.dependencies import require_permission

        with pytest.raises(ValueError):
            require_permission("agent", "create", org_id_source="body")
