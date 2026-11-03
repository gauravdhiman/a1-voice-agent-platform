"""Provider-independent one-pass maintenance job implementations."""

from typing import Awaitable, Callable

from .runner import RetryableMaintenanceError


async def refresh_oauth() -> None:
    """Refresh due OAuth connections using existing per-connection fencing."""
    from src.services.token_refresh_service import TokenRefreshService

    from shared.voice_agents.tool_service import ToolService

    await TokenRefreshService(ToolService()).run_once(strict=True)


async def recover_pending_work() -> None:
    """Process notification, retention, and voice-settlement recovery once."""
    from src.notifications.retry_scheduler import NotificationRetryScheduler

    failures = await NotificationRetryScheduler().run_once(strict=True)
    if failures:
        # Outboxes and the existing notification system provide at-least-once
        # delivery, not exactly-once provider side effects. A retry preserves
        # their existing semantics; duplicate delivery can still occur when a
        # provider accepts a message but its acknowledgement is lost.
        raise RetryableMaintenanceError("One or more recovery operations failed")


async def renew_free_plans() -> None:
    """Grant due free-plan renewals and report partial failure."""
    from src.billing.free_plan_renewal_scheduler import FreePlanRenewalScheduler

    result = await FreePlanRenewalScheduler().run_once()
    if result.errors:
        # Period-specific grant keys make a repeated renewal pass safe.
        raise RetryableMaintenanceError("Free-plan renewal pass had failures")


async def migrate_plans() -> None:
    """Process due subscription-plan migrations and report partial failure."""
    from src.billing.plan_migration_scheduler import PlanMigrationSchedulerService

    result = await PlanMigrationSchedulerService().run_once()
    if result.errors:
        raise RuntimeError("Plan migration pass had failures")


async def process_phone_rentals() -> None:
    """Process due phone-number rentals and report partial failure."""
    from src.phone_numbers.rental_scheduler import PhoneNumberRentalScheduler

    result = await PhoneNumberRentalScheduler().run_once(guarded=True)
    if result.errors:
        raise RuntimeError("Phone rental pass had failures")
    if result.deferred:
        raise RetryableMaintenanceError("Phone rental pass has deferred organizations")


def maintenance_jobs() -> dict[str, Callable[[], Awaitable[None]]]:
    """Return the fixed allowlist of named maintenance operations."""
    return {
        "oauth-refresh": refresh_oauth,
        "recovery": recover_pending_work,
        "free-renewal": renew_free_plans,
        "plan-migration": migrate_plans,
        "phone-rental": process_phone_rentals,
    }


async def maintenance_interval_seconds(job: str) -> float:
    """Resolve each job's existing cadence, including phone admin overrides."""
    from shared.config import settings

    if job == "oauth-refresh":
        return float(settings.token_refresh_check_interval_minutes) * 60
    if job == "recovery":
        from src.notifications.retry_scheduler import _check_interval_hours

        return _check_interval_hours() * 3600
    if job == "free-renewal":
        from src.billing.free_plan_renewal_scheduler import _check_interval_hours

        return _check_interval_hours() * 3600
    if job == "plan-migration":
        from src.billing.plan_migration_scheduler import _check_interval_hours

        return _check_interval_hours() * 3600
    if job == "phone-rental":
        from src.phone_numbers.rental_scheduler import PhoneNumberRentalScheduler

        return await PhoneNumberRentalScheduler()._get_runtime_interval_hours() * 3600
    raise ValueError("Unknown maintenance job")
