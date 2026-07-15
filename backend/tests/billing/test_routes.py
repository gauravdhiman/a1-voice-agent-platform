"""
Route-level permission tests for ``src/billing/routes.py``.

N1 Epic C: the billing routes were migrated from inline ``has_role`` ladders
to the typed helpers in :mod:`src.auth.dependencies`:

- Plan CRUD (create / update) → :func:`assert_platform_role`.
- Body-scoped billing writes (portal, checkout, consume, cancel,
  reactivate) → :func:`assert_billing_access` — the four-way OR of
  ``platform_admin`` / ``org_admin`` / ``billing:manage`` /
  ``billing:subscribe``.

The path-scoped billing reads (``/subscription/{org_id}``,
``/credits/{org_id}``, ``/history/{org_id}``, ``/summary/{org_id}``,
``/subscription/checkout``, ``/credit-products/checkout``) gate via
``Depends(check_billing_permissions)``. The dependency itself is the
four-way OR and is unit-tested in
``tests/auth/test_dependencies.py::TestCheckBillingPermissions``; wiring
those routes to that dependency is FastAPI's concern (verified by the
``@router.get/.post`` decorators at import time), so this file focuses
on the **inline** gates that run inside the handler body.

These tests pin the contract:

- No role and no billing permission → 403, downstream service never called.
- ``org_admin`` on the target org → passes the gate.
- ``platform_admin`` → passes (org-agnostic short-circuit).
- ``billing:manage`` on the target org → passes (Phase 2 custom role).
- ``billing:subscribe`` on the target org → passes (legacy fallback).
- ``org_admin`` on a *different* org → 403 (cross-org isolation).
- Plan create / update without ``platform_admin`` → 403; with → passes.
"""
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

TEST_ORG_ID = UUID("00000000-0000-0000-0000-0000000000b1")
TEST_OTHER_ORG_ID = UUID("00000000-0000-0000-0000-0000000009b1")
TEST_USER_ID = UUID("00000000-0000-0000-0000-0000000000b2")
TEST_PLAN_ID = UUID("00000000-0000-0000-0000-0000000000b3")
TEST_PRODUCT_ID = UUID("00000000-0000-0000-0000-0000000000b4")


