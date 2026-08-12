"""
Route-level permission tests for ``src/phone_numbers/routes.py``.

N1 Epic C / §6 of the implementation report: the phone-number routes
previously gated on ``check_billing_permissions`` (the OR of
``platform_admin`` / ``org_admin`` / ``billing:subscribe``). That let a
``billing:subscribe``-only holder mutate phone inventory through the API
while the frontend ``canManagePhoneNumbers`` gate
(``phone_number:create|update|delete``) hid the UI from them — an
API/UI consistency gap.

The routes now gate on ``phone_number:<action>`` via
:func:`assert_has_permission` (platform_admin short-circuits inside the
helper). These tests pin that contract:

  - No role and no phone-number permission → 403, service never called.
  - ``org_admin`` on the target org (seeded with ``phone_number:*``) → passes.
  - ``platform_admin`` → passes (org-agnostic short-circuit).
  - ``billing:subscribe``-only on the target org → 403 (the legacy
    billing seed no longer grants phone-number mutations). This is the
    behavior change vs. the old ``check_billing_permissions`` gate.
  - ``org_admin`` on a *different* org → 403 (cross-org isolation).
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from shared.organization.phone_number_models import (
    PhoneNumberAssignRequest,
    PhoneNumberImportRequest,
    PhoneNumberPurchaseRequest,
)

TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000020")
TEST_OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000999")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000040")
TEST_PHONE_ID = UUID("00000000-0000-0000-0000-000000000070")


def _make_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
    has_phone_perm_on: str | None = None,
    phone_perm: str = "phone_number:create",
    has_billing_subscribe_on: str | None = None,
):
    """Build a UserProfile mock matching the N1 permission seed.

    - ``is_platform_admin``: org-agnostic platform_admin role.
    - ``is_org_admin_on``: org_id string the user holds ``org_admin`` on
      (the seed grants org_admin the full ``phone_number:*`` CRUD set;
      we model that by also granting the requested ``phone_perm``).
    - ``has_phone_perm_on``: org_id string the user holds a single
      ``phone_number:<action>`` permission on (custom-role case).
    - ``has_billing_subscribe_on``: org_id string the user holds the
      legacy ``billing:subscribe`` permission on (no phone-number perm).
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )

    def _has_permission(perm, org_id=None):
        # org_admin inherits the full phone_number:* CRUD set from the seed.
        if (
            is_org_admin_on is not None
            and org_id == is_org_admin_on
            and perm.startswith("phone_number:")
        ):
            return True
        if (
            has_phone_perm_on is not None
            and org_id == has_phone_perm_on
            and perm == phone_perm
        ):
            return True
        if (
            has_billing_subscribe_on is not None
            and org_id == has_billing_subscribe_on
            and perm == "billing:subscribe"
        ):
            return True
        return False

    profile.has_permission = Mock(side_effect=_has_permission)
    return profile


def _make_request() -> Request:
    """Build a real Starlette Request.

    ``purchase_phone_number`` is wrapped by ``@limiter.limit("3/hour")``,
    which validates that ``request`` is a Starlette ``Request`` (a Mock
    fails that check). The body is not read by these tests —
    ``purchase_request`` is passed as a constructed model.

    The rate limit itself is disabled per-test by the ``_disable_limiter``
    fixture so the shared in-memory counter doesn't exhaust across the
    five purchase cases in one session.
    """
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=receive)


@pytest.fixture(autouse=True)
def _disable_limiter(monkeypatch):
    """Disable the slowapi limiter for these route tests.

    The ``@limiter.limit("3/hour")`` decorator on ``purchase_phone_number``
    shares an in-memory counter across the test session; without disabling
    it, the 4th+ purchase call raises 429 before the permission check runs
    (the limiter runs before the route body). These tests exercise the
    permission gate, not rate limiting.
    """
    from src.security.rate_limiter import limiter

    monkeypatch.setattr(limiter, "enabled", False)


