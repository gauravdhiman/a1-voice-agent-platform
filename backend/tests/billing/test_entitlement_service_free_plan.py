"""
Tests for free-plan resolution via database lookup in EntitlementService.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def entitlement_service(mock_supabase_client):
    from src.billing.entitlement_service import EntitlementService

    service = EntitlementService()
    service.supabase = mock_supabase_client
    return service


def _configure_supabase_chain(mock_supabase_client, table_responses):
    def table_side_effect(name):
        mock = MagicMock()
        mock.select.return_value = mock
        mock.eq.return_value = mock
        mock.limit.return_value = mock
        mock.order.return_value = mock
        response = MagicMock()
        response.data = table_responses.get(name, [])
        mock.execute.return_value = response
        return mock

    mock_supabase_client.table.side_effect = table_side_effect


class TestFreePlanResolution:
    """Database lookup for default free plan version."""

    @pytest.mark.asyncio
    async def test_resolve_free_plan_version_from_database(
        self, entitlement_service, mock_supabase_client
    ):
        free_version_id = uuid4()
        org_id = uuid4()

        _configure_supabase_chain(
            mock_supabase_client,
            {
                "organization_subscriptions": [],
                "plan_versions": [
                    {
                        "id": str(free_version_id),
                        "plan_product_id": str(uuid4()),
                        "version_number": 1,
                        "status": "published",
                        "display_label": "Free v1",
                        "price_amount_cents": 0,
                        "currency": "USD",
                        "billing_interval": "monthly",
                        "trial_period_days": None,
                        "stripe_product_id": None,
                        "stripe_price_id": None,
                        "is_current_for_signup": True,
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "legacy_subscription_plan_id": None,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "plan_products": {"slug": "free", "display_name": "Free"},
                    }
                ],
                "plan_version_entitlements": [
                    {
                        "id": str(uuid4()),
                        "plan_version_id": str(free_version_id),
                        "entitlement_key": "max_agents",
                        "value": {"type": "integer", "value": 0},
                    }
                ],
                "entitlement_definitions": [
                    {
                        "key": "max_agents",
                        "kind": "limit",
                        "display_name": "Maximum agents",
                        "value_type": "integer",
                        "unit": "count",
                        "validation_schema": {},
                        "enforcement_handler": "limit.max_count",
                        "default_enforcement": "hard",
                        "default_when_absent": {"type": "integer", "value": 0},
                        "is_active": True,
                        "description": None,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            },
        )

        result = await entitlement_service.get_org_entitlements(org_id)

        assert result.plan_product_slug == "free"
        assert entitlement_service._free_plan_version_id == free_version_id
