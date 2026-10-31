"""
Tests for plan-version entitlements and limit enforcement.

Follows red-green TDD: these tests define Phase 1 behavior before/alongside
implementation in ``src.billing.entitlement_service``.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.billing.entitlement_models import (
    EntitlementDenied,
    EntitlementKind,
    EntitlementValueType,
    LimitCheckResult,
)
from src.billing.models import SubscriptionStatus


@pytest.fixture(autouse=True)
def _mock_plan_migration_lookup():
    """Entitlement tests do not exercise migration joins on the global singleton."""
    with patch(
        "src.billing.entitlement_service.plan_migration_service.get_active_migration_for_organization",
        new_callable=AsyncMock,
        return_value=None,
    ):
        yield


@pytest.fixture
def entitlement_service(mock_supabase_client):
    """EntitlementService with mocked Supabase."""
    from src.billing.entitlement_service import EntitlementService

    service = EntitlementService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def plan_version_id():
    return uuid4()


@pytest.fixture
def free_plan_version_id():
    return uuid4()


@pytest.fixture
def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _subscription_row(
    org_id,
    plan_version_id,
    *,
    status="active",
    cancel_at_period_end=False,
    period_end=None,
):
    end = period_end or (datetime.now(timezone.utc) + timedelta(days=30))
    return {
        "id": str(uuid4()),
        "organization_id": str(org_id),
        "subscription_plan_id": None,
        "plan_version_id": str(plan_version_id),
        "stripe_subscription_id": "sub_test",
        "stripe_customer_id": "cus_test",
        "status": status,
        "current_period_start": datetime.now(timezone.utc).isoformat(),
        "current_period_end": end.isoformat(),
        "trial_start": None,
        "trial_end": None,
        "cancel_at_period_end": cancel_at_period_end,
        "cancelled_at": None,
        "metadata": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _plan_version_row(plan_version_id, product_slug="starter", version_number=1):
    return {
        "id": str(plan_version_id),
        "plan_product_id": str(uuid4()),
        "version_number": version_number,
        "status": "published",
        "display_label": "Starter v1",
        "price_amount_cents": 7900,
        "currency": "USD",
        "billing_interval": "monthly",
        "trial_period_days": None,
        "stripe_product_id": "prod_test",
        "stripe_price_id": "price_test",
        "is_current_for_signup": True,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "legacy_subscription_plan_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "plan_products": {"slug": product_slug, "display_name": "Starter"},
    }


def _entitlement_row(plan_version_id, key, value):
    return {
        "id": str(uuid4()),
        "plan_version_id": str(plan_version_id),
        "entitlement_key": key,
        "value": value,
    }


def _definition_row(key, kind, value_type, handler, default_absent=None):
    row = {
        "key": key,
        "kind": kind,
        "display_name": key.replace("_", " ").title(),
        "value_type": value_type,
        "unit": "count",
        "validation_schema": {},
        "enforcement_handler": handler,
        "default_enforcement": "hard",
        "default_when_absent": default_absent,
        "is_active": True,
        "description": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return row


def _configure_supabase_chain(mock_supabase_client, table_responses):
    """Return configured table mocks keyed by table name."""

    def table_side_effect(name):
        mock = MagicMock()
        mock.select.return_value = mock
        mock.eq.return_value = mock
        mock.single.return_value = mock
        mock.limit.return_value = mock
        mock.order.return_value = mock
        response = MagicMock()
        response.data = table_responses.get(name, [])
        mock.execute.return_value = response
        return mock

    mock_supabase_client.table.side_effect = table_side_effect


class TestEntitlementServiceResolve:
    """Resolve org entitlements from bound plan version."""

    @pytest.mark.asyncio
    async def test_resolve_active_subscription_with_max_agents(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """Active sub resolves sparse limits from plan version."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id,
                        "max_agents",
                        {"type": "integer", "value": 1},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                        default_absent={"type": "integer", "value": 0},
                    )
                ],
            },
        )

        result = await entitlement_service.get_org_entitlements(org_id)

        assert result.plan_product_slug == "starter"
        assert result.plan_version_number == 1
        assert result.limits["max_agents"].effective_value == 1
        assert result.cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_resolve_pending_cancel_keeps_full_entitlements(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """cancel_at_period_end=true while active — still full plan (P9)."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(
                        org_id,
                        plan_version_id,
                        cancel_at_period_end=True,
                    )
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id,
                        "max_agents",
                        {"type": "integer", "value": 5},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                    )
                ],
            },
        )

        result = await entitlement_service.get_org_entitlements(org_id)

        assert result.cancel_at_period_end is True
        assert result.is_entitled is True
        assert result.limits["max_agents"].effective_value == 5

    @pytest.mark.asyncio
    async def test_resolve_cancelled_subscription_uses_free_plan(
        self,
        entitlement_service,
        mock_supabase_client,
        org_id,
        plan_version_id,
        free_plan_version_id,
    ):
        """Cancelled sub falls back to default free plan version."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(
                        org_id,
                        plan_version_id,
                        status=SubscriptionStatus.CANCELLED.value,
                    )
                ],
                "plan_versions": [
                    _plan_version_row(
                        free_plan_version_id, product_slug="free", version_number=1
                    ),
                ],
                "plan_version_entitlements": [
                    _entitlement_row(
                        free_plan_version_id,
                        "max_agents",
                        {"type": "integer", "value": 0},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                        default_absent={"type": "integer", "value": 0},
                    )
                ],
            },
        )

        entitlement_service._free_plan_version_id = free_plan_version_id

        result = await entitlement_service.get_org_entitlements(org_id)

        assert result.is_entitled is False
        assert result.plan_product_slug == "free"
        assert result.limits["max_agents"].effective_value is None
        assert result.limits["max_agents"].is_unlimited is True

    @pytest.mark.asyncio
    async def test_no_subscription_uses_free_plan(
        self,
        entitlement_service,
        mock_supabase_client,
        org_id,
        free_plan_version_id,
    ):
        """Org without subscription gets free tier."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [],
                "plan_versions": [
                    _plan_version_row(
                        free_plan_version_id, product_slug="free", version_number=1
                    ),
                ],
                "plan_version_entitlements": [],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                        default_absent={"type": "unlimited"},
                    )
                ],
            },
        )

        entitlement_service._free_plan_version_id = free_plan_version_id

        result = await entitlement_service.get_org_entitlements(org_id)

        assert result.plan_product_slug == "free"
        assert result.is_entitled is False
        assert result.limits["max_agents"].effective_value is None
        assert result.limits["max_agents"].is_unlimited is True


class TestEntitlementServiceCheckLimit:
    """Limit checks for max_agents."""

    @pytest.mark.asyncio
    async def test_check_max_agents_allowed_under_limit(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """Creating agent allowed when count < limit."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id,
                        "max_agents",
                        {"type": "integer", "value": 3},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                    )
                ],
                "voice_agents": [{"id": str(uuid4())}, {"id": str(uuid4())}],
            },
        )

        result = await entitlement_service.check_limit(
            org_id, "max_agents", increment=1
        )

        assert result.allowed is True
        assert result.current == 2
        assert result.limit == 3

    @pytest.mark.asyncio
    async def test_check_max_agents_denied_at_limit(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """Creating agent denied when at limit."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id,
                        "max_agents",
                        {"type": "integer", "value": 1},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                    )
                ],
                "voice_agents": [{"id": str(uuid4())}],
            },
        )

        result = await entitlement_service.check_limit(
            org_id, "max_agents", increment=1
        )

        assert result.allowed is False
        assert result.code == "MAX_AGENTS"
        assert result.current == 1
        assert result.limit == 1

    @pytest.mark.asyncio
    async def test_check_unlimited_agents_always_allowed(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """Unlimited max_agents never blocks."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id, "max_agents", {"type": "unlimited"}
                    ),
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.UNLIMITED.value,
                        "limit.max_count",
                    )
                ],
                "voice_agents": [{"id": str(uuid4())} for _ in range(100)],
            },
        )

        result = await entitlement_service.check_limit(
            org_id, "max_agents", increment=1
        )

        assert result.allowed is True
        assert result.limit is None

    @pytest.mark.asyncio
    async def test_assert_limit_raises_entitlement_denied(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """assert_limit raises EntitlementDenied when blocked."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id,
                        "max_agents",
                        {"type": "integer", "value": 1},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "max_agents",
                        EntitlementKind.LIMIT.value,
                        EntitlementValueType.INTEGER.value,
                        "limit.max_count",
                    )
                ],
                "voice_agents": [{"id": str(uuid4())}],
            },
        )

        with pytest.raises(EntitlementDenied) as exc_info:
            await entitlement_service.assert_limit(org_id, "max_agents", increment=1)

        assert exc_info.value.code == "MAX_AGENTS"


class TestEntitlementServiceFeatures:
    """Feature flag checks."""

    @pytest.mark.asyncio
    async def test_check_feature_enabled(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """Feature present and true returns True."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [
                    _entitlement_row(
                        plan_version_id,
                        "payg_enabled",
                        {"type": "boolean", "value": True},
                    )
                ],
                "entitlement_definitions": [
                    _definition_row(
                        "payg_enabled",
                        EntitlementKind.FEATURE.value,
                        EntitlementValueType.BOOLEAN.value,
                        "feature.flag",
                        default_absent={"type": "boolean", "value": False},
                    )
                ],
            },
        )

        assert await entitlement_service.check_feature(org_id, "payg_enabled") is True

    @pytest.mark.asyncio
    async def test_check_feature_absent_uses_default(
        self, entitlement_service, mock_supabase_client, org_id, plan_version_id
    ):
        """Missing feature on version uses default_when_absent."""
        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [
                    _subscription_row(org_id, plan_version_id)
                ],
                "plan_versions": [_plan_version_row(plan_version_id)],
                "plan_version_entitlements": [],
                "entitlement_definitions": [
                    _definition_row(
                        "payg_enabled",
                        EntitlementKind.FEATURE.value,
                        EntitlementValueType.BOOLEAN.value,
                        "feature.flag",
                        default_absent={"type": "boolean", "value": False},
                    )
                ],
            },
        )

        assert await entitlement_service.check_feature(org_id, "payg_enabled") is False
