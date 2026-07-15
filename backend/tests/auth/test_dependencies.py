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


class TestAssertHasPermission:
    """`assert_has_permission` — the imperative variant of the factory.

    Used inside a route handler *after* a resource has been loaded
    (e.g. after `voice_agent_service.get_agent(agent_id)` resolves
    the agent's `organization_id`). The dependency-injection
    `require_permission` factory can't help there because the org
    id is not yet known at dep-time.
    """

    def test_platform_admin_passes(self):
        from src.auth.dependencies import assert_has_permission

        profile = _make_profile(is_platform_admin=True)
        # Should NOT raise.
        assert_has_permission(profile, "agent", "update", TEST_ORG_A)

    def test_user_with_perm_on_target_org_passes(self):
        from src.auth.dependencies import assert_has_permission

        profile = _make_profile(has_perm_a="agent:update")
        # Should NOT raise.
        assert_has_permission(profile, "agent", "update", TEST_ORG_A)

    def test_user_with_perm_on_other_org_forbidden(self):
        from src.auth.dependencies import assert_has_permission

        profile = _make_profile(has_perm_b="agent:update")
        with pytest.raises(HTTPException) as exc_info:
            assert_has_permission(profile, "agent", "update", TEST_ORG_A)
        assert exc_info.value.status_code == 403
        # Default error message names the permission.
        assert "agent:update" in exc_info.value.detail

    def test_user_with_no_perm_forbidden(self):
        from src.auth.dependencies import assert_has_permission

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            assert_has_permission(profile, "agent", "update", TEST_ORG_A)
        assert exc_info.value.status_code == 403

    def test_custom_error_message_is_respected(self):
        from src.auth.dependencies import assert_has_permission

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            assert_has_permission(
                profile,
                "agent",
                "delete",
                TEST_ORG_A,
                error_message="Cannot delete this agent",
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Cannot delete this agent"

    def test_permission_string_is_built_correctly(self):
        """The internal `permission_name` must be `<resource>:<action>` —
        the format the UserProfile.has_permission check expects."""
        from src.auth.dependencies import assert_has_permission

        profile = _make_profile()  # no permissions at all
        with pytest.raises(HTTPException) as exc_info:
            assert_has_permission(
                profile, "phone_number", "create", TEST_ORG_A
            )
        # The default error names the exact permission string format.
        assert "phone_number:create" in exc_info.value.detail
        # And `has_permission` was called with the same shape
        # (no spaces, colon-separated, no wildcard hackery).
        called_with = profile.has_permission.call_args
        assert called_with.args[0] == "phone_number:create"
        assert called_with.args[1] == str(TEST_ORG_A)


class TestAssertHasRole:
    """`assert_has_role` — same pattern as `assert_has_permission` but
    for role-only checks (rare on the org-scoped surface, common
    for platform-scoped surfaces)."""

    def test_platform_admin_passes(self):
        from src.auth.dependencies import assert_has_role

        profile = _make_profile(is_platform_admin=True)
        # Should NOT raise.
        assert_has_role(profile, "org_admin", TEST_ORG_A)

    def test_org_admin_on_target_org_passes(self):
        from src.auth.dependencies import assert_has_role

        profile = _make_profile(role_for_org_a="org_admin")
        assert_has_role(profile, "org_admin", TEST_ORG_A)

    def test_org_admin_on_other_org_forbidden(self):
        from src.auth.dependencies import assert_has_role

        profile = _make_profile(role_for_org_b="org_admin")
        with pytest.raises(HTTPException) as exc_info:
            assert_has_role(profile, "org_admin", TEST_ORG_A)
        assert exc_info.value.status_code == 403
        assert "org_admin" in exc_info.value.detail

    def test_user_with_no_role_forbidden(self):
        from src.auth.dependencies import assert_has_role

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            assert_has_role(profile, "org_admin", TEST_ORG_A)
        assert exc_info.value.status_code == 403

    def test_custom_error_message_is_respected(self):
        from src.auth.dependencies import assert_has_role

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            assert_has_role(
                profile,
                "org_admin",
                TEST_ORG_A,
                error_message="Org-admin role required to manage members",
            )
        assert exc_info.value.status_code == 403
        assert (
            exc_info.value.detail
            == "Org-admin role required to manage members"
        )

    def test_role_check_uses_has_role_not_has_permission(self):
        """`assert_has_role` must call `has_role` (org-scoped) and NOT
        `has_permission` — they are separate contract channels."""
        from src.auth.dependencies import assert_has_role

        profile = _make_profile()  # no roles, no perms
        with pytest.raises(HTTPException):
            assert_has_role(profile, "org_admin", TEST_ORG_A)
        # has_role was called with the right args.
        role_calls = [
            c for c in profile.has_role.call_args_list
            if c.args and c.args[0] == "org_admin"
        ]
        assert role_calls, "has_role should have been called for org_admin"
        # has_permission was NEVER called for this code path.
        # (It is called for platform_admin detection, but only with
        # the literal "platform_admin" role name — never for the
        # business role we're asserting.)
        perm_arg_names = {
            call.args[0]
            for call in profile.has_permission.call_args_list
            if call.args
        }
        assert "org_admin" not in perm_arg_names


class TestCheckBillingPermissions:
    """`check_billing_permissions` is the shared dependency used by
    `billing/routes.py` (10 endpoints total). The check is the OR of
    four conditions (delegated to :func:`assert_billing_access`):

      1. `platform_admin` (org-agnostic, short-circuit).
      2. `org_admin` on the target org.
      3. `billing:manage` permission on the target org (the N1 nav/UI
         composite gate — a Phase 2 custom billing manager role without
         `org_admin` passes here).
      4. `billing:subscribe` permission on the target org (the legacy
         billing API seed — a non-admin who can drive the Stripe portal
         flow but doesn't manage the billing surface).

    Migrating the function to the factory under the hood preserves
    the public signature (still `async def` returning
    `(UUID, UserProfile)`) but routes the actual decision through
    `assert_billing_access` so the platform_admin short-circuit and
    org-scoped checks stay in one place.
    """

    def _import(self):
        # The function calls `get_authenticated_user` directly (not via
        # FastAPI Depends), so we patch the reference in the
        # dependencies module to bypass JWT decoding — the unit-test
        # contract is the org-scope check, not the JWT verification.
        from src.auth import dependencies

        self._original_get_authenticated_user = dependencies.get_authenticated_user
        return dependencies.check_billing_permissions

    def _stub_auth(self, profile, user_id=None):
        """Patch `get_authenticated_user` to return ``(user_id, profile)``."""
        from src.auth import dependencies

        async def fake_get_authenticated_user(authorization=None):
            return (user_id or profile.id, profile)

        dependencies.get_authenticated_user = fake_get_authenticated_user

    def _restore_auth(self):
        from src.auth import dependencies

        if hasattr(self, "_original_get_authenticated_user"):
            dependencies.get_authenticated_user = self._original_get_authenticated_user

    @pytest.mark.asyncio
    async def test_platform_admin_passes(self):
        check_billing_permissions = self._import()
        profile = _make_profile(is_platform_admin=True)
        self._stub_auth(profile)
        try:
            result = await check_billing_permissions(
                TEST_ORG_A, authorization="Bearer x"
            )
            assert result[1] is profile
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_org_admin_on_target_org_passes(self):
        check_billing_permissions = self._import()
        profile = _make_profile(role_for_org_a="org_admin")
        self._stub_auth(profile)
        try:
            result = await check_billing_permissions(
                TEST_ORG_A, authorization="Bearer x"
            )
            assert result[1] is profile
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_billing_subscribe_permission_on_target_org_passes(self):
        """The legacy API seed: a non-admin who holds `billing:subscribe`
        on the org. This is what a self-serve billing flow relies on
        before the org promotes them to org_admin."""
        check_billing_permissions = self._import()
        # No role, but the permission is held.
        profile = _make_profile(has_perm_a="billing:subscribe")
        self._stub_auth(profile)
        try:
            result = await check_billing_permissions(
                TEST_ORG_A, authorization="Bearer x"
            )
            assert result[1] is profile
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_billing_manage_permission_on_target_org_passes(self):
        """The N1 unification: a Phase 2 custom billing-manager role that
        holds `billing:manage` (but is NOT `org_admin`) must pass. This is
        the Phase 2 readiness contract — the bare `org_admin` role check
        was replaced by the `billing:manage` permission check."""
        check_billing_permissions = self._import()
        # No role, but the composite billing permission is held.
        profile = _make_profile(has_perm_a="billing:manage")
        self._stub_auth(profile)
        try:
            result = await check_billing_permissions(
                TEST_ORG_A, authorization="Bearer x"
            )
            assert result[1] is profile
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_billing_manage_on_other_org_forbidden(self):
        check_billing_permissions = self._import()
        profile = _make_profile(has_perm_b="billing:manage")
        self._stub_auth(profile)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await check_billing_permissions(
                    TEST_ORG_A, authorization="Bearer x"
                )
            assert exc_info.value.status_code == 403
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        check_billing_permissions = self._import()
        profile = _make_profile(role_for_org_b="org_admin")
        self._stub_auth(profile)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await check_billing_permissions(
                    TEST_ORG_A, authorization="Bearer x"
                )
            assert exc_info.value.status_code == 403
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_billing_subscribe_on_other_org_forbidden(self):
        check_billing_permissions = self._import()
        profile = _make_profile(has_perm_b="billing:subscribe")
        self._stub_auth(profile)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await check_billing_permissions(
                    TEST_ORG_A, authorization="Bearer x"
                )
            assert exc_info.value.status_code == 403
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_no_role_no_perm_forbidden(self):
        check_billing_permissions = self._import()
        profile = _make_profile()  # no roles, no perms
        self._stub_auth(profile)
        try:
            with pytest.raises(HTTPException) as exc_info:
                await check_billing_permissions(
                    TEST_ORG_A, authorization="Bearer x"
                )
            assert exc_info.value.status_code == 403
            # Detail must name the org-scoped contract so debug logs are useful.
            assert "billing" in exc_info.value.detail.lower()
        finally:
            self._restore_auth()

    @pytest.mark.asyncio
    async def test_function_signature_preserved(self):
        """Callers in `billing/` and `phone_numbers/` `Depends(...)` on
        this function with a single positional `organization_id` arg
        and a defaulted `authorization` Header. Any signature change
        breaks every caller."""
        import inspect

        check_billing_permissions = self._import()
        sig = inspect.signature(check_billing_permissions)
        params = list(sig.parameters.values())
        # First two must be organization_id (positional) and authorization (keyword).
        assert params[0].name == "organization_id"
        assert params[1].name == "authorization"
        # authorization must be optional (defaulted) so FastAPI can
        # pass the Header value without callers having to set it.
        assert params[1].default is not inspect.Parameter.empty



class TestAssertPlatformRole:
    """`assert_platform_role` — the org-agnostic counterpart of
    `assert_has_role` for routes that have no org_id in scope (e.g.
    subscription-plan CRUD, org deletion, RBAC catalog reads)."""

    def test_platform_admin_passes(self):
        from src.auth.dependencies import assert_platform_role

        profile = _make_profile(is_platform_admin=True)
        # Should NOT raise.
        assert_platform_role(profile, "platform_admin")

    def test_org_admin_on_target_org_fails(self):
        """The helper is org-agnostic — `org_admin` on a specific org
        is NOT `platform_admin` and must 403. This is the contract
        that the create/delete-organization routes rely on."""
        from src.auth.dependencies import assert_platform_role

        profile = _make_profile(role_for_org_a="org_admin")
        with pytest.raises(HTTPException) as exc_info:
            assert_platform_role(profile, "platform_admin")
        assert exc_info.value.status_code == 403
        assert "platform_admin" in exc_info.value.detail

    def test_user_with_no_role_fails(self):
        from src.auth.dependencies import assert_platform_role

        profile = _make_profile()  # no roles
        with pytest.raises(HTTPException) as exc_info:
            assert_platform_role(profile, "platform_admin")
        assert exc_info.value.status_code == 403

    def test_custom_error_message_is_respected(self):
        from src.auth.dependencies import assert_platform_role

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            assert_platform_role(
                profile,
                "platform_admin",
                error_message="Only platform admins can delete organizations",
            )
        assert exc_info.value.detail == "Only platform admins can delete organizations"
