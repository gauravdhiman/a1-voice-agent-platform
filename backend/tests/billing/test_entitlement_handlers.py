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
        effective, is_unlimited = parse_entitlement_value({"type": "integer", "value": 5})
        assert effective == 5
        assert is_unlimited is False

    def test_boolean(self):
        effective, is_unlimited = parse_entitlement_value({"type": "boolean", "value": True})
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
