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
def _use_in_process_maintenance(monkeypatch):
    """These route-contract tests run without a database-backed worker."""
    from src.phone_numbers.maintenance_guard import settings

    monkeypatch.setattr(settings, "maintenance_mode", "in_process")


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
    async def test_rejects_non_us_platform_number_purchase(self):
        from src.phone_numbers.routes import purchase_phone_number

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        purchase_request = PhoneNumberPurchaseRequest(
            phone_number="+14155551234", country_code="CA"
        )

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.purchase_number = AsyncMock(
                return_value=(
                    None,
                    "Only US platform-provided phone numbers are available in v1.",
                )
            )

            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=purchase_request,
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

        assert exc_info.value.status_code == 400
        assert "Only US platform-provided" in exc_info.value.detail
        mock_svc.purchase_number.assert_awaited_once()

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


class TestSearchAvailableNumbers:
    """Search route tests pin the public provider-search contract."""

    @pytest.mark.asyncio
    async def test_search_requires_permission_for_pricing_organization(self):
        from src.phone_numbers.routes import search_available_numbers

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.search_available = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await search_available_numbers(
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, _make_profile()),
                )

        assert exc_info.value.status_code == 403
        mock_svc.search_available.assert_not_called()

    @pytest.mark.asyncio
    async def test_forwards_match_mode_and_filters(self):
        from src.phone_numbers.routes import search_available_numbers

        response = Mock()
        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.search_available = AsyncMock(return_value=(response, None))

            result = await search_available_numbers(
                organization_id=TEST_ORG_ID,
                country_code="US",
                phone_number_type="local",
                area_code="480",
                contains="2168",
                search_mode="ends_with",
                page=1,
                page_size=50,
                user_auth=(TEST_USER_ID, profile),
            )

        assert result is response
        request = mock_svc.search_available.await_args.args[0]
        assert request.country_code == "US"
        assert request.area_code == "480"
        assert request.contains == "2168"
        assert request.search_mode.value == "ends_with"
        assert mock_svc.search_available.await_args.args[1] == TEST_ORG_ID

    @pytest.mark.asyncio
    async def test_rejects_non_us_platform_number_search(self):
        from src.phone_numbers.routes import search_available_numbers

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.search_available = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await search_available_numbers(
                    organization_id=TEST_ORG_ID,
                    country_code="CA",
                    user_auth=(TEST_USER_ID, profile),
                )

        assert exc_info.value.status_code == 400
        assert "Only US platform-provided" in exc_info.value.detail
        mock_svc.search_available.assert_not_called()

    @pytest.mark.asyncio
    async def test_provider_error_maps_to_safe_bad_gateway_response(self):
        from src.phone_numbers.routes import search_available_numbers
        from src.phone_numbers.service import PHONE_NUMBER_SEARCH_UNAVAILABLE

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.search_available = AsyncMock(
                return_value=(None, "provider rate limit exceeded; account AC123456")
            )

            with pytest.raises(HTTPException) as exc_info:
                await search_available_numbers(
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == PHONE_NUMBER_SEARCH_UNAVAILABLE
        assert "AC123456" not in exc_info.value.detail

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import search_available_numbers

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.search_available = AsyncMock(
                side_effect=RuntimeError("provider secret")
            )

            with pytest.raises(HTTPException) as exc_info:
                await search_available_numbers(
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert (
            exc_info.value.detail
            == "Phone number search is temporarily unavailable. Please try again later."
        )


class TestGetAgentPhoneNumber:
    """The agent lookup route uses the phone-number read permission contract."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.phone_numbers.routes import get_agent_phone_number

        profile = _make_profile()

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_agent_number = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_agent_phone_number(
                    agent_id=UUID("00000000-0000-0000-0000-0000000000a1"),
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_svc.get_agent_number.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_returns_current_assignment(self):
        from src.phone_numbers.routes import get_agent_phone_number

        assignment = Mock()
        agent_id = UUID("00000000-0000-0000-0000-0000000000a1")
        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_agent_number = AsyncMock(return_value=(assignment, None))
            result = await get_agent_phone_number(
                agent_id=agent_id,
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )

            assert result is assignment
            mock_svc.get_agent_number.assert_awaited_once_with(
                organization_id=TEST_ORG_ID,
                agent_id=agent_id,
            )

    @pytest.mark.asyncio
    async def test_service_error_returns_server_error(self):
        from src.phone_numbers.routes import get_agent_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_agent_number = AsyncMock(
                return_value=(None, "database unavailable")
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_agent_phone_number(
                    agent_id=UUID("00000000-0000-0000-0000-0000000000a1"),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "database unavailable"

    @pytest.mark.asyncio
    async def test_unexpected_service_error_is_sanitized(self):
        from src.phone_numbers.routes import get_agent_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_agent_number = AsyncMock(side_effect=RuntimeError("secret"))
            with pytest.raises(HTTPException) as exc_info:
                await get_agent_phone_number(
                    agent_id=UUID("00000000-0000-0000-0000-0000000000a1"),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to load phone number for agent"


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

    @pytest.mark.asyncio
    async def test_cancel_does_not_touch_provider_while_organization_is_guarded(self):
        from contextlib import asynccontextmanager

        from src.phone_numbers.routes import cancel_phone_number

        @asynccontextmanager
        async def busy_guard(organization_id):
            assert organization_id == TEST_ORG_ID
            raise HTTPException(status_code=409, detail="Please retry shortly")
            yield

        with (
            patch("src.phone_numbers.routes.phone_mutation_guard", busy_guard),
            patch("src.phone_numbers.routes.phone_number_service") as mock_service,
        ):
            mock_service.cancel_number = AsyncMock()
            with pytest.raises(HTTPException) as error:
                await cancel_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )
        assert error.value.status_code == 409
        mock_service.cancel_number.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_platform_admin_can_update_settings(self):
        from src.phone_numbers.platform_settings_models import (
            PlatformPhoneNumberSettingsUpdate,
        )
        from src.phone_numbers.routes import update_platform_phone_number_settings

        payload = PlatformPhoneNumberSettingsUpdate(billing_grace_period_days=14)
        updated = Mock()
        with patch(
            "src.phone_numbers.routes.platform_phone_number_settings_service"
        ) as mock_service:
            mock_service.update_settings = AsyncMock(return_value=updated)
            result = await update_platform_phone_number_settings(
                payload=payload,
                user_auth=(TEST_USER_ID, _make_profile(is_platform_admin=True)),
            )

        assert result is updated
        mock_service.update_settings.assert_awaited_once_with(payload, TEST_USER_ID)


class TestPurchaseAndImportErrorMapping:
    """Route errors expose stable client-facing statuses and messages."""

    @pytest.mark.asyncio
    async def test_purchase_insufficient_credits_maps_to_payment_required(self):
        from src.phone_numbers.routes import purchase_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.purchase_number = AsyncMock(
                return_value=(None, "Insufficient credits to purchase the phone number")
            )
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_purchase_plan_limit_maps_to_payment_required(self):
        from src.phone_numbers.routes import purchase_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.purchase_number = AsyncMock(
                return_value=(
                    None,
                    "Your plan allows 0 phone numbers. You currently have 0.",
                )
            )
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_purchase_other_service_error_maps_to_bad_request(self):
        from src.phone_numbers.routes import purchase_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.purchase_number = AsyncMock(
                return_value=(None, "Phone number already exists")
            )
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_purchase_provider_failure_is_safe_and_maps_to_502(self):
        from src.phone_numbers.routes import purchase_phone_number
        from src.phone_numbers.service import PHONE_NUMBER_PURCHASE_UNAVAILABLE

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.purchase_number = AsyncMock(
                return_value=(None, PHONE_NUMBER_PURCHASE_UNAVAILABLE)
            )
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == PHONE_NUMBER_PURCHASE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_purchase_terminal_idempotency_reuse_maps_to_conflict(self):
        from src.phone_numbers.routes import purchase_phone_number

        message = (
            "This purchase attempt has ended. Start a new purchase with a fresh "
            "idempotency key."
        )
        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.purchase_number = AsyncMock(return_value=(None, message))
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_purchase_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import purchase_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.purchase_number = AsyncMock(side_effect=RuntimeError("secret"))
            with pytest.raises(HTTPException) as exc_info:
                await purchase_phone_number(
                    request=_make_request(),
                    purchase_request=_purchase_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to purchase phone number"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [
            ("plan allows 0 phone numbers", 403),
            ("invalid phone number", 400),
            ("provider rate limit exceeded", 400),
        ],
    )
    async def test_import_error_mapping(self, error, expected_status):
        from src.phone_numbers.routes import import_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.import_number = AsyncMock(return_value=(None, error))
            with pytest.raises(HTTPException) as exc_info:
                await import_phone_number(
                    import_request=PhoneNumberImportRequest(
                        phone_number="+14807452168"
                    ),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == expected_status
        assert exc_info.value.detail == error

    @pytest.mark.asyncio
    async def test_import_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import import_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.import_number = AsyncMock(side_effect=RuntimeError("secret"))
            with pytest.raises(HTTPException) as exc_info:
                await import_phone_number(
                    import_request=PhoneNumberImportRequest(
                        phone_number="+14807452168"
                    ),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to connect phone number"


class TestVerificationDetailsAndAssignmentErrors:
    """Customer setup and assignment routes cover their error contracts."""

    @pytest.mark.asyncio
    async def test_verification_details_success(self):
        from src.phone_numbers.routes import get_phone_number_verification_details

        details = Mock()
        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.get_verification_details = AsyncMock(
                return_value=(details, None)
            )
            result = await get_phone_number_verification_details(
                phone_number_id=TEST_PHONE_ID,
                organization_id=TEST_ORG_ID,
                user_auth=(
                    TEST_USER_ID,
                    _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                ),
            )

        assert result is details

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [("Phone number not found", 404), ("Setup is no longer pending", 400)],
    )
    async def test_verification_details_error_mapping(self, error, expected_status):
        from src.phone_numbers.routes import get_phone_number_verification_details

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.get_verification_details = AsyncMock(
                return_value=(None, error)
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_phone_number_verification_details(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == expected_status

    @pytest.mark.asyncio
    async def test_verification_details_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import get_phone_number_verification_details

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.get_verification_details = AsyncMock(
                side_effect=RuntimeError("secret")
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_phone_number_verification_details(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert (
            exc_info.value.detail == "Failed to load phone-number verification details"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [
            ("Phone number not found", 404),
            ("Phone number is already assigned to an agent", 409),
            ("Invalid assignment", 400),
        ],
    )
    async def test_assignment_error_mapping(self, error, expected_status):
        from src.phone_numbers.routes import assign_phone_number_to_agent

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.assign_to_agent = AsyncMock(return_value=(None, error))
            with pytest.raises(HTTPException) as exc_info:
                await assign_phone_number_to_agent(
                    phone_number_id=TEST_PHONE_ID,
                    assign_request=_assign_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == expected_status

    @pytest.mark.asyncio
    async def test_assignment_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import assign_phone_number_to_agent

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.assign_to_agent = AsyncMock(side_effect=RuntimeError("secret"))
            with pytest.raises(HTTPException) as exc_info:
                await assign_phone_number_to_agent(
                    phone_number_id=TEST_PHONE_ID,
                    assign_request=_assign_request(),
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to assign phone number"


class TestOrganizationListAndCancelErrors:
    """List, unassign, and release routes sanitize service failures."""

    @pytest.mark.asyncio
    async def test_list_service_error_preserves_service_detail(self):
        from src.phone_numbers.routes import list_organization_numbers

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.get_organization_numbers = AsyncMock(
                return_value=(None, "database unavailable")
            )
            with pytest.raises(HTTPException) as exc_info:
                await list_organization_numbers(
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "database unavailable"

    @pytest.mark.asyncio
    async def test_list_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import list_organization_numbers

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.get_organization_numbers = AsyncMock(
                side_effect=RuntimeError("secret")
            )
            with pytest.raises(HTTPException) as exc_info:
                await list_organization_numbers(
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to list phone numbers"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [("Phone number not found", 404), ("Cannot unassign number", 400)],
    )
    async def test_unassign_error_mapping(self, error, expected_status):
        from src.phone_numbers.routes import unassign_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.unassign_from_agent = AsyncMock(return_value=(None, error))
            with pytest.raises(HTTPException) as exc_info:
                await unassign_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == expected_status

    @pytest.mark.asyncio
    async def test_unassign_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import unassign_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.unassign_from_agent = AsyncMock(
                side_effect=RuntimeError("secret")
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
        assert exc_info.value.detail == "Failed to unassign phone number"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [("Phone number not found", 404), ("Provider release failed", 400)],
    )
    async def test_cancel_error_mapping(self, error, expected_status):
        from src.phone_numbers.routes import cancel_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.cancel_number = AsyncMock(return_value=(False, error))
            with pytest.raises(HTTPException) as exc_info:
                await cancel_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == expected_status

    @pytest.mark.asyncio
    async def test_cancel_unexpected_error_is_sanitized(self):
        from src.phone_numbers.routes import cancel_phone_number

        with patch("src.phone_numbers.routes.phone_number_service") as mock_service:
            mock_service.cancel_number = AsyncMock(side_effect=RuntimeError("secret"))
            with pytest.raises(HTTPException) as exc_info:
                await cancel_phone_number(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(
                        TEST_USER_ID,
                        _make_profile(is_org_admin_on=str(TEST_ORG_ID)),
                    ),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to cancel phone number"


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


class TestVerificationDetailsPermission:
    """Pending webhook URLs use the phone-number read permission."""

    @pytest.mark.asyncio
    async def test_org_admin_can_read_verification_details(self):
        from src.phone_numbers.routes import get_phone_number_verification_details

        details = Mock()
        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_verification_details = AsyncMock(return_value=(details, None))

            result = await get_phone_number_verification_details(
                phone_number_id=TEST_PHONE_ID,
                organization_id=TEST_ORG_ID,
                user_auth=(TEST_USER_ID, profile),
            )

        assert result is details
        mock_svc.get_verification_details.assert_awaited_once_with(
            organization_id=TEST_ORG_ID,
            phone_number_id=TEST_PHONE_ID,
        )

    @pytest.mark.asyncio
    async def test_verification_details_without_permission_are_forbidden(self):
        from src.phone_numbers.routes import get_phone_number_verification_details

        profile = _make_profile()
        with patch("src.phone_numbers.routes.phone_number_service") as mock_svc:
            mock_svc.get_verification_details = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await get_phone_number_verification_details(
                    phone_number_id=TEST_PHONE_ID,
                    organization_id=TEST_ORG_ID,
                    user_auth=(TEST_USER_ID, profile),
                )

        assert exc_info.value.status_code == 403
        mock_svc.get_verification_details.assert_not_called()


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
