"""Maintenance jobs propagate partial failures to their scheduler."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from src.maintenance import jobs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "job, target",
    [
        (
            jobs.renew_free_plans,
            "src.billing.free_plan_renewal_scheduler.FreePlanRenewalScheduler.run_once",
        ),
        (
            jobs.migrate_plans,
            "src.billing.plan_migration_scheduler."
            "PlanMigrationSchedulerService.run_once",
        ),
        (
            jobs.process_phone_rentals,
            "src.phone_numbers.rental_scheduler.PhoneNumberRentalScheduler.run_once",
        ),
    ],
)
async def test_row_failure_is_not_acknowledged_as_success(job, target):
    with patch(target, new=AsyncMock(return_value=SimpleNamespace(errors=1))):
        with pytest.raises(RuntimeError):
            await job()


@pytest.mark.asyncio
async def test_recovery_pass_requests_strict_failure_reporting():
    with patch(
        "src.notifications.retry_scheduler.NotificationRetryScheduler.run_once",
        new=AsyncMock(return_value=["interest_lead"]),
    ) as run:
        with pytest.raises(RuntimeError):
            await jobs.recover_pending_work()
    run.assert_awaited_once_with(strict=True)


def test_job_names_are_a_fixed_allowlist():
    assert set(jobs.maintenance_jobs()) == {
        "oauth-refresh",
        "recovery",
        "free-renewal",
        "plan-migration",
        "phone-rental",
    }


@pytest.mark.asyncio
async def test_phone_interval_respects_runtime_administrator_setting():
    with patch(
        "src.phone_numbers.rental_scheduler.PhoneNumberRentalScheduler."
        "_get_runtime_interval_hours",
        new=AsyncMock(return_value=2),
    ):
        assert await jobs.maintenance_interval_seconds("phone-rental") == 7200


@pytest.mark.asyncio
async def test_phone_worker_retries_deferred_organizations():
    with patch(
        "src.phone_numbers.rental_scheduler.PhoneNumberRentalScheduler.run_once",
        new=AsyncMock(return_value=SimpleNamespace(errors=0, deferred=1)),
    ) as run:
        with pytest.raises(jobs.RetryableMaintenanceError):
            await jobs.process_phone_rentals()
    run.assert_awaited_once_with(guarded=True)


@pytest.mark.asyncio
async def test_unknown_interval_is_rejected():
    with pytest.raises(ValueError):
        await jobs.maintenance_interval_seconds("unknown")