def _purchase_request():
    return PhoneNumberPurchaseRequest(phone_number="+1234567890", country_code="US")


def _assign_request():
    return PhoneNumberAssignRequest(
        agent_id=UUID("00000000-0000-0000-0000-0000000000a1")
    )


class TestPurchasePhoneNumberPermission:
    """``purchase_phone_number`` gates on ``phone_number:create``."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.phone_numbers.routes import purchase_phone_number

        profile = _make_profile()
        request = _make_request()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.purchase_number = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=request,
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.purchase_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_on_target_org_passes(self):
        from src.phone_numbers.routes import purchase_phone_number

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        request = _make_request()
        purchased = Mock()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.purchase_number = AsyncMock(return_value=(purchased, None))

            result = await purchase_phone_number(
                request=request,
                purchase_request=_purchase_request(),
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result is purchased
            mock_svc.purchase_number.assert_called_once()

    @pytest.mark.asyncio
    async def test_platform_admin_passes(self):
        from src.phone_numbers.routes import purchase_phone_number

        profile = _make_profile(is_platform_admin=True)
        request = _make_request()
        purchased = Mock()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.purchase_number = AsyncMock(return_value=(purchased, None))

            result = await purchase_phone_number(
                request=request,
                purchase_request=_purchase_request(),
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result is purchased

    @pytest.mark.asyncio
    async def test_billing_subscribe_only_now_forbidden(self):
        """The §6 behavior change: a legacy ``billing:subscribe``-only
        holder could purchase under the old ``check_billing_permissions``
        gate. They now get 403 because phone-number routes gate on
        ``phone_number:*``, not billing."""
        from src.phone_numbers.routes import purchase_phone_number

        profile = _make_profile(has_billing_subscribe_on=str(TEST_ORG_ID))
        request = _make_request()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.purchase_number = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=request,
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.purchase_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        from src.phone_numbers.routes import purchase_phone_number

        profile = _make_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        request = _make_request()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.purchase_number = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=request,
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.purchase_number.assert_not_called()


class TestListOrganizationNumbersPermission:
    """``list_organization_numbers`` gates on ``phone_number:read``."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.phone_numbers.routes import list_organization_numbers

        profile = _make_profile()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_organization_numbers = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await list_organization_numbers(
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_numbers.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_passes(self):
        from src.phone_numbers.routes import list_organization_numbers

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        listed = Mock()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_organization_numbers = AsyncMock(return_value=(listed, None))

            result = await list_organization_numbers(
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result is listed


class TestPlatformPhoneNumberSettingsRoutes:
    """Platform-admin-only settings and release-pending response behavior."""

    @pytest.mark.asyncio
    async def test_settings_require_platform_admin(self):
        from src.phone_numbers.routes import get_platform_phone_number_settings

        with patch(
            "src.phone_numbers.routes.platform_phone_number_settings_service"
        ) as mock_service:
            with pytest.raises(HTTPException) as exc_info:
                await get_platform_phone_number_settings(
                    user_auth=(TEST_USER_ID, _make_profile())
                )
            assert exc_info.value.status_code == 403
            mock_service.get_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_admin_can_read_settings(self):
        from src.phone_numbers.routes import get_platform_phone_number_settings

        settings = Mock()
        with patch(
            "src.phone_numbers.routes.platform_phone_number_settings_service"
        ) as mock_service:
            mock_service.get_settings = AsyncMock(return_value=settings)
            result = await get_platform_phone_number_settings(
                user_auth=(TEST_USER_ID, _make_profile(is_platform_admin=True))
            )
            assert result is settings
            mock_service.get_settings.assert_awaited_once_with(allow_fallback=False)

    @pytest.mark.asyncio
    async def test_release_pending_is_successful_queued_response(self):
        from src.phone_numbers.routes import cancel_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.cancel_number = AsyncMock(
                return_value=(True, "release_pending")
            )
            result = await cancel_phone_number(
                phone_number_id=TEST_PHONE_ID,
                organization_id=TEST_ORG_ID,
                user_auth=(
                    TEST_USER_ID,
                    _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                ),
            )
            assert result["success"] is True
            assert "retry" in result["message"]


class TestAssignPhoneNumberPermission:
    """``assign_phone_number_to_agent`` gates on ``phone_number:update``."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.phone_numbers.routes import assign_phone_number_to_agent

        profile = _make_profile()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.assign_to_agent = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await assign_phone_number_to_agent(
                    phone_number_id=TEST_PHONE_ID,
                    assign_request=_assign_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.assign_to_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_passes(self):
        from src.phone_numbers.routes import assign_phone_number_to_agent

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        assigned = Mock()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.assign_to_agent = AsyncMock(return_value=(assigned, None))

            result = await assign_phone_number_to_agent(
                phone_number_id=TEST_PHONE_ID,
                assign_request=_assign_request(),
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result["phone_number"] is assigned


class TestUnassignPhoneNumberPermission:
    """Unassigning a number uses the same scoped update permission."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.phone_numbers.routes import unassign_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.unassign_from_agent = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await unassign_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, _make_profile()),
                )

        assert exc_info.value.status_code == 403
        mock_svc.unassign_from_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_passes(self):
        from src.phone_numbers.routes import unassign_phone_number

        unassigned = Mock()
        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.unassign_from_agent = AsyncMock(return_value=(unassigned, None))
            result = await unassign_phone_number(
                phone_number_id=TEST_PHONE_ID,
                organization_id=TEST_ORG_ID,
                user_auth=(
                    TEST_USER_ID,
                    _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                ),
            )

        assert result["success"] is True
        assert result["phone_number"] is unassigned

    @pytest.mark.asyncio
    async def test_not_found_maps_to_404(self):
        from src.phone_numbers.routes import unassign_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.unassign_from_agent = AsyncMock(
                return_value=(None, "Phone number not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await unassign_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_service_error_maps_to_400(self):
        from src.phone_numbers.routes import unassign_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.unassign_from_agent = AsyncMock(
                return_value=(None, "Cannot unassign terminal number")
            )
            with pytest.raises(HTTPException) as exc_info:
                await unassign_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_unexpected_service_error_maps_to_500(self):
        from src.phone_numbers.routes import unassign_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.unassign_from_agent = AsyncMock(
                side_effect=RuntimeError("database unavailable")
            )
            with pytest.raises(HTTPException) as exc_info:
                await unassign_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500


class TestImportPhoneNumberPermission:
    """Existing Twilio numbers use the same organization create permission."""

    @pytest.mark.asyncio
    async def test_org_admin_can_import_without_provider_purchase(self):
        from src.phone_numbers.routes import import_phone_number

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        imported = Mock()
        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.import_number = AsyncMock(return_value=(imported, None))

            result = await import_phone_number(
                import_request=PhoneNumberImportRequest(phone_number="+14155550100"),
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )

        assert result is imported
        mock_svc.import_number.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_import_without_permission_is_forbidden(self):
        from src.phone_numbers.routes import import_phone_number

        profile = _make_profile()
        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.import_number = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await import_phone_number(
                    import_request=PhoneNumberImportRequest(
                        phone_number="+14155550100"
                    ),
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

        assert exc_info.value.status_code == 403
        mock_svc.import_number.assert_not_called()


class TestCancelPhoneNumberPermission:
    """``cancel_phone_number`` gates on ``phone_number:delete``."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.phone_numbers.routes import cancel_phone_number

        profile = _make_profile()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.cancel_number = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await cancel_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.cancel_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_passes(self):
        from src.phone_numbers.routes import cancel_phone_number

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.cancel_number = AsyncMock(return_value=(True, None))

            result = await cancel_phone_number(
                phone_number_id=TEST_PHONE_ID,
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result["success"] is True
