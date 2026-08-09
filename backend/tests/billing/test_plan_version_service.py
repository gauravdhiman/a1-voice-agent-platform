"""
Tests for plan version publish workflow and Stripe price resolution.

Phase 2: grandfathering — publishing a new version must not mutate existing
subscriber ``plan_version_id`` unless migration_mode is ``immediate_required``.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.billing.plan_version_models import (
    BillingMode,
    MigrationMode,
    PlanVersionPublishRequest,
    PlanVersionStatus,
)


@pytest.fixture
def plan_version_service(mock_supabase_client):
    """PlanVersionService with mocked Supabase."""
    from src.billing.plan_version_service import PlanVersionService

    service = PlanVersionService()
    service.supabase = mock_supabase_client
    return service


@pytest.fixture
def product_id():
    return uuid4()


@pytest.fixture
def draft_version_id():
    return uuid4()


@pytest.fixture
def previous_version_id():
    return uuid4()


@pytest.fixture
def admin_user_id():
    return uuid4()


def _version_row(
    version_id,
    product_id,
    *,
    status=PlanVersionStatus.DRAFT.value,
    version_number=2,
    price_amount_cents=5900,
    stripe_price_id=None,
    billing_mode=BillingMode.PAID.value,
    is_current=False,
    legacy_plan_id=None,
):
    return {
        "id": str(version_id),
        "plan_product_id": str(product_id),
        "version_number": version_number,
        "status": status,
        "display_label": f"Plan v{version_number}",
        "price_amount_cents": price_amount_cents,
        "currency": "USD",
        "billing_interval": "monthly",
        "trial_period_days": None,
        "stripe_product_id": "prod_stripe",
        "stripe_price_id": stripe_price_id,
        "billing_mode": billing_mode,
        "is_current_for_signup": is_current,
        "published_at": (
            datetime.now(timezone.utc).isoformat()
            if status == PlanVersionStatus.PUBLISHED.value
            else None
        ),
        "legacy_subscription_plan_id": str(legacy_plan_id) if legacy_plan_id else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class TestPlanVersionPublish:
    """Publish workflow and grandfathering behavior."""

    @pytest.mark.asyncio
    async def test_publish_free_version_keeps_stripe_price_optional(
        self,
        plan_version_service,
        draft_version_id,
        product_id,
        admin_user_id,
    ):
        """Free versions publish without a Stripe Price identifier."""
        draft = _version_row(
            draft_version_id,
            product_id,
            price_amount_cents=0,
            billing_mode=BillingMode.FREE.value,
        )

        with patch.object(
            plan_version_service, "_get_plan_version", new_callable=AsyncMock
        ) as mock_get, patch.object(
            plan_version_service,
            "_get_current_signup_version_for_product",
            new_callable=AsyncMock,
            return_value=None,
        ), patch.object(
            plan_version_service, "_ensure_stripe_price", new_callable=AsyncMock
        ) as mock_stripe, patch.object(
            plan_version_service, "_update_plan_version", new_callable=AsyncMock
        ) as mock_update, patch.object(
            plan_version_service, "_create_publish_event", new_callable=AsyncMock
        ) as mock_event:
            mock_get.return_value = draft
            mock_stripe.return_value = None
            mock_update.return_value = {**draft, "status": "published"}
            event_id = uuid4()
            mock_event.return_value = {"id": str(event_id)}

            result = await plan_version_service.publish_plan_version(
                draft_version_id,
                PlanVersionPublishRequest(),
                published_by=admin_user_id,
            )

        assert result.stripe_price_id is None
        mock_stripe.assert_awaited_once_with(draft)
        update_fields = mock_update.call_args.args[1]
        assert update_fields["stripe_price_id"] is None

    @pytest.mark.asyncio
    async def test_publish_marks_draft_current_and_deprecates_previous(
        self,
        plan_version_service,
        draft_version_id,
        previous_version_id,
        product_id,
        admin_user_id,
    ):
        """Publishing sets draft to published/current and deprecates prior version."""
        draft = _version_row(draft_version_id, product_id)
        previous = _version_row(
            previous_version_id,
            product_id,
            status=PlanVersionStatus.PUBLISHED.value,
            version_number=1,
            stripe_price_id="price_v1",
            is_current=True,
            legacy_plan_id=uuid4(),
        )

        with patch.object(
            plan_version_service, "_get_plan_version", new_callable=AsyncMock
        ) as mock_get, patch.object(
            plan_version_service,
            "_get_current_signup_version_for_product",
            new_callable=AsyncMock,
            return_value=previous,
        ), patch.object(
            plan_version_service, "_ensure_stripe_price", new_callable=AsyncMock
        ) as mock_stripe, patch.object(
            plan_version_service, "_update_plan_version", new_callable=AsyncMock
        ) as mock_update, patch.object(
            plan_version_service, "_create_publish_event", new_callable=AsyncMock
        ) as mock_event, patch.object(
            plan_version_service,
            "_create_migration_rows_for_subscribers",
            new_callable=AsyncMock,
            return_value=0,
        ), patch.object(
            plan_version_service,
            "_migrate_subscribers_immediately",
            new_callable=AsyncMock,
            return_value=0,
        ):
            mock_get.return_value = draft
            mock_stripe.return_value = "price_v2_new"
            published_at = datetime.now(timezone.utc)
            mock_update.side_effect = [
                {**draft, "status": "published", "stripe_price_id": "price_v2_new"},
                {**previous, "status": "deprecated", "is_current_for_signup": False},
            ]
            event_id = uuid4()
            mock_event.return_value = {
                "id": str(event_id),
                "published_at": published_at.isoformat(),
            }

            result = await plan_version_service.publish_plan_version(
                draft_version_id,
                PlanVersionPublishRequest(
                    migration_mode=MigrationMode.NEW_SIGNUPS_ONLY
                ),
                published_by=admin_user_id,
            )

        assert result.plan_version_id == draft_version_id
        assert result.from_plan_version_id == previous_version_id
        assert result.stripe_price_id == "price_v2_new"
        assert result.publish_event_id == event_id
        assert result.migration_rows_created == 0
        assert mock_update.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_grace_then_required_creates_migration_rows_not_immediate_migrate(
        self,
        plan_version_service,
        draft_version_id,
        previous_version_id,
        product_id,
        admin_user_id,
    ):
        """Grace migration creates tracking rows but does not change subs on publish."""
        draft = _version_row(draft_version_id, product_id, stripe_price_id="price_v2")
        previous = _version_row(
            previous_version_id,
            product_id,
            status=PlanVersionStatus.PUBLISHED.value,
            version_number=1,
            stripe_price_id="price_v1",
            is_current=True,
        )

        with patch.object(
            plan_version_service, "_get_plan_version", new_callable=AsyncMock
        ) as mock_get, patch.object(
            plan_version_service,
            "_get_current_signup_version_for_product",
            new_callable=AsyncMock,
            return_value=previous,
        ), patch.object(
            plan_version_service, "_ensure_stripe_price", new_callable=AsyncMock
        ) as mock_stripe, patch.object(
            plan_version_service, "_update_plan_version", new_callable=AsyncMock
        ) as mock_update, patch.object(
            plan_version_service, "_create_publish_event", new_callable=AsyncMock
        ) as mock_event, patch.object(
            plan_version_service,
            "_create_migration_rows_for_subscribers",
            new_callable=AsyncMock,
            return_value=2,
        ) as mock_migrations, patch.object(
            plan_version_service,
            "_migrate_subscribers_immediately",
            new_callable=AsyncMock,
            return_value=0,
        ) as mock_immediate:
            mock_get.return_value = draft
            mock_stripe.return_value = "price_v2"
            mock_update.return_value = draft
            mock_event.return_value = {
                "id": str(uuid4()),
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

            result = await plan_version_service.publish_plan_version(
                draft_version_id,
                PlanVersionPublishRequest(
                    migration_mode=MigrationMode.GRACE_THEN_REQUIRED,
                    grace_period_days=90,
                    auto_migrate_on_expiry=True,
                ),
                published_by=admin_user_id,
            )

        assert result.migration_rows_created == 2
        assert result.subscribers_migrated_immediately == 0
        mock_migrations.assert_called_once()
        mock_immediate.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_immediate_required_migrates_subscribers(
        self,
        plan_version_service,
        draft_version_id,
        previous_version_id,
        product_id,
        admin_user_id,
    ):
        """Immediate required mode updates subscriber plan_version_id on publish."""
        draft = _version_row(draft_version_id, product_id, stripe_price_id="price_v2")
        previous = _version_row(
            previous_version_id,
            product_id,
            status=PlanVersionStatus.PUBLISHED.value,
            version_number=1,
            is_current=True,
        )

        with patch.object(
            plan_version_service, "_get_plan_version", new_callable=AsyncMock
        ) as mock_get, patch.object(
            plan_version_service,
            "_get_current_signup_version_for_product",
            new_callable=AsyncMock,
            return_value=previous,
        ), patch.object(
            plan_version_service, "_ensure_stripe_price", new_callable=AsyncMock
        ) as mock_stripe, patch.object(
            plan_version_service, "_update_plan_version", new_callable=AsyncMock
        ) as mock_update, patch.object(
            plan_version_service, "_create_publish_event", new_callable=AsyncMock
        ) as mock_event, patch.object(
            plan_version_service,
            "_create_migration_rows_for_subscribers",
            new_callable=AsyncMock,
            return_value=0,
        ), patch.object(
            plan_version_service,
            "_migrate_subscribers_immediately",
            new_callable=AsyncMock,
            return_value=3,
        ) as mock_immediate:
            mock_get.return_value = draft
            mock_stripe.return_value = "price_v2"
            mock_update.return_value = draft
            mock_event.return_value = {
                "id": str(uuid4()),
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

            result = await plan_version_service.publish_plan_version(
                draft_version_id,
                PlanVersionPublishRequest(
                    migration_mode=MigrationMode.IMMEDIATE_REQUIRED,
                ),
                published_by=admin_user_id,
            )

        assert result.subscribers_migrated_immediately == 3
        mock_immediate.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_rejects_non_draft(
        self, plan_version_service, draft_version_id, product_id, admin_user_id
    ):
        """Only draft versions can be published."""
        published = _version_row(
            draft_version_id,
            product_id,
            status=PlanVersionStatus.PUBLISHED.value,
            stripe_price_id="price_x",
            is_current=True,
        )

        with patch.object(
            plan_version_service, "_get_plan_version", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = published
            with pytest.raises(ValueError, match="draft"):
                await plan_version_service.publish_plan_version(
                    draft_version_id,
                    PlanVersionPublishRequest(),
                    published_by=admin_user_id,
                )


class TestEnsureStripePrice:
    """Stripe Price auto-create and manual fallback."""

    @pytest.mark.asyncio
    async def test_ensure_stripe_price_returns_existing_id(
        self, plan_version_service, product_id, draft_version_id
    ):
        draft = _version_row(
            draft_version_id,
            product_id,
            stripe_price_id="price_manual",
        )
        result = await plan_version_service._ensure_stripe_price(draft)
        assert result == "price_manual"

    @pytest.mark.asyncio
    async def test_ensure_stripe_price_skips_stripe_for_free_version(
        self, plan_version_service, product_id, draft_version_id
    ):
        """Free versions may publish without creating a Stripe Price."""
        draft = _version_row(
            draft_version_id,
            product_id,
            billing_mode=BillingMode.FREE.value,
        )
        with patch(
            "src.billing.plan_version_service.stripe_service.create_price",
            new_callable=AsyncMock,
        ) as create_price:
            result = await plan_version_service._ensure_stripe_price(draft)

        assert result is None
        create_price.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ensure_stripe_price_raises_actionable_error_on_stripe_failure(
        self, plan_version_service, product_id, draft_version_id
    ):
        draft = _version_row(draft_version_id, product_id)
        with patch(
            "src.billing.plan_version_service.stripe_service.create_price",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network down"),
        ):
            with pytest.raises(ValueError, match="Failed to auto-create Stripe Price"):
                await plan_version_service._ensure_stripe_price(draft)


class TestResolveCheckoutPlan:
    """Stripe price ID → plan version resolution."""

    @pytest.mark.asyncio
    async def test_resolve_by_stripe_price_id(
        self, plan_version_service, mock_supabase_client
    ):
        """Webhook/checkout resolves plan_version_id from stripe_price_id."""
        version_id = uuid4()
        legacy_plan_id = uuid4()
        row = {
            "id": str(version_id),
            "stripe_price_id": "price_abc",
            "legacy_subscription_plan_id": str(legacy_plan_id),
            "status": PlanVersionStatus.PUBLISHED.value,
        }
        table = mock_supabase_client.table.return_value
        table.execute.return_value = MagicMock(data=[row])

        resolved = await plan_version_service.resolve_checkout_plan("price_abc")

        assert resolved.plan_version_id == version_id
        assert resolved.subscription_plan_id == legacy_plan_id
        assert resolved.stripe_price_id == "price_abc"

    @pytest.mark.asyncio
    async def test_resolve_raises_when_price_unknown(
        self, plan_version_service, mock_supabase_client
    ):
        """Unknown Stripe price IDs raise ValueError."""
        table = mock_supabase_client.table.return_value
        table.execute.return_value = MagicMock(data=[])

        with pytest.raises(ValueError, match="No plan version"):
            await plan_version_service.resolve_checkout_plan("price_missing")
