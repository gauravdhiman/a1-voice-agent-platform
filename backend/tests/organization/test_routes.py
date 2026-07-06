"""
Tests for the /organizations/{org_id}/invite permission check (Task #32).

Closes the typo in `backend/src/organization/routes.py:187`:

    if not user_profile.has_permission("member:invite", str(org_id)):

The migration grants ``member:create`` (not ``member:invite``), so
the guard never matches — any user granted ``member:create`` is
incorrectly rejected with 403.

Contract:
  - User with `member:create` permission on the org → 200.
  - User with no permission and no admin role → 403.
  - User with `org_admin` role on the org → 200 (existing path).
  - User with `platform_admin` role → 200 (existing path).
  - `org_service.create_invitation` is NEVER called for a 403 path.
"""
import json

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

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
            perm == "member:create"
            and org_id == str(TEST_ORG_ID)
            and has_member_create
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

        with patch("src.organization.routes.organization_service") as mock_svc, \
             patch("src.organization.service.organization_service") as mock_svc_module:
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

        with patch("src.organization.routes.organization_service") as mock_svc, \
             patch("src.organization.service.organization_service") as mock_svc_module:
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

        with patch("src.organization.routes.organization_service") as mock_svc, \
             patch("src.organization.service.organization_service") as mock_svc_module:
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
