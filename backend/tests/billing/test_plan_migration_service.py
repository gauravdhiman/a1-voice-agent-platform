"""
Tests for plan-version migration processing and self-service migrate.

Phase 3: grace-period expiry auto-migration and org self-service migrate must
update ``plan_version_id`` while respecting publish-event policy.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.billing.entitlement_models import PlanMigrationStatus


@pytest.fixture
def plan_migration_service(mock_supabase_client):
    """PlanMigrationService with mocked Supabase."""
    from src.billing.plan_migration_service import PlanMigrationService

    service = PlanMigrationService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def subscription_id():
    return uuid4()


@pytest.fixture
def migration_id():
    return uuid4()


@pytest.fixture
def from_version_id():
    return uuid4()


@pytest.fixture
def to_version_id():
    return uuid4()


def _migration_row(
    migration_id,
    subscription_id,
    from_version_id,
    to_version_id,
    *,
    status="grace_active",
    grace_end=None,
    org_id=None,
    stripe_sub_id="sub_stripe",
):
    end = grace_end or (datetime.now(timezone.utc) - timedelta(days=1))
    return {
        "id": str(migration_id),
        "organization_subscription_id": str(subscription_id),
        "publish_event_id": str(uuid4()),
        "from_plan_version_id": str(from_version_id),
        "to_plan_version_id": str(to_version_id),
        "status": status,
        "grace_period_ends_at": end.isoformat(),
        "migrated_at": None,
        "migration_type": None,
        "organization_subscriptions": {
            "id": str(subscription_id),
            "organization_id": str(org_id or uuid4()),
            "stripe_subscription_id": stripe_sub_id,
            "plan_version_id": str(from_version_id),
            "status": "active",
        },
        "plan_version_publish_events": {
            "auto_migrate_on_expiry": True,
            "migration_mode": "grace_then_required",
            "stripe_migration_timing": "immediate",
        },
    }


class TestProcessDueMigrations:
    """Daily job processes expired grace-period migrations."""

    @pytest.mark.asyncio
    async def test_process_due_migrations_migrates_expired_grace(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        """Expired grace_active rows with auto_migrate_on_expiry are migrated."""
        row = _migration_row(
            migration_id,
            subscription_id,
            from_version_id,
            to_version_id,
        )

        with (
            patch.object(
                plan_migration_service,
                "_fetch_due_migrations",
                new_callable=AsyncMock,
                return_value=[row],
            ),
            patch.object(
                plan_migration_service,
                "_execute_migration",
                new_callable=AsyncMock,
            ) as mock_execute,
        ):
            result = await plan_migration_service.process_due_migrations()

        assert result.processed == 1
        assert result.migrated == 1
        assert result.errors == 0
        mock_execute.assert_called_once()
        call_kwargs = mock_execute.call_args.kwargs
        assert call_kwargs["migration_type"] == "auto"

    @pytest.mark.asyncio
    async def test_process_due_migrations_skips_when_auto_migrate_disabled(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        """Rows without auto_migrate_on_expiry are skipped."""
        row = _migration_row(
            migration_id,
            subscription_id,
            from_version_id,
            to_version_id,
        )
        row["plan_version_publish_events"]["auto_migrate_on_expiry"] = False

        with (
            patch.object(
                plan_migration_service,
                "_fetch_due_migrations",
                new_callable=AsyncMock,
                return_value=[row],
            ),
            patch.object(
                plan_migration_service,
                "_execute_migration",
                new_callable=AsyncMock,
            ) as mock_execute,
        ):
            result = await plan_migration_service.process_due_migrations()

        assert result.processed == 1
        assert result.skipped == 1
        assert result.migrated == 0
        mock_execute.assert_not_called()


class TestSelfServiceMigrate:
    """Org admin can migrate before grace deadline."""

    @pytest.mark.asyncio
    async def test_migrate_organization_self_service(
        self,
        plan_migration_service,
        org_id,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        """Self-service migrate executes migration for active grace row."""
        row = _migration_row(
            migration_id,
            subscription_id,
            from_version_id,
            to_version_id,
            org_id=org_id,
            grace_end=datetime.now(timezone.utc) + timedelta(days=30),
        )

        with (
            patch.object(
                plan_migration_service,
                "_get_active_migration_for_subscription_org",
                new_callable=AsyncMock,
                return_value=row,
            ),
            patch.object(
                plan_migration_service,
                "_execute_migration",
                new_callable=AsyncMock,
            ) as mock_execute,
        ):
            result = await plan_migration_service.migrate_organization(org_id)

        assert result["migration_id"] == str(migration_id)
        mock_execute.assert_called_once()
        assert mock_execute.call_args.kwargs["migration_type"] == "self_service"

    @pytest.mark.asyncio
    async def test_migrate_organization_raises_when_no_active_migration(
        self, plan_migration_service, org_id
    ):
        """Self-service migrate fails when org has no pending migration."""
        with patch.object(
            plan_migration_service,
            "_get_active_migration_for_subscription_org",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ValueError, match="No active plan migration"):
                await plan_migration_service.migrate_organization(org_id)


class TestGetActiveMigrationForOrg:
    """Migration info exposed to billing UI via entitlements."""

    @pytest.mark.asyncio
    async def test_get_active_migration_for_organization(
        self,
        org_id,
        migration_id,
        from_version_id,
        to_version_id,
        subscription_id,
    ):
        """Returns OrgPlanMigrationInfo for orgs in grace period."""
        from src.billing.plan_migration_service import PlanMigrationService

        row = _migration_row(
            migration_id,
            subscription_id,
            from_version_id,
            to_version_id,
            org_id=org_id,
            grace_end=datetime.now(timezone.utc) + timedelta(days=10),
        )
        row["plan_version_publish_events"]["allow_indefinite_legacy"] = True

        service = PlanMigrationService()
        with (
            patch.object(
                service,
                "_get_active_migration_for_subscription_org",
                new_callable=AsyncMock,
                return_value=row,
            ),
            patch.object(
                service,
                "_get_plan_version_display",
                new_callable=AsyncMock,
                return_value=("Pro v3", "pro"),
            ),
        ):
            info = await service.get_active_migration_for_organization(org_id)

        assert info is not None
        assert info.migration_id == migration_id
        assert info.status == PlanMigrationStatus.GRACE_ACTIVE
        assert info.target_plan_version_label == "Pro v3"
        assert info.target_plan_product_slug == "pro"
        assert info.can_self_migrate is True


class TestExecuteMigrationLocks:
    """Automated and self-service migrations share the plan-change lock."""

    @pytest.mark.asyncio
    async def test_migration_claims_and_releases_the_shared_transition_lock(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        row = _migration_row(
            migration_id, subscription_id, from_version_id, to_version_id
        )
        plan_migration_service._get_plan_version = AsyncMock(
            side_effect=[
                {
                    "id": str(to_version_id),
                    "billing_interval": "monthly",
                    "stripe_price_id": "price_target",
                    "billing_mode": "paid",
                    "legacy_subscription_plan_id": None,
                },
                {
                    "id": str(from_version_id),
                    "billing_interval": "monthly",
                    "stripe_price_id": "price_source",
                },
            ]
        )

        with (
            patch(
                "src.billing.versioned_subscription_service.versioned_subscription_service.claim_plan_transition",
                return_value=True,
            ) as claim,
            patch(
                "src.billing.versioned_subscription_service.versioned_subscription_service.clear_plan_transition",
                return_value=True,
            ) as clear,
            patch(
                "src.billing.plan_migration_service.stripe_service.change_subscription_price",
                new_callable=AsyncMock,
            ) as change_price,
        ):
            await plan_migration_service._execute_migration(
                row, migration_type="self_service"
            )

        claim.assert_called_once()
        assert claim.call_args.args[0] == str(subscription_id)
        assert claim.call_args.args[1]["transition_id"] == str(migration_id)
        change_price.assert_awaited_once_with(
            "sub_stripe", "price_target", at_period_end=False
        )
        clear.assert_called_once_with(str(subscription_id), str(migration_id))

    @pytest.mark.asyncio
    async def test_at_period_end_migration_persists_scheduled_plan_marker(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        """A scheduled Stripe migration blocks conflicting plan changes."""
        row = _migration_row(
            migration_id, subscription_id, from_version_id, to_version_id
        )
        row["organization_subscriptions"]["metadata"] = {"billing_mode": "paid"}
        row["organization_subscriptions"][
            "current_period_end"
        ] = "2026-11-01T00:00:00+00:00"
        row["plan_version_publish_events"]["stripe_migration_timing"] = "at_period_end"
        plan_migration_service._get_plan_version = AsyncMock(
            side_effect=[
                {
                    "id": str(to_version_id),
                    "billing_interval": "monthly",
                    "stripe_price_id": "price_target",
                    "billing_mode": "paid",
                    "legacy_subscription_plan_id": None,
                },
                {
                    "id": str(from_version_id),
                    "billing_interval": "monthly",
                    "stripe_price_id": "price_source",
                },
            ]
        )

        with (
            patch(
                "src.billing.versioned_subscription_service.versioned_subscription_service.claim_plan_transition",
                return_value=True,
            ),
            patch(
                "src.billing.versioned_subscription_service.versioned_subscription_service.clear_plan_transition",
                return_value=True,
            ) as clear,
            patch(
                "src.billing.plan_migration_service.stripe_service.change_subscription_price",
                new_callable=AsyncMock,
            ) as change_price,
        ):
            await plan_migration_service._execute_migration(
                row, migration_type="self_service"
            )

        change_price.assert_awaited_once_with(
            "sub_stripe", "price_target", at_period_end=True
        )
        subscription_update = (
            plan_migration_service.supabase.table.return_value.update.call_args_list[
                0
            ].args[0]
        )
        scheduled = subscription_update["metadata"]["pending_plan_change"]
        assert scheduled == {
            "transition_id": str(migration_id),
            "target_plan_version_id": str(to_version_id),
            "target_billing_mode": "paid",
            "effective_at": "2026-11-01T00:00:00+00:00",
            "status": "scheduled",
        }
        clear.assert_called_once_with(str(subscription_id), str(migration_id))

        from src.billing.versioned_subscription_service import (
            PlanChangeConfirmRequest,
            PlanChangeInProgressError,
            VersionedSubscriptionService,
        )

        customer_service = VersionedSubscriptionService()
        customer_service._get_existing_subscription = AsyncMock(
            return_value={
                "id": str(subscription_id),
                "plan_version_id": str(from_version_id),
                "status": "active",
                "metadata": subscription_update["metadata"],
            }
        )
        customer_service.preview_plan_change = AsyncMock()
        with pytest.raises(PlanChangeInProgressError, match="already scheduled"):
            await customer_service.confirm_plan_change(
                PlanChangeConfirmRequest(
                    organization_id=UUID(
                        row["organization_subscriptions"]["organization_id"]
                    ),
                    transition_id=uuid4(),
                    target_plan_version_id=to_version_id,
                ),
                customer_email="owner@example.com",
            )
        customer_service.preview_plan_change.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_migration_rejects_existing_pending_plan_transition(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        row = _migration_row(
            migration_id, subscription_id, from_version_id, to_version_id
        )
        row["organization_subscriptions"]["pending_plan_transition"] = {
            "transition_id": "existing_transition",
            "billing_interval_changed": True,
        }

        with (
            patch(
                "src.billing.versioned_subscription_service.versioned_subscription_service.reconcile_pending_plan_transition",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "src.billing.plan_migration_service.stripe_service.change_subscription_price",
                new_callable=AsyncMock,
            ) as change_price,
            pytest.raises(PlanChangeInProgressError),
        ):
            await plan_migration_service._execute_migration(
                row, migration_type="self_service"
            )

        change_price.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_migration_rejects_a_different_scheduled_plan_change(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        row = _migration_row(
            migration_id, subscription_id, from_version_id, to_version_id
        )
        row["organization_subscriptions"]["metadata"] = {
            "pending_plan_change": {
                "transition_id": str(uuid4()),
                "target_plan_version_id": str(uuid4()),
                "status": "scheduled",
            }
        }

        with (
            patch(
                "src.billing.plan_migration_service.stripe_service.change_subscription_price",
                new_callable=AsyncMock,
            ) as change_price,
            pytest.raises(PlanChangeInProgressError, match="different plan change"),
        ):
            await plan_migration_service._execute_migration(
                row, migration_type="self_service"
            )

        change_price.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_migration_rejects_a_competing_atomic_claim(
        self,
        plan_migration_service,
        migration_id,
        subscription_id,
        from_version_id,
        to_version_id,
    ):
        from src.billing.versioned_subscription_service import (
            PlanChangeInProgressError,
        )

        row = _migration_row(
            migration_id, subscription_id, from_version_id, to_version_id
        )
        plan_migration_service._get_plan_version = AsyncMock(
            side_effect=[
                {
                    "id": str(to_version_id),
                    "billing_interval": "monthly",
                    "stripe_price_id": "price_target",
                },
                {
                    "id": str(from_version_id),
                    "billing_interval": "monthly",
                    "stripe_price_id": "price_source",
                },
            ]
        )

        with (
            patch(
                "src.billing.versioned_subscription_service.versioned_subscription_service.claim_plan_transition",
                return_value=False,
            ),
            patch(
                "src.billing.plan_migration_service.stripe_service.change_subscription_price",
                new_callable=AsyncMock,
            ) as change_price,
            pytest.raises(PlanChangeInProgressError),
        ):
            await plan_migration_service._execute_migration(
                row, migration_type="self_service"
            )

        change_price.assert_not_awaited()
