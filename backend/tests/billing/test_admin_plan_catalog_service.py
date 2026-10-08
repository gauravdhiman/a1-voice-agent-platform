"""
Tests for AdminPlanCatalogService draft CRUD and entitlement catalog updates.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.billing.admin_plan_models import (
    CreditEventAdminUpdate,
    EntitlementDefinitionUpdate,
    PlanProductCreate,
    PlanVersionDraftCreate,
    PlanVersionDraftUpdate,
    PlanVersionEntitlementInput,
)
from src.billing.entitlement_models import EntitlementKind, EntitlementValueType
from src.billing.plan_version_models import (
    BillingMode,
    CreditGrantPolicy,
    PlanVersionStatus,
)


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


def _version_row(
    version_id,
    product_id,
    *,
    status=PlanVersionStatus.DRAFT.value,
    version_number=1,
    billing_mode=BillingMode.PAID.value,
    credit_grant_policy=CreditGrantPolicy.RECURRING.value,
):
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
        "billing_mode": billing_mode,
        "credit_grant_policy": credit_grant_policy,
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


def _credit_event_row(name="voice_call_minute"):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid4()),
        "name": name,
        "description": "One connected voice-call minute",
        "credit_cost": 10,
        "category": "voice",
        "is_active": True,
        "metadata": None,
        "meter_type": "duration",
        "billing_unit": "minute",
        "created_at": now,
        "updated_at": now,
    }


class TestAdminPlanCatalogService:
    """Unit tests for catalog service methods."""

    @pytest.mark.asyncio
    async def test_list_entitlement_definitions(
        self, catalog_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.execute.return_value = MagicMock(
            data=[_entitlement_def_row()]
        )
        result = await catalog_service.list_entitlement_definitions()
        assert len(result) == 1
        assert result[0].key == "max_agents"

    def test_free_draft_contract_allows_optional_stripe_metadata(self):
        """A free draft is explicit and does not require Stripe identifiers."""
        draft = PlanVersionDraftCreate(
            billing_mode=BillingMode.FREE,
            credit_grant_policy=CreditGrantPolicy.ONE_TIME,
            price_amount_cents=0,
            stripe_product_id=None,
        )

        assert draft.billing_mode is BillingMode.FREE
        assert draft.credit_grant_policy is CreditGrantPolicy.ONE_TIME
        assert draft.stripe_product_id is None

    @pytest.mark.asyncio
    async def test_update_entitlement_definition(
        self, catalog_service, mock_supabase_client
    ):
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
    async def test_list_credit_events_returns_only_system_pricing_configuration(
        self, catalog_service, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.select.return_value.in_.return_value.order.return_value.order.return_value.execute.return_value = MagicMock(
            data=[_credit_event_row()]
        )

        result = await catalog_service.list_credit_events()

        assert result[0].name == "voice_call_minute"
        assert result[0].billing_unit.value == "minute"

    @pytest.mark.asyncio
    async def test_update_credit_event_persists_cost_without_editable_metering(
        self, catalog_service, mock_supabase_client
    ):
        updated = _credit_event_row()
        updated["credit_cost"] = 0
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated]
        )

        result = await catalog_service.update_credit_event(
            "voice_call_minute",
            CreditEventAdminUpdate(credit_cost=0),
        )

        assert result.credit_cost == 0
        mock_supabase_client.table.return_value.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_credit_event_rejects_non_system_activity(
        self, catalog_service
    ):
        with pytest.raises(
            ValueError, match="must be a supported system pricing event"
        ):
            await catalog_service.update_credit_event(
                "api_call_basic", CreditEventAdminUpdate(credit_cost=1)
            )

    @pytest.mark.asyncio
    async def test_list_plan_products_returns_version_summaries_without_entitlements(
        self, catalog_service, product_id, version_id
    ):
        """List endpoint should not load entitlement rows for each version."""
        from src.billing.admin_plan_models import PlanVersionSummary

        product_row = _product_row(product_id)
        summary = PlanVersionSummary(**_version_row(version_id, product_id))

        products_execute = MagicMock(data=[product_row])
        table_mock = MagicMock()
        table_mock.select.return_value.order.return_value.execute.return_value = (
            products_execute
        )
        catalog_service.supabase.table.return_value = table_mock

        with patch.object(
            catalog_service,
            "_list_version_summaries_for_product",
            return_value=[summary],
        ) as mock_list_summaries, patch.object(
            catalog_service,
            "_get_entitlements_for_version",
        ) as mock_get_entitlements:
            result = await catalog_service.list_plan_products()
            mock_list_summaries.assert_called_once()
            mock_get_entitlements.assert_not_called()

        assert len(result) == 1
        assert len(result[0].versions) == 1
        assert result[0].versions[0].id == version_id
        assert "entitlements" not in PlanVersionSummary.model_fields

    @pytest.mark.asyncio
    async def test_create_plan_product(
        self, catalog_service, mock_supabase_client, product_id
    ):
        from src.billing.admin_plan_models import PlanProductCreateResult

        row = _product_row(product_id)
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        with patch(
            "src.billing.admin_plan_catalog_service.stripe_service.create_product",
            new_callable=AsyncMock,
        ) as mock_stripe:
            mock_stripe.return_value = MagicMock(id="prod_auto")
            with patch.object(
                catalog_service,
                "_update_plan_product_fields",
                return_value={**row, "stripe_product_id": "prod_auto"},
            ):
                result = await catalog_service.create_plan_product(
                    PlanProductCreate(slug="Pro", display_name="Pro Plan")
                )
        assert isinstance(result, PlanProductCreateResult)
        assert result.product.slug == "pro"
        assert result.product.stripe_product_id == "prod_auto"
        assert result.stripe_auto_create_error is None

    @pytest.mark.asyncio
    async def test_create_plan_product_survives_stripe_failure(
        self, catalog_service, mock_supabase_client, product_id
    ):
        row = _product_row(product_id)
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        with patch(
            "src.billing.admin_plan_catalog_service.stripe_service.create_product",
            new_callable=AsyncMock,
            side_effect=ValueError("Stripe is not configured"),
        ):
            result = await catalog_service.create_plan_product(
                PlanProductCreate(slug="Pro", display_name="Pro Plan")
            )
        assert result.product.slug == "pro"
        assert result.stripe_auto_create_error is not None

    @pytest.mark.asyncio
    async def test_create_free_plan_product_skips_stripe_product_creation(
        self, catalog_service, mock_supabase_client, product_id
    ):
        row = _product_row(product_id, slug="free")
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[row]
        )
        with patch(
            "src.billing.admin_plan_catalog_service.stripe_service.create_product",
            new_callable=AsyncMock,
        ) as mock_stripe:
            result = await catalog_service.create_plan_product(
                PlanProductCreate(slug="free", display_name="Free")
            )

        mock_stripe.assert_not_awaited()
        assert result.product.slug == "free"
        assert result.product.stripe_product_id is None
        assert result.stripe_auto_create_error is None

    @pytest.mark.asyncio
    async def test_create_draft_version_increments_version_number(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import PlanVersionDetail

        new_row = _version_row(
            version_id,
            product_id,
            version_number=3,
            billing_mode=BillingMode.FREE.value,
        )

        async def fake_get_plan_version(_vid):
            return PlanVersionDetail(**new_row, entitlements=[])

        with patch.object(
            catalog_service,
            "_get_product",
            return_value={**_product_row(product_id), "stripe_product_id": "prod_paid"},
        ), patch.object(
            catalog_service, "_get_draft_version_for_product", return_value=None
        ), patch.object(
            catalog_service, "_next_version_number", return_value=3
        ), patch.object(
            catalog_service, "_replace_entitlements", return_value=None
        ), patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ):
            insert_execute = MagicMock(data=[new_row])
            catalog_service.supabase.table.return_value.insert.return_value.execute.return_value = (
                insert_execute
            )
            result = await catalog_service.create_draft_version(
                product_id,
                PlanVersionDraftCreate(
                    display_label="Free v3",
                    price_amount_cents=0,
                    billing_mode=BillingMode.FREE,
                    credit_grant_policy=CreditGrantPolicy.ONE_TIME,
                ),
            )
        assert result.version_number == 3
        inserted_row = (
            catalog_service.supabase.table.return_value.insert.call_args.args[0]
        )
        assert inserted_row["billing_mode"] == BillingMode.FREE.value
        assert inserted_row["credit_grant_policy"] == CreditGrantPolicy.ONE_TIME.value
        assert inserted_row["stripe_product_id"] is None

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
    async def test_switching_draft_to_free_clears_stripe_metadata(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import PlanVersionDetail

        current = {
            **_version_row(version_id, product_id),
            "stripe_product_id": "prod_paid",
            "stripe_price_id": "price_paid",
        }
        updated = {**current, "billing_mode": BillingMode.FREE.value}
        call_count = {"n": 0}

        async def fake_get_plan_version(_vid):
            call_count["n"] += 1
            row = current if call_count["n"] == 1 else updated
            return PlanVersionDetail(**row, entitlements=[])

        with patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ):
            catalog_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[updated]
            )
            await catalog_service.update_draft_version(
                version_id,
                PlanVersionDraftUpdate(billing_mode=BillingMode.FREE),
            )

        fields = catalog_service.supabase.table.return_value.update.call_args.args[0]
        assert fields["stripe_product_id"] is None
        assert fields["stripe_price_id"] is None

    @pytest.mark.asyncio
    async def test_explicit_null_clears_draft_display_label(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import PlanVersionDetail

        current = _version_row(version_id, product_id)
        updated = {**current, "display_label": None}
        call_count = {"n": 0}

        async def fake_get_plan_version(_vid):
            call_count["n"] += 1
            row = current if call_count["n"] == 1 else updated
            return PlanVersionDetail(**row, entitlements=[])

        with patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ):
            catalog_service.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[updated]
            )
            await catalog_service.update_draft_version(
                version_id, PlanVersionDraftUpdate(display_label=None)
            )

        fields = catalog_service.supabase.table.return_value.update.call_args.args[0]
        assert fields["display_label"] is None

    @pytest.mark.asyncio
    async def test_clone_preserves_credit_grant_policy(
        self, catalog_service, product_id, version_id
    ):
        """Cloning a one-time version keeps its explicit credit cadence."""
        from src.billing.admin_plan_models import PlanVersionDetail

        source = _version_row(
            version_id,
            product_id,
            credit_grant_policy=CreditGrantPolicy.ONE_TIME.value,
        )
        source_detail = PlanVersionDetail(**source, entitlements=[])
        cloned_detail = PlanVersionDetail(
            **_version_row(uuid4(), product_id), entitlements=[]
        )

        with patch.object(
            catalog_service, "get_plan_version", return_value=source_detail
        ), patch.object(
            catalog_service, "_ensure_no_existing_draft", return_value=None
        ), patch.object(
            catalog_service,
            "create_draft_version",
            return_value=cloned_detail,
        ) as create_draft:
            await catalog_service.clone_plan_version(source_detail.id)

        create_data = create_draft.call_args.args[1]
        assert create_data.credit_grant_policy is CreditGrantPolicy.ONE_TIME

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
        ), patch.object(catalog_service, "_replace_entitlements", return_value=None):
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

    @pytest.mark.asyncio
    async def test_replace_entitlements_persists_display_order(
        self, catalog_service, version_id
    ):
        """Draft entitlement replacement stores the editor's display sequence."""
        await catalog_service._replace_entitlements(
            version_id,
            [
                PlanVersionEntitlementInput(
                    entitlement_key="max_agents",
                    value={"type": "integer", "value": 5},
                ),
                PlanVersionEntitlementInput(
                    entitlement_key="payg_enabled",
                    value={"type": "boolean", "value": True},
                ),
            ],
        )

        inserted_rows = (
            catalog_service.supabase.table.return_value.insert.call_args.args[0]
        )
        assert [row["display_order"] for row in inserted_rows] == [0, 1]

    @pytest.mark.asyncio
    async def test_replace_entitlements_normalizes_nonpositive_agent_caps(
        self, catalog_service, version_id
    ):
        """Only non-positive max_agents values are serialized as unlimited."""
        await catalog_service._replace_entitlements(
            version_id,
            [
                PlanVersionEntitlementInput(
                    entitlement_key="max_agents",
                    value={"type": "integer", "value": 0},
                ),
                PlanVersionEntitlementInput(
                    entitlement_key="max_phone_numbers",
                    value={"type": "integer", "value": 0},
                ),
            ],
        )

        inserted_rows = (
            catalog_service.supabase.table.return_value.insert.call_args.args[0]
        )
        assert inserted_rows[0]["value"] == {"type": "unlimited"}
        assert inserted_rows[1]["value"] == {"type": "integer", "value": 0}

    @pytest.mark.asyncio
    async def test_reorder_published_version_changes_order_only(
        self, catalog_service, product_id, version_id
    ):
        """Published reordering updates order columns without changing values."""
        from src.billing.admin_plan_models import (
            PlanVersionDetail,
            PlanVersionEntitlement,
        )

        first_id = uuid4()
        second_id = uuid4()
        published = PlanVersionDetail(
            **_version_row(
                version_id,
                product_id,
                status=PlanVersionStatus.PUBLISHED.value,
            ),
            entitlements=[
                PlanVersionEntitlement(
                    id=first_id,
                    entitlement_key="max_agents",
                    value={"type": "integer", "value": 5},
                    display_order=0,
                ),
                PlanVersionEntitlement(
                    id=second_id,
                    entitlement_key="payg_enabled",
                    value={"type": "boolean", "value": True},
                    display_order=1,
                ),
            ],
        )

        with patch.object(catalog_service, "get_plan_version", return_value=published):
            await catalog_service.reorder_plan_version_entitlements(
                version_id, ["payg_enabled", "max_agents"]
            )

        update_calls = catalog_service.supabase.table.return_value.update.call_args_list
        assert [call.args[0] for call in update_calls] == [
            {"display_order": 0},
            {"display_order": 1},
        ]
        assert all("value" not in call.args[0] for call in update_calls)

    @pytest.mark.asyncio
    async def test_create_draft_version_rejects_second_draft(
        self, catalog_service, product_id
    ):
        with patch.object(
            catalog_service, "_get_product", return_value=_product_row(product_id)
        ), patch.object(
            catalog_service,
            "_get_draft_version_for_product",
            return_value={
                "id": str(uuid4()),
                "version_number": 2,
                "display_label": "v2",
            },
        ):
            with pytest.raises(ValueError, match="already has draft"):
                await catalog_service.create_draft_version(
                    product_id,
                    PlanVersionDraftCreate(display_label="Pro v3"),
                )

    @pytest.mark.asyncio
    async def test_delete_draft_version_removes_row(
        self, catalog_service, product_id, version_id
    ):
        from src.billing.admin_plan_models import PlanVersionDetail

        draft = _version_row(version_id, product_id)

        async def fake_get_plan_version(_vid):
            return PlanVersionDetail(**draft, entitlements=[])

        with patch.object(
            catalog_service, "get_plan_version", side_effect=fake_get_plan_version
        ):
            catalog_service.supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[draft]
            )
            await catalog_service.delete_draft_version(version_id)

    @pytest.mark.asyncio
    async def test_delete_draft_version_rejects_published(
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
                await catalog_service.delete_draft_version(version_id)
