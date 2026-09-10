"""
Tests for the /organizations/{org_id}/invite permission check (Task #32).

The route guards with ``member:create`` (the canonical grant in
``alembic/versions/20260705000001_*``). Earlier revisions of this
test pinned the route to ``member:invite`` (the typo that this
task fixed); the typo guard never matched a real grant, so any
user granted ``member:create`` was incorrectly rejected with 403.

Contract:
  - User with `member:create` permission on the org → 200.
  - User with no permission and no admin role → 403.
  - User with `org_admin` role on the org → 200 (existing path).
  - User with `platform_admin` role → 200 (existing path).
  - `org_service.create_invitation` is NEVER called for a 403 path.
"""

import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000020")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000040")
TEST_EMAIL = "new.member@example.com"


def _make_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
    has_member_create: bool = False,
):
    """Build a UserProfile mock.

    `has_member_create` models the (org-scoped) `member:create` permission
    that the migration grants. `is_org_admin_on` is the org_id string
    for `org_admin`. `is_platform_admin` is org-agnostic.
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )
    profile.has_permission = Mock(
        side_effect=lambda perm, org_id=None: (
            perm == "member:create" and org_id == str(TEST_ORG_ID) and has_member_create
        )
    )
    return profile


def _make_invitation():
    inv = Mock()
    inv.id = UUID("00000000-0000-0000-0000-000000000099")
    inv.email = TEST_EMAIL
    return inv


def _make_json_request(body: dict) -> Request:
    """Build a real Starlette Request whose .json() returns the body.

    `request.json()` reads the receive channel — we provide a coroutine
    that returns the next 'http.request' message containing the body.
    """
    body_bytes = json.dumps(body).encode("utf-8")

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }
    return Request(scope, receive=receive)


class TestInviteMemberPermissionTypo:
    """The `member:invite` → `member:create` typo at organization/routes.py:187."""

    @pytest.mark.asyncio
    async def test_user_with_member_create_permission_allowed(self):
        """The bug: a user granted `member:create` is currently 403'd
        because the route checks `member:invite` (which doesn't exist).
        After fix: 200."""
        from src.organization.routes import invite_member

        profile = _make_profile(has_member_create=True)
        mock_request = _make_json_request({"email": TEST_EMAIL})

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.service.organization_service") as mock_svc_module,
        ):
            mock_svc.create_invitation = AsyncMock(
                return_value=(_make_invitation(), None)
            )
            mock_svc_module.create_invitation = mock_svc.create_invitation

            result = await invite_member(
                org_id=TEST_ORG_ID,
                request=mock_request,
                user_data=(TEST_USER_ID, profile),
            )

            assert result is not None
            mock_svc.create_invitation.assert_called_once()
            assert mock_svc.create_invitation.call_args.args[0].role.value == (
                "regular_user"
            )

    @pytest.mark.asyncio
    async def test_member_create_permission_cannot_invite_org_admin(self):
        """Elevated invitations require an administrator, not only member:create."""
        from src.organization.routes import invite_member

        profile = _make_profile(has_member_create=True)
        mock_request = _make_json_request({"email": TEST_EMAIL, "role": "org_admin"})

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.create_invitation = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await invite_member(
                    org_id=TEST_ORG_ID,
                    request=mock_request,
                    user_data=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.create_invitation.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_admin_can_invite_org_admin_role(self):
        """Platform administrators can select the elevated invitation role."""
        from src.organization.routes import invite_member

        profile = _make_profile(is_platform_admin=True)
        mock_request = _make_json_request({"email": TEST_EMAIL, "role": "org_admin"})

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.service.organization_service") as mock_svc_module,
        ):
            mock_svc.create_invitation = AsyncMock(
                return_value=(_make_invitation(), None)
            )
            mock_svc_module.create_invitation = mock_svc.create_invitation

            result = await invite_member(
                org_id=TEST_ORG_ID,
                request=mock_request,
                user_data=(TEST_USER_ID, profile),
            )

        assert result is not None
        invite_data = mock_svc.create_invitation.call_args.args[0]
        assert invite_data.role.value == "org_admin"

    @pytest.mark.asyncio
    async def test_invalid_invitation_role_is_rejected(self):
        """Invitation role input is limited to the supported organization roles."""
        from src.organization.routes import invite_member

        profile = _make_profile(is_platform_admin=True)
        mock_request = _make_json_request(
            {"email": TEST_EMAIL, "role": "billing_owner"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await invite_member(
                org_id=TEST_ORG_ID,
                request=mock_request,
                user_data=(TEST_USER_ID, profile),
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["message"] == (
            "Role must be regular_user or org_admin"
        )

    @pytest.mark.asyncio
    async def test_user_with_no_permission_forbidden(self):
        from src.organization.routes import invite_member

        profile = _make_profile()  # no roles, no permissions
        mock_request = _make_json_request({"email": TEST_EMAIL})

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.create_invitation = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await invite_member(
                    org_id=TEST_ORG_ID,
                    request=mock_request,
                    user_data=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.create_invitation.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_on_target_org_allowed(self):
        """org_admin on the target org bypasses the permission check."""
        from src.organization.routes import invite_member

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        mock_request = _make_json_request({"email": TEST_EMAIL})

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.service.organization_service") as mock_svc_module,
        ):
            mock_svc.create_invitation = AsyncMock(
                return_value=(_make_invitation(), None)
            )
            mock_svc_module.create_invitation = mock_svc.create_invitation

            result = await invite_member(
                org_id=TEST_ORG_ID,
                request=mock_request,
                user_data=(TEST_USER_ID, profile),
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_platform_admin_allowed(self):
        """platform_admin bypasses the permission check (org-agnostic)."""
        from src.organization.routes import invite_member

        profile = _make_profile(is_platform_admin=True)
        mock_request = _make_json_request({"email": TEST_EMAIL})

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.service.organization_service") as mock_svc_module,
        ):
            mock_svc.create_invitation = AsyncMock(
                return_value=(_make_invitation(), None)
            )
            mock_svc_module.create_invitation = mock_svc.create_invitation

            result = await invite_member(
                org_id=TEST_ORG_ID,
                request=mock_request,
                user_data=(TEST_USER_ID, profile),
            )

            assert result is not None


class TestDeleteOrganizationPlatformRole:
    """`delete_organization` is platform_admin-only. The 403 message
    is the contract the frontend surfaces on the org settings page
    danger zone."""

    @pytest.mark.asyncio
    async def test_non_platform_admin_gets_403(self):
        from src.organization.routes import delete_organization

        # An org_admin (not platform_admin) must NOT be able to delete
        # the org — this is a platform-only op.
        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))

        with pytest.raises(HTTPException) as exc_info:
            await delete_organization(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
        assert exc_info.value.status_code == 403
        assert "platform admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_no_role_gets_403(self):
        from src.organization.routes import delete_organization

        profile = _make_profile()  # no roles
        with pytest.raises(HTTPException) as exc_info:
            await delete_organization(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_platform_admin_does_not_403(self):
        """The 403 must NOT fire for platform_admin; downstream errors
        (e.g. org-not-found from the service) are a separate concern."""
        from src.organization.routes import delete_organization

        profile = _make_profile(is_platform_admin=True)

        with patch("src.organization.routes.organization_service") as mock_svc:
            # Simulate the service raising 404 for not-found, which is
            # a different code path from the auth 403.
            mock_svc.delete_organization = AsyncMock(
                return_value=(False, "Organization not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_organization(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )
            # The auth check passed (no 403); we get a 404 from the service.
            assert exc_info.value.status_code == 404


class TestCreateOrganizationPlatformRole:
    """`create_organization` is platform_admin-only. The 403 message
    matches `delete_organization`'s."""

    @pytest.mark.asyncio
    async def test_non_platform_admin_gets_403(self):
        from src.organization.models import OrganizationCreate
        from src.organization.routes import create_organization

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))

        with pytest.raises(HTTPException) as exc_info:
            await create_organization(
                org_data=OrganizationCreate(name="Test Org", slug="test-org"),
                user_data=(TEST_USER_ID, profile),
            )
        assert exc_info.value.status_code == 403
        assert "platform admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_platform_admin_creation_activates_default_free_plan(self):
        from src.organization.models import OrganizationCreate
        from src.organization.routes import create_organization

        profile = _make_profile(is_platform_admin=True)
        organization = Mock(id=TEST_ORG_ID)

        with (
            patch("src.organization.routes.organization_service") as mock_org,
            patch(
                "src.organization.routes.versioned_subscription_service"
            ) as mock_billing,
        ):
            mock_org.create_organization = AsyncMock(return_value=(organization, None))
            mock_billing.activate_default_free_plan = AsyncMock()

            result = await create_organization(
                org_data=OrganizationCreate(name="Test Org", slug="test-org"),
                user_data=(TEST_USER_ID, profile),
            )

        assert result is organization
        mock_billing.activate_default_free_plan.assert_awaited_once_with(TEST_ORG_ID)

    @pytest.mark.asyncio
    async def test_platform_admin_creation_assigns_selected_plan(self):
        from src.organization.models import PlatformOrganizationCreate
        from src.organization.routes import create_organization

        profile = _make_profile(is_platform_admin=True)
        organization = Mock(id=TEST_ORG_ID)
        selected_plan_id = UUID("00000000-0000-0000-0000-000000000055")

        with (
            patch("src.organization.routes.organization_service") as mock_org,
            patch(
                "src.organization.routes.versioned_subscription_service"
            ) as mock_billing,
        ):
            mock_org.create_organization = AsyncMock(return_value=(organization, None))
            mock_billing.assign_plan_for_platform_admin = AsyncMock()
            mock_billing.activate_default_free_plan = AsyncMock()

            result = await create_organization(
                org_data=PlatformOrganizationCreate(
                    name="Test Org",
                    slug="test-org",
                    plan_version_id=selected_plan_id,
                ),
                user_data=(TEST_USER_ID, profile),
            )

        assert result is organization
        mock_billing.assign_plan_for_platform_admin.assert_awaited_once_with(
            TEST_ORG_ID, selected_plan_id
        )
        mock_billing.activate_default_free_plan.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_platform_admin_creation_rolls_back_when_plan_assignment_fails(self):
        """Organization creation is rolled back if plan provisioning fails."""
        from src.organization.models import PlatformOrganizationCreate
        from src.organization.routes import create_organization

        profile = _make_profile(is_platform_admin=True)
        organization = Mock(id=TEST_ORG_ID)
        selected_plan_id = UUID("00000000-0000-0000-0000-000000000056")

        with (
            patch("src.organization.routes.organization_service") as mock_org,
            patch(
                "src.organization.routes.versioned_subscription_service"
            ) as mock_billing,
        ):
            mock_org.create_organization = AsyncMock(return_value=(organization, None))
            mock_org.delete_organization = AsyncMock(
                return_value=(False, "cleanup failed")
            )
            mock_billing.assign_plan_for_platform_admin = AsyncMock(
                side_effect=ValueError("selected plan unavailable")
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_organization(
                    org_data=PlatformOrganizationCreate(
                        name="Test Org",
                        slug="test-org",
                        plan_version_id=selected_plan_id,
                    ),
                    user_data=(TEST_USER_ID, profile),
                )

        assert exc_info.value.status_code == 500
        mock_org.delete_organization.assert_awaited_once_with(TEST_ORG_ID)


class TestUpdateOrganizationOrgAdminOnly:
    """`update_organization` accepts platform_admin or org_admin on
    the target org. The 403 fires for any other role."""

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_gets_403(self):
        from src.organization.models import OrganizationUpdate
        from src.organization.routes import update_organization

        # org_admin on a DIFFERENT org (not TEST_ORG_ID).
        profile = _make_profile(is_org_admin_on="00000000-0000-0000-0000-000000000999")

        with pytest.raises(HTTPException) as exc_info:
            await update_organization(
                org_id=TEST_ORG_ID,
                org_data=OrganizationUpdate(name="Renamed"),
                user_data=(TEST_USER_ID, profile),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_role_gets_403(self):
        from src.organization.models import OrganizationUpdate
        from src.organization.routes import update_organization

        profile = _make_profile()
        with pytest.raises(HTTPException) as exc_info:
            await update_organization(
                org_id=TEST_ORG_ID,
                org_data=OrganizationUpdate(name="Renamed"),
                user_data=(TEST_USER_ID, profile),
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Read + onboarding gate coverage (Epic C sweep — 3-way OR read gates).
#
# The invite/create/delete/update gates above are already covered. These
# classes fill the remaining N1-migrated gates:
#   - get_organization_members  (platform_admin / org_admin / organization:read)
#   - get_organization          (platform_admin / org_admin / organization:read)
#   - complete_onboarding       (org_admin only)
#   - get_all_organizations      (platform_admin read-scope vs. member scope)
# ---------------------------------------------------------------------------

OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000021")


def _make_read_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
    has_org_read_on: str | None = None,
):
    """Build a UserProfile mock for the organization:read 3-way OR gates.

    - ``is_platform_admin``: org-agnostic platform_admin role.
    - ``is_org_admin_on``: org_id string the user holds ``org_admin`` on.
    - ``has_org_read_on``: org_id string with ``organization:read`` (the
      regular_user grant for read-only workspace access).
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )

    def _has_permission(perm, org_id=None):
        return perm == "organization:read" and org_id == has_org_read_on

    profile.has_permission = Mock(side_effect=_has_permission)
    return profile


class TestGetOrganizationMembersReadGate:
    """``get_organization_members`` 3-way OR: platform_admin / org_admin /
    ``organization:read``. Unauthorized → 403, service never called."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.organization.routes import get_organization_members

        profile = _make_read_profile()

        with patch("src.organization.routes.user_role_service") as mock_svc:
            mock_svc.get_users_by_organization = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_organization_members(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_users_by_organization.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_admin_passes(self):
        from src.organization.routes import get_organization_members

        profile = _make_read_profile(is_platform_admin=True)
        members = [Mock()]

        with patch("src.organization.routes.user_role_service") as mock_svc:
            mock_svc.get_users_by_organization = AsyncMock(return_value=(members, None))

            result = await get_organization_members(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is members

    @pytest.mark.asyncio
    async def test_org_admin_on_target_org_passes(self):
        from src.organization.routes import get_organization_members

        profile = _make_read_profile(is_org_admin_on=str(TEST_ORG_ID))
        members = [Mock()]

        with patch("src.organization.routes.user_role_service") as mock_svc:
            mock_svc.get_users_by_organization = AsyncMock(return_value=(members, None))

            result = await get_organization_members(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is members

    @pytest.mark.asyncio
    async def test_org_read_permission_on_target_org_passes(self):
        """A regular_user with ``organization:read`` can list members."""
        from src.organization.routes import get_organization_members

        profile = _make_read_profile(has_org_read_on=str(TEST_ORG_ID))
        members = [Mock()]

        with patch("src.organization.routes.user_role_service") as mock_svc:
            mock_svc.get_users_by_organization = AsyncMock(return_value=(members, None))

            result = await get_organization_members(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is members

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        from src.organization.routes import get_organization_members

        profile = _make_read_profile(is_org_admin_on=str(OTHER_ORG_ID))

        with patch("src.organization.routes.user_role_service") as mock_svc:
            mock_svc.get_users_by_organization = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_organization_members(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_users_by_organization.assert_not_called()


class TestGetOrganizationReadGate:
    """``get_organization`` 3-way OR: platform_admin / org_admin /
    ``organization:read``."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.organization.routes import get_organization

        profile = _make_read_profile()

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.get_organization_by_id = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_organization(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_admin_passes(self):
        from src.organization.routes import get_organization

        profile = _make_read_profile(is_platform_admin=True)
        org = Mock()

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.get_organization_by_id = AsyncMock(return_value=(org, None))

            result = await get_organization(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is org

    @pytest.mark.asyncio
    async def test_org_read_permission_on_target_org_passes(self):
        from src.organization.routes import get_organization

        profile = _make_read_profile(has_org_read_on=str(TEST_ORG_ID))
        org = Mock()

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.get_organization_by_id = AsyncMock(return_value=(org, None))

            result = await get_organization(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is org

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        from src.organization.routes import get_organization

        profile = _make_read_profile(is_org_admin_on=str(OTHER_ORG_ID))

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.get_organization_by_id = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_organization(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_by_id.assert_not_called()


class TestCompleteOnboardingOrgAdminOnly:
    """``complete_onboarding`` is org_admin-only (one-way, idempotent)."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.organization.routes import complete_onboarding

        profile = _make_read_profile(is_org_admin_on=str(OTHER_ORG_ID))

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.complete_onboarding = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await complete_onboarding(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.complete_onboarding.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_admin_passes_via_short_circuit(self):
        """``complete_onboarding`` nominally requires ``org_admin``, but
        ``assert_has_role`` routes through ``_check_access`` which
        short-circuits on ``platform_admin``. So a platform_admin who is
        not an org_admin on the target org still passes. This pins the
        actual behavior (platform_admin is a global superuser); if the
        short-circuit is ever scoped out, this test must be updated."""
        from src.organization.routes import complete_onboarding

        profile = _make_read_profile(is_platform_admin=True)
        org = Mock()

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.routes.billing_service") as mock_billing,
        ):
            mock_svc.complete_onboarding = AsyncMock(return_value=(org, None))
            mock_billing.get_organization_subscription = AsyncMock(
                return_value=Mock(status="active")
            )

            result = await complete_onboarding(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is org

    @pytest.mark.asyncio
    async def test_org_admin_on_target_org_passes(self):
        from src.organization.routes import complete_onboarding

        profile = _make_read_profile(is_org_admin_on=str(TEST_ORG_ID))
        org = Mock()

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.routes.billing_service") as mock_billing,
        ):
            mock_svc.complete_onboarding = AsyncMock(return_value=(org, None))
            mock_billing.get_organization_subscription = AsyncMock(
                return_value=Mock(status="active")
            )

            result = await complete_onboarding(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is org

    @pytest.mark.asyncio
    async def test_complete_onboarding_does_not_call_missing_skill_seed(self):
        """Regression: dead seed_built_in_skills + missing logger caused HTTP 500."""
        from src.organization.routes import complete_onboarding

        profile = _make_read_profile(is_org_admin_on=str(TEST_ORG_ID))
        org = Mock()

        with (
            patch("src.organization.routes.organization_service") as mock_svc,
            patch("src.organization.routes.billing_service") as mock_billing,
        ):
            mock_svc.complete_onboarding = AsyncMock(return_value=(org, None))
            mock_billing.get_organization_subscription = AsyncMock(
                return_value=Mock(status="active")
            )
            result = await complete_onboarding(
                org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
            )
            assert result is org
            mock_svc.complete_onboarding.assert_awaited_once_with(TEST_ORG_ID)

    @pytest.mark.asyncio
    async def test_unselected_plan_cannot_complete_onboarding(self):
        """Founder onboarding cannot be completed before plan activation."""
        from src.organization.routes import complete_onboarding

        profile = _make_read_profile(is_org_admin_on=str(TEST_ORG_ID))

        with (
            patch("src.organization.routes.billing_service") as mock_billing,
            patch("src.organization.routes.organization_service") as mock_svc,
        ):
            mock_billing.get_organization_subscription = AsyncMock(return_value=None)
            mock_svc.complete_onboarding = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await complete_onboarding(
                    org_id=TEST_ORG_ID, user_data=(TEST_USER_ID, profile)
                )

        assert exc_info.value.status_code == 400
        assert "subscription" in str(exc_info.value.detail).lower()
        mock_svc.complete_onboarding.assert_not_called()


class TestGetAllOrganizationsReadScope:
    """``get_all_organizations`` uses a read-scope conditional: platform_admin
    sees every org; everyone else sees only orgs they belong to. This is a
    genuine branch (not a 403 gate)."""

    @pytest.mark.asyncio
    async def test_platform_admin_sees_all_organizations(self):
        from src.organization.routes import get_all_organizations

        profile = _make_read_profile(is_platform_admin=True)
        all_orgs = [Mock()]

        with patch("src.organization.routes.organization_service") as mock_svc:
            mock_svc.get_all_organizations = AsyncMock(return_value=(all_orgs, None))

            result = await get_all_organizations(user_data=(TEST_USER_ID, profile))
            assert result is all_orgs
            mock_svc.get_all_organizations.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_admin_sees_only_their_organizations(self):
        from src.organization.routes import get_all_organizations

        profile = _make_read_profile(has_org_read_on=str(TEST_ORG_ID))
        own_orgs = [Mock()]

        with patch("src.organization.routes.user_role_service") as mock_role_svc:
            mock_role_svc.get_organizations_for_user = AsyncMock(
                return_value=(own_orgs, None)
            )

            result = await get_all_organizations(user_data=(TEST_USER_ID, profile))
            assert result is own_orgs
            mock_role_svc.get_organizations_for_user.assert_called_once_with(
                TEST_USER_ID
            )
