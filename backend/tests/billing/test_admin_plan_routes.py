"""Tests for platform-admin plan catalog API routes (Phase 4)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.billing.entitlement_models import EntitlementKind, EntitlementValueType
from src.billing.plan_version_models import PlanVersionStatus

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000004")
TEST_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000501")
TEST_VERSION_ID = UUID("00000000-0000-0000-0000-000000000502")


def _profile(is_admin: bool) -> Mock:
    p = Mock()
    p.has_role = Mock(return_value=is_admin)
    return p


def _entitlement_definition():
    from src.billing.entitlement_models import EntitlementDefinition

    return EntitlementDefinition(
        key="max_agents",
        kind=EntitlementKind.LIMIT,
        display_name="Maximum agents",
        value_type=EntitlementValueType.INTEGER,
        unit="count",
        enforcement_handler="limit.max_count",
        description="Max agents",
    )


def _plan_version_detail():
    from src.billing.admin_plan_models import PlanVersionDetail

    now = datetime.now(timezone.utc)
    return PlanVersionDetail(
        id=TEST_VERSION_ID,
        plan_product_id=TEST_PRODUCT_ID,
        version_number=1,
        status=PlanVersionStatus.DRAFT,
        display_label="Pro v1",
        price_amount_cents=2900,
        currency="USD",
        billing_interval="monthly",
        trial_period_days=None,
        stripe_product_id=None,
        stripe_price_id=None,
        is_current_for_signup=False,
        published_at=None,
        legacy_subscription_plan_id=None,
        entitlements=[],
        created_at=now,
        updated_at=now,
    )


class TestAdminPlanRoutesAuthz:
    """Authorization tests for admin plan catalog routes."""

    @pytest.mark.asyncio
    async def test_list_entitlement_definitions_requires_platform_admin(self):
        from src.billing.admin_plan_routes import list_entitlement_definitions

        with pytest.raises(HTTPException) as exc_info:
            await list_entitlement_definitions(
                active_only=False,
                user_auth=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_entitlement_definitions_succeeds_for_admin(self):
        from src.billing.admin_plan_routes import list_entitlement_definitions

        with patch(
            "src.billing.admin_plan_routes.admin_plan_catalog_service"
        ) as mock_svc:
            mock_svc.list_entitlement_definitions = AsyncMock(
                return_value=[_entitlement_definition()]
            )
            result = await list_entitlement_definitions(
                active_only=False,
                user_auth=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result[0].key == "max_agents"

    @pytest.mark.asyncio
    async def test_list_credit_events_requires_platform_admin(self):
        from src.billing.admin_plan_routes import list_credit_events

        with pytest.raises(HTTPException) as exc_info:
            await list_credit_events(
                user_auth=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_credit_event_succeeds_for_admin(self):
        from src.billing.admin_plan_models import CreditEventAdminUpdate
        from src.billing.admin_plan_routes import update_credit_event
        from src.billing.models import CreditEvent

        event = CreditEvent(
            id=uuid4(),
            name="voice_call_minute",
            description="Voice minute",
            credit_cost=0,
            category="voice",
            meter_type="duration",
            billing_unit="minute",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with patch(
            "src.billing.admin_plan_routes.admin_plan_catalog_service"
        ) as mock_svc:
            mock_svc.update_credit_event = AsyncMock(return_value=event)
            result = await update_credit_event(
                name="voice_call_minute",
                body=CreditEventAdminUpdate(credit_cost=0),
                user_auth=(TEST_USER_ID, _profile(is_admin=True)),
            )

        assert result.name == "voice_call_minute"

    @pytest.mark.asyncio
    async def test_create_draft_version_returns_400_on_value_error(self):
        from src.billing.admin_plan_models import PlanVersionDraftCreate
        from src.billing.admin_plan_routes import create_draft_plan_version

        with patch(
            "src.billing.admin_plan_routes.admin_plan_catalog_service"
        ) as mock_svc:
            mock_svc.create_draft_version = AsyncMock(
                side_effect=ValueError("Plan product not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await create_draft_plan_version(
                    product_id=TEST_PRODUCT_ID,
                    body=PlanVersionDraftCreate(price_amount_cents=1000),
                    user_auth=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_plan_version_returns_404_when_missing(self):
        from src.billing.admin_plan_routes import get_plan_version

        with patch(
            "src.billing.admin_plan_routes.admin_plan_catalog_service"
        ) as mock_svc:
            mock_svc.get_plan_version = AsyncMock(
                side_effect=ValueError("Plan version not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await get_plan_version(
                    plan_version_id=TEST_VERSION_ID,
                    user_auth=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_draft_plan_version_returns_400_on_value_error(self):
        from src.billing.admin_plan_routes import delete_draft_plan_version

        with patch(
            "src.billing.admin_plan_routes.admin_plan_catalog_service"
        ) as mock_svc:
            mock_svc.delete_draft_version = AsyncMock(
                side_effect=ValueError("Plan version is not draft")
            )
            with pytest.raises(HTTPException) as exc_info:
                await delete_draft_plan_version(
                    plan_version_id=TEST_VERSION_ID,
                    user_auth=(TEST_USER_ID, _profile(is_admin=True)),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_clone_plan_version_succeeds_for_admin(self):
        from src.billing.admin_plan_models import PlanVersionCloneRequest
        from src.billing.admin_plan_routes import clone_plan_version

        detail = _plan_version_detail()
        detail.version_number = 2

        with patch(
            "src.billing.admin_plan_routes.admin_plan_catalog_service"
        ) as mock_svc:
            mock_svc.clone_plan_version = AsyncMock(return_value=detail)
            result = await clone_plan_version(
                plan_version_id=TEST_VERSION_ID,
                body=PlanVersionCloneRequest(display_label="Pro v2"),
                user_auth=(TEST_USER_ID, _profile(is_admin=True)),
            )
        assert result.version_number == 2

    @pytest.mark.asyncio
    async def test_publish_plan_version_still_requires_admin(self):
        from src.billing.admin_plan_routes import publish_plan_version
        from src.billing.plan_version_models import PlanVersionPublishRequest

        with pytest.raises(HTTPException) as exc_info:
            await publish_plan_version(
                plan_version_id=TEST_VERSION_ID,
                request=PlanVersionPublishRequest(),
                user_auth=(TEST_USER_ID, _profile(is_admin=False)),
            )
        assert exc_info.value.status_code == 403
