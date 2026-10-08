"""Make agent entitlements unlimited unless a positive cap is assigned.

Revision ID: 20261008000001
Revises: 20261007000001
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20261008000001"
down_revision: str | None = "20261007000001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Use unlimited as the max_agents fallback and publish Free v2."""
    connection = op.get_bind()
    connection.execute(
        sa.text("LOCK TABLE organization_subscriptions IN SHARE ROW EXCLUSIVE MODE")
    )
    connection.execute(sa.text("LOCK TABLE plan_versions IN SHARE ROW EXCLUSIVE MODE"))
    connection.execute(
        sa.text(
            """
            UPDATE entitlement_definitions
            SET default_when_absent = '{"type":"unlimited"}'::jsonb,
                updated_at = NOW()
            WHERE key = 'max_agents'
            """
        )
    )

    free_version = (
        connection.execute(
            sa.text(
                """
            SELECT pv.*
            FROM plan_versions AS pv
            JOIN plan_products AS pp ON pp.id = pv.plan_product_id
            WHERE pp.slug = 'free'
              AND pv.is_current_for_signup = true
            ORDER BY pv.version_number DESC
            LIMIT 1
            """
            )
        )
        .mappings()
        .first()
    )
    if free_version is None:
        raise RuntimeError(
            "Cannot publish unlimited Free plan: no current Free version"
        )

    now = datetime.now(timezone.utc)
    new_version_id = uuid4()
    next_version_number = connection.execute(
        sa.text(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM plan_versions
            WHERE plan_product_id = :plan_product_id
            """
        ),
        {"plan_product_id": free_version["plan_product_id"]},
    ).scalar_one()

    connection.execute(
        sa.text(
            """
            UPDATE plan_versions
            SET is_current_for_signup = false,
                status = 'deprecated',
                updated_at = :updated_at
            WHERE id = :version_id
            """
        ),
        {"version_id": free_version["id"], "updated_at": now},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO plan_versions (
                id, plan_product_id, version_number, status, display_label,
                billing_mode, credit_grant_policy, price_amount_cents, currency,
                billing_interval, trial_period_days, stripe_product_id,
                stripe_price_id, is_current_for_signup, published_at,
                legacy_subscription_plan_id, created_at, updated_at
            ) VALUES (
                :id, :plan_product_id, :version_number, 'published', :display_label,
                :billing_mode, :credit_grant_policy, :price_amount_cents, :currency,
                :billing_interval, :trial_period_days, NULL, NULL, true, :published_at,
                NULL, :created_at, :updated_at
            )
            """
        ),
        {
            "id": new_version_id,
            "plan_product_id": free_version["plan_product_id"],
            "version_number": next_version_number,
            "display_label": f"Free v{next_version_number}",
            "billing_mode": free_version["billing_mode"],
            "credit_grant_policy": free_version["credit_grant_policy"],
            "price_amount_cents": free_version["price_amount_cents"],
            "currency": free_version["currency"],
            "billing_interval": free_version["billing_interval"],
            "trial_period_days": free_version["trial_period_days"],
            "published_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO plan_version_entitlements (
                plan_version_id, entitlement_key, value, display_order
            )
            SELECT
                :new_version_id,
                entitlement_key,
                CASE
                    WHEN entitlement_key = 'max_agents'
                    THEN '{"type":"unlimited"}'::jsonb
                    ELSE value
                END,
                display_order
            FROM plan_version_entitlements
            WHERE plan_version_id = :old_version_id
            """
        ),
        {
            "new_version_id": new_version_id,
            "old_version_id": free_version["id"],
        },
    )
    if (
        connection.execute(
            sa.text(
                """
            SELECT 1
            FROM plan_version_entitlements
            WHERE plan_version_id = :old_version_id
              AND entitlement_key = 'max_agents'
            """
            ),
            {"old_version_id": free_version["id"]},
        ).first()
        is None
    ):
        connection.execute(
            sa.text(
                """
                INSERT INTO plan_version_entitlements (
                    plan_version_id, entitlement_key, value, display_order
                )
                SELECT
                    :new_version_id,
                    'max_agents',
                    '{"type":"unlimited"}'::jsonb,
                    COALESCE(MAX(display_order) + 1, 0)
                FROM plan_version_entitlements
                WHERE plan_version_id = :new_version_id
                """
            ),
            {"new_version_id": new_version_id},
        )

    publish_event_id = connection.execute(
        sa.text(
            """
            INSERT INTO plan_version_publish_events (
                from_plan_version_id, to_plan_version_id, migration_mode,
                grace_period_days, auto_migrate_on_expiry,
                allow_indefinite_legacy, stripe_migration_timing,
                compliance_policy, published_by, published_at
            ) VALUES (
                :from_version_id, :to_version_id, 'immediate_required',
                NULL, false, true, 'at_period_end', NULL, NULL, :published_at
            )
            RETURNING id
            """
        ),
        {
            "from_version_id": free_version["id"],
            "to_version_id": new_version_id,
            "published_at": now,
        },
    ).scalar_one()

    connection.execute(
        sa.text(
            """
            INSERT INTO organization_subscription_migrations (
                organization_subscription_id, publish_event_id,
                from_plan_version_id, to_plan_version_id, status,
                migrated_at, migration_type
            )
            SELECT
                id, :publish_event_id, :from_version_id, :to_version_id,
                'migrated', :migrated_at, 'auto'
            FROM organization_subscriptions
            WHERE plan_version_id = :from_version_id
              AND status IN ('active', 'trial')
            """
        ),
        {
            "publish_event_id": publish_event_id,
            "from_version_id": free_version["id"],
            "to_version_id": new_version_id,
            "migrated_at": now,
        },
    )
    connection.execute(
        sa.text(
            """
            UPDATE organization_subscriptions
            SET plan_version_id = :to_version_id,
                updated_at = :updated_at
            WHERE plan_version_id = :from_version_id
              AND status IN ('active', 'trial')
            """
        ),
        {
            "to_version_id": new_version_id,
            "from_version_id": free_version["id"],
            "updated_at": now,
        },
    )


def downgrade() -> None:
    """Restore the previous default and current Free plan version."""
    connection = op.get_bind()
    connection.execute(
        sa.text("LOCK TABLE organization_subscriptions IN SHARE ROW EXCLUSIVE MODE")
    )
    connection.execute(sa.text("LOCK TABLE plan_versions IN SHARE ROW EXCLUSIVE MODE"))
    publish_event = (
        connection.execute(
            sa.text(
                """
            SELECT e.id, e.from_plan_version_id, e.to_plan_version_id
            FROM plan_version_publish_events AS e
            JOIN plan_versions AS target ON target.id = e.to_plan_version_id
            JOIN plan_products AS pp ON pp.id = target.plan_product_id
            WHERE pp.slug = 'free'
              AND e.published_by IS NULL
              AND e.migration_mode = 'immediate_required'
              -- The upgrade stamps its target version and publish event identically.
              AND e.published_at = target.created_at
            ORDER BY e.published_at DESC, e.id DESC
            LIMIT 1
            """
            )
        )
        .mappings()
        .first()
    )
    if publish_event is not None:
        untracked_subscription = connection.execute(
            sa.text(
                """
                SELECT 1
                FROM organization_subscriptions AS subscription
                WHERE subscription.plan_version_id = :to_version_id
                  AND NOT EXISTS (
                      SELECT 1
                      FROM organization_subscription_migrations AS migration
                      WHERE migration.publish_event_id = :publish_event_id
                        AND migration.organization_subscription_id = subscription.id
                  )
                LIMIT 1
                """
            ),
            {
                "to_version_id": publish_event["to_plan_version_id"],
                "publish_event_id": publish_event["id"],
            },
        ).first()
        if untracked_subscription is not None:
            raise RuntimeError(
                "Cannot downgrade unlimited Free agents while subscriptions use the new version"
            )

        connection.execute(
            sa.text(
                """
                UPDATE organization_subscriptions AS subscription
                SET plan_version_id = :from_version_id,
                    updated_at = NOW()
                FROM organization_subscription_migrations AS migration
                WHERE migration.publish_event_id = :publish_event_id
                  AND migration.organization_subscription_id = subscription.id
                  AND migration.to_plan_version_id = :to_version_id
                  AND migration.status = 'migrated'
                  AND migration.migration_type = 'auto'
                  AND subscription.plan_version_id = :to_version_id
                """
            ),
            {
                "from_version_id": publish_event["from_plan_version_id"],
                "to_version_id": publish_event["to_plan_version_id"],
                "publish_event_id": publish_event["id"],
            },
        )
        result = connection.execute(
            sa.text(
                """
                UPDATE plan_versions
                SET is_current_for_signup = false,
                    status = 'deprecated',
                    updated_at = NOW()
                WHERE id = :version_id
                  AND is_current_for_signup = true
                """
            ),
            {"version_id": publish_event["to_plan_version_id"]},
        )
        if result.rowcount == 1:
            connection.execute(
                sa.text(
                    """
                    UPDATE plan_versions
                    SET is_current_for_signup = true,
                        status = 'published',
                        updated_at = NOW()
                    WHERE id = :version_id
                    """
                ),
                {"version_id": publish_event["from_plan_version_id"]},
            )
    connection.execute(
        sa.text(
            """
            UPDATE entitlement_definitions
            SET default_when_absent = '{"type":"integer","value":0}'::jsonb,
                updated_at = NOW()
            WHERE key = 'max_agents'
            """
        )
    )
