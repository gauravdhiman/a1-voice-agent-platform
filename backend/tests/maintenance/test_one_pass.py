"""One-shot entry points preserve the outcomes used for retry decisions."""

from unittest.mock import AsyncMock, patch

import pytest
from src.billing.free_plan_renewal_scheduler import FreePlanRenewalScheduler
from src.billing.plan_migration_scheduler import PlanMigrationSchedulerService
from src.services.token_refresh_service import TokenRefreshService


@pytest.mark.asyncio
async def test_free_plan_one_pass_returns_service_result():
    result = object()
    with patch(
        "src.billing.free_plan_renewal_scheduler.FreePlanRenewalService"
    ) as service:
        service.return_value.process_due_renewals = AsyncMock(return_value=result)
        scheduler = FreePlanRenewalScheduler()
        assert await scheduler.run_once() is result


@pytest.mark.asyncio
async def test_plan_migration_one_pass_returns_service_result():
    result = object()
    with patch(
        "src.billing.plan_migration_scheduler."
        "plan_migration_service.process_due_migrations",
        new=AsyncMock(return_value=result),
    ):
        assert await PlanMigrationSchedulerService().run_once() is result


@pytest.mark.asyncio
async def test_token_refresh_one_pass_checks_due_connections():
    service = TokenRefreshService.__new__(TokenRefreshService)
    service._refresh_expired_tokens = AsyncMock()
    await service.run_once()
    service._refresh_expired_tokens.assert_awaited_once()