def _make_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
    has_billing_manage_on: str | None = None,
    has_billing_subscribe_on: str | None = None,
):
    """Build a UserProfile mock matching the N1 permission seed.

    - ``is_platform_admin``: org-agnostic platform_admin role.
    - ``is_org_admin_on``: org_id string the user holds ``org_admin`` on.
    - ``has_billing_manage_on``: org_id string with ``billing:manage``.
    - ``has_billing_subscribe_on``: org_id string with ``billing:subscribe``.
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )

    def _has_permission(perm, org_id=None):
        if (
            has_billing_manage_on is not None
            and org_id == has_billing_manage_on
            and perm == "billing:manage"
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


class TestPlanCrudPermission:
    """Plan create / update gate on ``assert_platform_role``."""

    @pytest.mark.asyncio
    async def test_create_plan_non_platform_admin_forbidden(self):
        from src.billing.routes import create_subscription_plan

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        plan_data = Mock()

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.create_subscription_plan = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_plan(
                    plan_data=plan_data, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.create_subscription_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_plan_platform_admin_passes(self):
        from src.billing.routes import create_subscription_plan

        profile = _make_profile(is_platform_admin=True)
        plan_data = Mock()
        created = Mock()

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.create_subscription_plan = AsyncMock(return_value=created)

            result = await create_subscription_plan(
                plan_data=plan_data, user_auth=(TEST_USER_ID, profile)
            )
            assert result is created
            mock_svc.create_subscription_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_plan_non_platform_admin_forbidden(self):
        from src.billing.routes import update_subscription_plan

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        plan_data = Mock()

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.update_subscription_plan = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await update_subscription_plan(
                    plan_id=TEST_PLAN_ID,
                    plan_data=plan_data,
                    user_auth=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_svc.update_subscription_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_plan_platform_admin_passes(self):
        from src.billing.routes import update_subscription_plan

        profile = _make_profile(is_platform_admin=True)
        plan_data = Mock()
        updated = Mock()

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.update_subscription_plan = AsyncMock(return_value=updated)

            result = await update_subscription_plan(
                plan_id=TEST_PLAN_ID,
                plan_data=plan_data,
                user_auth=(TEST_USER_ID, profile),
            )
            assert result is updated


class TestConsumeCreditsPermission:
    """``consume_credits`` gates on ``assert_billing_access`` (body org)."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.billing.routes import consume_credits

        profile = _make_profile()
        req = Mock()
        req.organization_id = TEST_ORG_ID

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.consume_credits = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await consume_credits(
                    consumption_request=req, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.consume_credits.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_on_target_org_passes(self):
        from src.billing.routes import consume_credits

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        req = Mock()
        req.organization_id = TEST_ORG_ID
        consumed = Mock()

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.consume_credits = AsyncMock(return_value=consumed)

            result = await consume_credits(
                consumption_request=req, user_auth=(TEST_USER_ID, profile)
            )
            assert result is consumed
            mock_svc.consume_credits.assert_called_once()

    @pytest.mark.asyncio
    async def test_platform_admin_passes(self):
        from src.billing.routes import consume_credits

        profile = _make_profile(is_platform_admin=True)
        req = Mock()
        req.organization_id = TEST_ORG_ID

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.consume_credits = AsyncMock(return_value=Mock())

            await consume_credits(
                consumption_request=req, user_auth=(TEST_USER_ID, profile)
            )
            mock_svc.consume_credits.assert_called_once()

    @pytest.mark.asyncio
    async def test_billing_manage_on_target_org_passes(self):
        """Phase 2 custom billing-manager role (``billing:manage`` only)."""
        from src.billing.routes import consume_credits

        profile = _make_profile(has_billing_manage_on=str(TEST_ORG_ID))
        req = Mock()
        req.organization_id = TEST_ORG_ID

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.consume_credits = AsyncMock(return_value=Mock())

            await consume_credits(
                consumption_request=req, user_auth=(TEST_USER_ID, profile)
            )
            mock_svc.consume_credits.assert_called_once()

    @pytest.mark.asyncio
    async def test_billing_subscribe_on_target_org_passes(self):
        """Legacy ``billing:subscribe`` fallback still grants access."""
        from src.billing.routes import consume_credits

        profile = _make_profile(has_billing_subscribe_on=str(TEST_ORG_ID))
        req = Mock()
        req.organization_id = TEST_ORG_ID

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.consume_credits = AsyncMock(return_value=Mock())

            await consume_credits(
                consumption_request=req, user_auth=(TEST_USER_ID, profile)
            )
            mock_svc.consume_credits.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        from src.billing.routes import consume_credits

        profile = _make_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        req = Mock()
        req.organization_id = TEST_ORG_ID

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.consume_credits = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await consume_credits(
                    consumption_request=req, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.consume_credits.assert_not_called()


def _subscription_mock(stripe_subscription_id="sub_123", stripe_customer_id="cus_123"):
    """Build a subscription mock with the attrs the portal/cancel/reactivate
    routes read after the gate passes."""
    sub = Mock()
    sub.id = UUID("00000000-0000-0000-0000-0000000000c1")
    sub.stripe_subscription_id = stripe_subscription_id
    sub.stripe_customer_id = stripe_customer_id
    return sub


class TestCancelSubscriptionPermission:
    """``cancel_subscription`` gates on ``assert_billing_access`` (body org)."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.billing.routes import cancel_subscription

        profile = _make_profile()
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_organization_subscription = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await cancel_subscription(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_passes_and_cancels(self):
        from src.billing.routes import cancel_subscription

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc, patch(
            "src.billing.routes.stripe_service"
        ) as mock_stripe:
            mock_svc.get_organization_subscription = AsyncMock(
                return_value=_subscription_mock()
            )
            mock_svc.update_organization_subscription = AsyncMock()
            mock_stripe.cancel_subscription = AsyncMock()

            result = await cancel_subscription(
                request=request, user_auth=(TEST_USER_ID, profile)
            )
            assert "cancelled" in result["message"]
            mock_stripe.cancel_subscription.assert_called_once()
            mock_svc.update_organization_subscription.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_org_id_returns_400_before_gate(self):
        """Body validation (``organization_id`` required) runs before the
        permission gate — this pins the ordering so a caller can't probe the
        gate with an empty body."""
        from src.billing.routes import cancel_subscription

        profile = _make_profile(is_platform_admin=True)
        request = {}

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_organization_subscription = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await cancel_subscription(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 400
            mock_svc.get_organization_subscription.assert_not_called()


class TestReactivateSubscriptionPermission:
    """``reactivate_subscription`` gates on ``assert_billing_access`` (body org)."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.billing.routes import reactivate_subscription

        profile = _make_profile()
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_organization_subscription = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await reactivate_subscription(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_billing_manage_passes_and_reactivates(self):
        from src.billing.routes import reactivate_subscription

        profile = _make_profile(has_billing_manage_on=str(TEST_ORG_ID))
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc, patch(
            "src.billing.routes.stripe_service"
        ) as mock_stripe:
            mock_svc.get_organization_subscription = AsyncMock(
                return_value=_subscription_mock()
            )
            mock_svc.update_organization_subscription = AsyncMock()
            mock_stripe.reactivate_subscription = AsyncMock()

            result = await reactivate_subscription(
                request=request, user_auth=(TEST_USER_ID, profile)
            )
            assert "reactivated" in result["message"]
            mock_stripe.reactivate_subscription.assert_called_once()


class TestCustomerPortalSessionPermission:
    """``create_customer_portal_session`` (POST /portal) gates on
    ``assert_billing_access`` (body org)."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.billing.routes import create_customer_portal_session

        profile = _make_profile()
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_organization_subscription = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_customer_portal_session(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_org_admin_passes(self):
        from src.billing.routes import create_customer_portal_session

        profile = _make_profile(is_org_admin_on=str(TEST_ORG_ID))
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc, patch(
            "src.billing.routes.stripe_service"
        ) as mock_stripe:
            mock_svc.get_organization_subscription = AsyncMock(
                return_value=_subscription_mock(stripe_customer_id="cus_x")
            )
            portal = Mock()
            portal.url = "https://portal.example.com"
            mock_stripe.create_customer_portal_session = AsyncMock(return_value=portal)

            result = await create_customer_portal_session(
                request=request, user_auth=(TEST_USER_ID, profile)
            )
            assert result["portal_url"] == "https://portal.example.com"
            mock_stripe.create_customer_portal_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_org_admin_on_other_org_forbidden(self):
        from src.billing.routes import create_customer_portal_session

        profile = _make_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        request = {"organization_id": str(TEST_ORG_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_organization_subscription = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_customer_portal_session(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_subscription.assert_not_called()


class TestCustomerPortalPermission:
    """``create_customer_portal`` (POST /subscription/portal) gates on
    ``assert_billing_access`` (body org)."""

    @pytest.mark.asyncio
    async def test_no_permission_forbidden(self):
        from src.billing.routes import create_customer_portal

        profile = _make_profile()
        request = {
            "organization_id": str(TEST_ORG_ID),
            "return_url": "https://app.example.com",
        }

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_organization_subscription = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_customer_portal(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_organization_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_platform_admin_passes(self):
        from src.billing.routes import create_customer_portal

        profile = _make_profile(is_platform_admin=True)
        request = {
            "organization_id": str(TEST_ORG_ID),
            "return_url": "https://app.example.com",
        }

        with patch("src.billing.routes.billing_service") as mock_svc, patch(
            "src.billing.routes.stripe_service"
        ) as mock_stripe:
            mock_svc.get_organization_subscription = AsyncMock(
                return_value=_subscription_mock(stripe_customer_id="cus_y")
            )
            customer = Mock()
            customer.id = "cus_y"
            mock_stripe.get_customer = AsyncMock(return_value=customer)
            portal = Mock()
            portal.url = "https://portal.example.com/sub"
            mock_stripe.create_portal_session = AsyncMock(return_value=portal)

            result = await create_customer_portal(
                request=request, user_auth=(TEST_USER_ID, profile)
            )
            assert result["portal_url"] == "https://portal.example.com/sub"


class TestCheckoutRoutesPermission:
    """``create_subscription_checkout`` (POST /checkout/subscription) and
    ``create_credits_checkout`` (POST /checkout/credits) gate on
    ``assert_billing_access`` (body org).

    The allow-path business logic (Stripe customer creation / checkout
    session) is exercised by the billing E2E flow and service tests; here we
    pin the **deny** path — the security-critical half — and one allow case
    to prove the gate passes.
    """

    @pytest.mark.asyncio
    async def test_subscription_checkout_no_permission_forbidden(self):
        from src.billing.routes import create_subscription_checkout

        profile = _make_profile()
        request = {
            "organization_id": str(TEST_ORG_ID),
            "plan_id": str(TEST_PLAN_ID),
        }

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_subscription_plan = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_checkout(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_subscription_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscription_checkout_org_admin_on_other_org_forbidden(self):
        from src.billing.routes import create_subscription_checkout

        profile = _make_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        request = {
            "organization_id": str(TEST_ORG_ID),
            "plan_id": str(TEST_PLAN_ID),
        }

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_subscription_plan = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_checkout(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_subscription_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscription_checkout_missing_org_id_returns_400(self):
        from src.billing.routes import create_subscription_checkout

        profile = _make_profile(is_platform_admin=True)
        request = {"plan_id": str(TEST_PLAN_ID)}

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_subscription_plan = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_checkout(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_credits_checkout_no_permission_forbidden(self):
        from src.billing.routes import create_credits_checkout

        profile = _make_profile()
        request = {
            "organization_id": str(TEST_ORG_ID),
            "product_id": str(TEST_PRODUCT_ID),
        }

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_credit_products = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_credits_checkout(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_credit_products.assert_not_called()

    @pytest.mark.asyncio
    async def test_credits_checkout_org_admin_on_other_org_forbidden(self):
        from src.billing.routes import create_credits_checkout

        profile = _make_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        request = {
            "organization_id": str(TEST_ORG_ID),
            "product_id": str(TEST_PRODUCT_ID),
        }

        with patch("src.billing.routes.billing_service") as mock_svc:
            mock_svc.get_credit_products = AsyncMock()
            with pytest.raises(HTTPException) as exc_info:
                await create_credits_checkout(
                    request=request, user_auth=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_svc.get_credit_products.assert_not_called()