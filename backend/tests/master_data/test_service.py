"""Tests for the audited master-data seeding service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.master_data.definitions import build_master_data_catalog
from src.master_data.service import MasterDataService


class TestMasterDataService:
    """Verify explicit, reviewed seed orchestration."""

    @pytest.mark.asyncio
    async def test_explicit_seed_can_reapply_a_domain(self):
        """A reviewed plan can explicitly rerun a seed domain."""
        service = MasterDataService.__new__(MasterDataService)
        service._catalog = lambda: build_master_data_catalog([])
        service._seed_domain = AsyncMock(return_value={"changed": 15})
        service._record_seed_run = AsyncMock()

        result = await service.seed_domains(["platform_skills"], triggered_by="admin")

        assert result == [
            {
                "domain": "platform_skills",
                "operation": "seed",
                "changed": 15,
                "details": {"changed": 15},
            }
        ]
        service._seed_domain.assert_awaited_once_with("platform_skills", reset=False)
        assert service._record_seed_run.await_count == 2
        assert service._record_seed_run.await_args_list[0].kwargs["status"] == "running"
        assert (
            service._record_seed_run.await_args_list[1].kwargs["status"] == "completed"
        )

    @pytest.mark.asyncio
    async def test_explicit_seed_rejects_changed_reviewed_definition(self):
        """The service refuses to apply a plan whose source hash is stale."""
        service = MasterDataService.__new__(MasterDataService)
        service._catalog = lambda: build_master_data_catalog([])
        service._seed_domain = AsyncMock()

        with pytest.raises(ValueError, match="definition changed"):
            await service.seed_domains(
                ["platform_skills"],
                triggered_by=None,
                expected_definition_hashes={"platform_skills": "stale-hash"},
            )

        service._seed_domain.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explicit_seed_rejects_missing_reviewed_definition_hash(self):
        """Direct callers cannot bypass reviewed-source validation with an empty map."""
        service = MasterDataService.__new__(MasterDataService)
        service._catalog = lambda: build_master_data_catalog([])
        service._seed_domain = AsyncMock()

        with pytest.raises(ValueError, match="definition hash"):
            await service.seed_domains(
                ["platform_skills"],
                triggered_by=None,
                expected_definition_hashes={},
            )

        service._seed_domain.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explicit_seed_rejects_duplicate_domains(self):
        """Direct callers cannot create duplicate audit runs for one domain."""
        service = MasterDataService.__new__(MasterDataService)
        service._catalog = lambda: build_master_data_catalog([])
        service._seed_domain = AsyncMock()

        with pytest.raises(ValueError, match="duplicate"):
            await service.seed_domains(
                ["platform_skills", "platform_skills"], triggered_by=None
            )

        service._seed_domain.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_preview_counts_entitlements_by_key(self):
        """Preview uses the entitlement catalog's string primary key."""
        service = MasterDataService.__new__(MasterDataService)
        service.supabase = MagicMock()
        query = service.supabase.table.return_value.select.return_value
        query.execute.return_value.data = [{"key": "max_agents"}]
        definition = next(
            item
            for item in build_master_data_catalog([])
            if item.key == "entitlement_definitions"
        )

        count = await service._safe_current_count(definition)

        assert count == 1
        service.supabase.table.assert_called_once_with("entitlement_definitions")
        service.supabase.table.return_value.select.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_system_pricing_skips_unchanged_rows_and_preserves_admin_state(self):
        """Normal pricing apply must not rewrite an administrator's rate or activation."""
        from src.billing.system_pricing import SYSTEM_PRICING

        service = MasterDataService.__new__(MasterDataService)
        service.supabase = MagicMock()
        table = service.supabase.table.return_value
        item = SYSTEM_PRICING[0]
        table.select.return_value.in_.return_value.execute.return_value.data = [
            {
                "name": item.event_name,
                "description": item.description,
                "credit_cost": 999,
                "category": item.category,
                "is_active": False,
                "meter_type": item.meter_type,
                "billing_unit": item.billing_unit,
            }
        ]

        result = await service._seed_system_pricing(reset=False)

        assert result["changed"] == len(SYSTEM_PRICING) - 1
        table.upsert.assert_called_once()
        rows = table.upsert.call_args.args[0]
        assert all(row["name"] != item.event_name for row in rows)

    @pytest.mark.asyncio
    async def test_system_pricing_creates_missing_rows(self):
        """A first apply creates every missing source-defined usage price."""
        from src.billing.system_pricing import SYSTEM_PRICING

        service = MasterDataService.__new__(MasterDataService)
        service.supabase = MagicMock()
        table = service.supabase.table.return_value
        table.select.return_value.in_.return_value.execute.return_value.data = []

        result = await service._seed_system_pricing(reset=False)

        assert result == {"changed": len(SYSTEM_PRICING), "reset_defaults": False}
        table.upsert.assert_called_once()
        rows = table.upsert.call_args.args[0]
        assert len(rows) == len(SYSTEM_PRICING)

    @pytest.mark.asyncio
    async def test_reset_rejects_an_unrecognized_environment(self, monkeypatch):
        """Direct service callers also fail closed when reset environment is unknown."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        service = MasterDataService.__new__(MasterDataService)
        service._catalog = lambda: build_master_data_catalog([])
        service._seed_domain = AsyncMock()
        service._record_seed_run = AsyncMock()

        with pytest.raises(ValueError, match="explicit non-production"):
            await service.seed_domains(
                ["platform_skills"], triggered_by=None, reset=True
            )

        service._seed_domain.assert_not_awaited()
