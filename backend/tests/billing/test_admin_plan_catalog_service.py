"""
Tests for AdminPlanCatalogService draft CRUD and entitlement catalog updates.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.billing.admin_plan_models import (
    EntitlementDefinitionUpdate,
    PlanProductCreate,
    PlanVersionDraftCreate,
    PlanVersionDraftUpdate,
    PlanVersionEntitlementInput,
)
from src.billing.entitlement_models import (
    EntitlementKind,
    EntitlementValueType,
)
from src.billing.plan_version_models import PlanVersionStatus


@pytest.fixture
def catalog_service(mock_supabase_client):
    """AdminPlanCatalogService with mocked Supabase."""
    from src.billing.admin_plan_catalog_service import AdminPlanCatalogService

    service = AdminPlanCatalogService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def product_id():
    return uuid4()


@pytest.fixture
def version_id():
    return uuid4()


def _product_row(product_id, slug="pro"):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(product_id),
        "slug": slug,
        "display_name": "Pro",
        "description": "Pro plan",
        "sort_order": 10,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


def _version_row(version_id, product_id, *, status=PlanVersionStatus.DRAFT.value, version_number=1):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(version_id),
        "plan_product_id": str(product_id),
        "version_number": version_number,
        "status": status,
        "display_label": f"v{version_number}",
        "price_amount_cents": 2900,
        "currency": "USD",
        "billing_interval": "monthly",
        "trial_period_days": None,
        "stripe_product_id": None,
        "stripe_price_id": None,
        "is_current_for_signup": False,
        "published_at": None,
        "legacy_subscription_plan_id": None,
        "created_at": now,
        "updated_at": now,
    }


def _entitlement_def_row(key="max_agents"):
    return {
        "key": key,
        "kind": EntitlementKind.LIMIT.value,
        "display_name": "Maximum agents",
        "value_type": EntitlementValueType.INTEGER.value,
        "unit": "count",
        "validation_schema": {},
        "enforcement_handler": "limit.max_count",
        "default_enforcement": "hard",
        "default_when_absent": {"type": "integer", "value": 0},
        "is_active": True,
        "description": "Max agents",
    }


class TestAdminPlanCatalogService:
    """Unit tests for catalog service methods."""

    @pytest.mark.asyncio
    async def test_list_entitlement_definitions(self, catalog_service, mock_supabase_client):
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[_entitlement_def_row()]
        )
        result = await catalog_service.list_entitlement_definitions()
        assert len(result) == 1
        assert result[0].key == "max_agents"

    @pytest.mark.asyncio
    async def test_update_entitlement_definition(self, catalog_service, mock_supabase_client):
        updated = _entitlement_def_row()
        updated["display_name"] = "Agents cap"
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[updated]
        )
        result = await catalog_service.update_entitlement_definition(
            "max_agents",
            EntitlementDefinitionUpdate(display_name="Agents cap"),
        )
        assert result.display_name == "Agents cap"

    @pytest.mark.asyncio
    async def test_update_entitlement_definition_empty_fields_raises(
        self, catalog_service
    ):
        with pytest.raises(ValueError, match="No fields"):
            await catalog_service.update_entitlement_definition(
                "max_agents", EntitlementDefinitionUpdate()
            )

    @pytest.mark.asyncio
    async def test_create_plan_product(self, catalog_service, mock_supabase_client, product_id):
        row = _product_row(product_id)
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        result = await catalog_service.create_plan_product(
            PlanProductCreate(slug="Pro", display_name="Pro Plan")
        )
        assert result.slug == "pro"

    @pytest.mark.asyncio
    async def test_create_draft_version_increments_version_number(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import PlanVersionDetail

        new_row = _version_row(version_id, product_id, version_number=3)

        async def fake_get_plan_version(_vid):
            return PlanVersionDetail(**new_row, entitlements=[])

        with patch.object(
            catalog_service, "_get_product", return_value=_product_row(product_id)
        ), patch.object(
            catalog_service, "_next_version_number", return_value=3
        ), patch.object(
            catalog_service, "_replace_entitlements", return_value=None
        ), patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ):
            catalog_service.supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[new_row]
            )
            result = await catalog_service.create_draft_version(
                product_id,
                PlanVersionDraftCreate(display_label="Pro v3", price_amount_cents=5900),
            )
        assert result.version_number == 3

    @pytest.mark.asyncio
    async def test_update_draft_version_rejects_published(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import PlanVersionDetail

        published = _version_row(
            version_id, product_id, status=PlanVersionStatus.PUBLISHED.value
        )

        async def fake_get_plan_version(_vid):
            return PlanVersionDetail(**published, entitlements=[])

        with patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ):
            with pytest.raises(ValueError, match="not draft"):
                await catalog_service.update_draft_version(
                    version_id, PlanVersionDraftUpdate(display_label="Nope")
                )

    @pytest.mark.asyncio
    async def test_update_draft_version_replaces_entitlements(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import (
            PlanVersionDetail,
            PlanVersionEntitlement,
        )

        draft = _version_row(version_id, product_id)
        entitlement_id = uuid4()
        updated_entitlements = [
            PlanVersionEntitlement(
                id=entitlement_id,
                entitlement_key="max_agents",
                value={"type": "integer", "value": 5},
            )
        ]

        call_count = {"n": 0}

        async def fake_get_plan_version(_vid):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return PlanVersionDetail(**draft, entitlements=[])
            return PlanVersionDetail(**draft, entitlements=updated_entitlements)

        with patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ), patch.object(
            catalog_service, "_replace_entitlements", return_value=None
        ):
            catalog_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[draft]
            )
            result = await catalog_service.update_draft_version(
                version_id,
                PlanVersionDraftUpdate(
                    entitlements=[
                        PlanVersionEntitlementInput(
                            entitlement_key="max_agents",
                            value={"type": "integer", "value": 5},
                        )
                    ]
                ),
            )
        assert len(result.entitlements) == 1
        assert result.entitlements[0].entitlement_key == "max_agents"
