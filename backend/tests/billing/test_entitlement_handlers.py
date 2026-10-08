"""
Unit tests for entitlement handler registry and value parsing.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.billing.entitlement_handlers import (
    ConcurrentCallsHandler,
    FeatureFlagHandler,
    MaxAgentsHandler,
    MaxPhoneNumbersHandler,
    get_handler,
    parse_entitlement_value,
)
from src.billing.entitlement_models import (
    EntitlementKind,
    OrgEntitlements,
    ResolvedEntitlement,
)


class TestParseEntitlementValue:
    """Tests for JSONB value parsing."""

    def test_unlimited(self):
        effective, is_unlimited = parse_entitlement_value({"type": "unlimited"})
        assert is_unlimited is True
        assert effective is None

    def test_integer(self):
        effective, is_unlimited = parse_entitlement_value(
            {"type": "integer", "value": 5}
        )
        assert effective == 5
        assert is_unlimited is False

    @pytest.mark.parametrize("value", [0, -1])
    def test_non_positive_max_agents_are_unlimited(self, value):
        effective, is_unlimited = parse_entitlement_value(
            {"type": "integer", "value": value}, entitlement_key="max_agents"
        )
        assert effective is None
        assert is_unlimited is True

    def test_non_positive_other_integer_entitlement_stays_literal(self):
        effective, is_unlimited = parse_entitlement_value(
            {"type": "integer", "value": 0}, entitlement_key="max_phone_numbers"
        )
        assert effective == 0
        assert is_unlimited is False

    def test_boolean(self):
        effective, is_unlimited = parse_entitlement_value(
            {"type": "boolean", "value": True}
        )
        assert effective is True


class TestGetHandler:
    """Handler registry resolution."""

    def test_unknown_handler_raises(self):
        with pytest.raises(ValueError, match="No entitlement handler"):
            get_handler("unknown.handler", "max_agents")

    def test_max_agents_uses_specialized_handler(self):
        handler = get_handler("limit.max_count", "max_agents")
        assert isinstance(handler, MaxAgentsHandler)

    def test_max_concurrent_calls_uses_concurrent_handler(self):
        handler = get_handler("limit.max_count", "max_concurrent_calls")
        assert isinstance(handler, ConcurrentCallsHandler)


class TestFeatureFlagHandler:
    """Boolean feature gate handler."""

    @pytest.mark.asyncio
    async def test_disabled_feature_returns_not_allowed(self):
        handler = FeatureFlagHandler()
        org_id = uuid4()
        entitlements = OrgEntitlements(
            organization_id=org_id,
            plan_version_id=uuid4(),
            plan_product_slug="starter",
            plan_version_number=1,
            is_entitled=True,
        )
        resolved = ResolvedEntitlement(
            key="payg_enabled",
            kind=EntitlementKind.FEATURE,
            assigned=True,
            raw_value={"type": "boolean", "value": False},
            effective_value=False,
        )
        result = await handler.check_limit(org_id, entitlements, resolved)
        assert result.allowed is False
        assert "not enabled" in (result.message or "")


class TestMaxAgentsHandlerEdgeCases:
    """Edge cases for agent count limits."""

    @pytest.mark.asyncio
    async def test_no_supabase_client_returns_zero_count(self, monkeypatch):
        handler = MaxAgentsHandler(supabase=None)
        org_id = uuid4()
        entitlements = OrgEntitlements(
            organization_id=org_id,
            plan_version_id=uuid4(),
            plan_product_slug="starter",
            plan_version_number=1,
            is_entitled=True,
        )
        resolved = ResolvedEntitlement(
            key="max_agents",
            kind=EntitlementKind.LIMIT,
            assigned=True,
            raw_value={"type": "integer", "value": 1},
            effective_value=1,
        )
        monkeypatch.setattr(
            "src.billing.entitlement_handlers.supabase_config",
            MagicMock(client=None),
        )
        result = await handler.check_limit(org_id, entitlements, resolved, increment=1)
        assert result.current == 0
        assert result.allowed is True


@pytest.mark.asyncio
async def test_phone_number_limit_counts_non_terminal_platform_rows_only():
    """Only platform-managed lifecycle rows consume plan phone capacity."""
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.in_.return_value = table
    table.execute.return_value = MagicMock(count=3, data=[{}, {}, {}])
    client = MagicMock()
    client.table.return_value = table
    handler = MaxPhoneNumbersHandler(supabase=client)
    org_id = uuid4()
    entitlements = OrgEntitlements(
        organization_id=org_id,
        plan_version_id=uuid4(),
        plan_product_slug="starter",
        plan_version_number=1,
        is_entitled=True,
    )
    resolved = ResolvedEntitlement(
        key="max_phone_numbers",
        kind=EntitlementKind.LIMIT,
        assigned=True,
        raw_value={"type": "integer", "value": 3},
        effective_value=3,
    )

    result = await handler.check_limit(org_id, entitlements, resolved, increment=1)

    assert result.allowed is False
    table.eq.assert_any_call("management_mode", "platform_managed")
    table.in_.assert_called_once_with(
        "status",
        [
            "provisioning",
            "purchased",
            "active",
            "verification_required",
            "release_pending",
        ],
    )
