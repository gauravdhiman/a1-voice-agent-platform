"""Add plan versioning, entitlement catalog, and plan_version_id on subscriptions.

Revision ID: 20260807000002
Revises: 20260807000001
Create Date: 2026-08-07

Introduces immutable plan versions with sparse entitlements per version.
Backfills existing subscription_plans rows to plan_products + plan_versions v1
and links organization_subscriptions.plan_version_id.

See docs/03_implementation/plan_entitlements_and_limits.md
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260807000002"
down_revision: Union[str, None] = "20260807000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Plan product families ---
    op.create_table(
        "plan_products",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.VARCHAR(length=100), nullable=False),
        sa.Column("display_name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("sort_order", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # --- Immutable plan versions ---
    op.create_table(
        "plan_versions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("plan_product_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.INTEGER(), nullable=False),
        sa.Column(
            "status",
            sa.VARCHAR(length=20),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("display_label", sa.VARCHAR(length=200), nullable=True),
        sa.Column("price_amount_cents", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column(
            "currency",
            sa.VARCHAR(length=3),
            server_default="USD",
            nullable=False,
        ),
        sa.Column(
            "billing_interval",
            sa.VARCHAR(length=20),
            server_default="monthly",
            nullable=False,
        ),
        sa.Column("trial_period_days", sa.INTEGER(), nullable=True),
        sa.Column("stripe_product_id", sa.VARCHAR(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.VARCHAR(length=255), nullable=True),
        sa.Column(
            "is_current_for_signup",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("published_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "legacy_subscription_plan_id",
            sa.UUID(),
            nullable=True,
            comment="Backfill link to subscription_plans.id",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_product_id"], ["plan_products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_product_id", "version_number"),
        sa.UniqueConstraint("stripe_price_id"),
    )
    op.create_index("idx_plan_versions_product_id", "plan_versions", ["plan_product_id"])
    op.create_index("idx_plan_versions_stripe_price_id", "plan_versions", ["stripe_price_id"])

    # --- Entitlement catalog ---
    op.create_table(
        "entitlement_definitions",
        sa.Column("key", sa.VARCHAR(length=100), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=20), nullable=False),
        sa.Column("display_name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("value_type", sa.VARCHAR(length=30), nullable=False),
        sa.Column("unit", sa.VARCHAR(length=50), nullable=True),
        sa.Column(
            "validation_schema",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("enforcement_handler", sa.VARCHAR(length=100), nullable=False),
        sa.Column(
            "default_enforcement",
            sa.VARCHAR(length=20),
            server_default="hard",
            nullable=False,
        ),
        sa.Column("default_when_absent", postgresql.JSONB(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # --- Sparse entitlements per version ---
    op.create_table(
        "plan_version_entitlements",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("plan_version_id", sa.UUID(), nullable=False),
        sa.Column("entitlement_key", sa.VARCHAR(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["entitlement_key"], ["entitlement_definitions.key"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_version_id", "entitlement_key"),
    )

    # --- Publish / migration tracking (Phase 2+) ---
    op.create_table(
        "plan_version_publish_events",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("from_plan_version_id", sa.UUID(), nullable=True),
        sa.Column("to_plan_version_id", sa.UUID(), nullable=False),
        sa.Column("migration_mode", sa.VARCHAR(length=50), nullable=False),
        sa.Column("grace_period_days", sa.INTEGER(), nullable=True),
        sa.Column(
            "auto_migrate_on_expiry",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "allow_indefinite_legacy",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "stripe_migration_timing",
            sa.VARCHAR(length=30),
            server_default="at_period_end",
            nullable=False,
        ),
        sa.Column("compliance_policy", sa.VARCHAR(length=30), nullable=True),
        sa.Column("published_by", sa.UUID(), nullable=True),
        sa.Column(
            "published_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_plan_version_id"], ["plan_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["to_plan_version_id"], ["plan_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "organization_subscription_migrations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_subscription_id", sa.UUID(), nullable=False),
        sa.Column("publish_event_id", sa.UUID(), nullable=False),
        sa.Column("from_plan_version_id", sa.UUID(), nullable=False),
        sa.Column("to_plan_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.VARCHAR(length=30),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("grace_period_ends_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notified_at", postgresql.JSONB(), nullable=True),
        sa.Column("migrated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("migration_type", sa.VARCHAR(length=30), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_subscription_id"],
            ["organization_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["publish_event_id"],
            ["plan_version_publish_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Link subscriptions to plan versions ---
    op.add_column(
        "organization_subscriptions",
        sa.Column("plan_version_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_org_subscriptions_plan_version_id",
        "organization_subscriptions",
        "plan_versions",
        ["plan_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_org_subscriptions_plan_version_id",
        "organization_subscriptions",
        ["plan_version_id"],
    )

    _seed_entitlement_definitions()
    _seed_free_plan()
    _backfill_legacy_plans()


def _seed_entitlement_definitions() -> None:
    """Seed platform entitlement catalog."""
    op.execute(
        """
        INSERT INTO entitlement_definitions
            (key, kind, display_name, value_type, unit, enforcement_handler,
             default_enforcement, default_when_absent, description)
        VALUES
            ('max_agents', 'limit', 'Maximum agents', 'integer', 'count',
             'limit.max_count', 'hard', '{"type": "integer", "value": 0}'::jsonb,
             'Maximum voice agents per organization'),
            ('max_org_members', 'limit', 'Maximum members', 'integer', 'count',
             'limit.max_count', 'hard', '{"type": "integer", "value": 1}'::jsonb,
             'Maximum organization members'),
            ('max_phone_numbers', 'limit', 'Maximum phone numbers', 'integer', 'count',
             'limit.max_count', 'hard', '{"type": "integer", "value": 0}'::jsonb,
             'Maximum purchased phone numbers'),
            ('max_concurrent_calls', 'limit', 'Maximum concurrent calls', 'integer', 'count',
             'limit.max_count', 'hard', '{"type": "integer", "value": 1}'::jsonb,
             'Maximum simultaneous voice sessions'),
            ('included_credits_monthly', 'limit', 'Included credits per month', 'integer', 'credits',
             'limit.max_count', 'none', NULL,
             'Credits granted each billing period'),
            ('payg_credit_cap', 'limit', 'PAYG credit cap', 'integer', 'credits',
             'limit.max_count', 'hard', NULL,
             'Maximum negative balance when PAYG enabled'),
            ('payg_enabled', 'feature', 'Pay as you go', 'boolean', NULL,
             'feature.flag', 'hard', '{"type": "boolean", "value": false}'::jsonb,
             'Allow usage after included credits exhausted'),
            ('credit_topup_enabled', 'feature', 'Credit top-up', 'boolean', NULL,
             'feature.flag', 'hard', '{"type": "boolean", "value": true}'::jsonb,
             'Allow purchasing credit packs'),
            ('premium_tools', 'feature', 'Premium integrations', 'boolean', NULL,
             'feature.flag', 'hard', '{"type": "boolean", "value": false}'::jsonb,
             'Includes Gmail, Google Sheets, HubSpot lead capture, and Cal.com scheduling.'),
            ('embed_widget', 'feature', 'Embed call widget', 'boolean', NULL,
             'feature.flag', 'hard', '{"type": "boolean", "value": false}'::jsonb,
             'Public embeddable call button'),
            ('custom_branding', 'feature', 'Custom branding', 'boolean', NULL,
             'feature.flag', 'hard', '{"type": "boolean", "value": false}'::jsonb,
             'White-label public org page')
        ON CONFLICT (key) DO NOTHING
        """
    )


def _seed_free_plan() -> None:
    """Default free tier for orgs without an active paid subscription."""
    op.execute(
        """
        INSERT INTO plan_products (id, slug, display_name, description, sort_order, is_active)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'free',
            'Free',
            'Default free tier for organizations without an active subscription',
            0,
            true
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO plan_versions (
            id, plan_product_id, version_number, status, display_label,
            price_amount_cents, currency, billing_interval,
            is_current_for_signup, published_at
        )
        VALUES (
            '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000001',
            1,
            'published',
            'Free v1',
            0,
            'USD',
            'monthly',
            true,
            NOW()
        )
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO plan_version_entitlements (plan_version_id, entitlement_key, value)
        VALUES
            (
                '00000000-0000-0000-0000-000000000002',
                'max_agents',
                '{"type": "integer", "value": 0}'::jsonb
            ),
            (
                '00000000-0000-0000-0000-000000000002',
                'max_org_members',
                '{"type": "integer", "value": 1}'::jsonb
            )
        ON CONFLICT DO NOTHING
        """
    )


def _backfill_legacy_plans() -> None:
    """Migrate subscription_plans rows to plan_versions v1 and link subscriptions."""
    op.execute(
        """
        INSERT INTO plan_products (slug, display_name, description, sort_order, is_active)
        SELECT
            lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g')),
            name,
            description,
            10,
            is_active
        FROM subscription_plans
        ON CONFLICT (slug) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO plan_versions (
            plan_product_id,
            version_number,
            status,
            display_label,
            price_amount_cents,
            currency,
            billing_interval,
            trial_period_days,
            stripe_product_id,
            stripe_price_id,
            is_current_for_signup,
            published_at,
            legacy_subscription_plan_id
        )
        SELECT
            pp.id,
            1,
            CASE WHEN sp.is_active THEN 'published' ELSE 'deprecated' END,
            sp.name || ' v1',
            sp.price_amount,
            sp.currency,
            sp.interval,
            sp.trial_period_days,
            sp.stripe_product_id,
            sp.stripe_price_id,
            sp.is_active,
            NOW(),
            sp.id
        FROM subscription_plans sp
        JOIN plan_products pp ON pp.slug = lower(regexp_replace(sp.name, '[^a-zA-Z0-9]+', '-', 'g'))
        ON CONFLICT DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO plan_version_entitlements (plan_version_id, entitlement_key, value)
        SELECT
            pv.id,
            'included_credits_monthly',
            jsonb_build_object('type', 'integer', 'value', sp.included_credits)
        FROM plan_versions pv
        JOIN subscription_plans sp ON sp.id = pv.legacy_subscription_plan_id
        WHERE sp.included_credits > 0
        ON CONFLICT DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO plan_version_entitlements (plan_version_id, entitlement_key, value)
        SELECT
            pv.id,
            'max_org_members',
            jsonb_build_object('type', 'integer', 'value', sp.max_users)
        FROM plan_versions pv
        JOIN subscription_plans sp ON sp.id = pv.legacy_subscription_plan_id
        WHERE sp.max_users IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO plan_version_entitlements (plan_version_id, entitlement_key, value)
        SELECT
            pv.id,
            'max_agents',
            jsonb_build_object('type', 'integer', 'value', (sp.features->>'agents')::int)
        FROM plan_versions pv
        JOIN subscription_plans sp ON sp.id = pv.legacy_subscription_plan_id
        WHERE sp.features ? 'agents'
          AND (sp.features->>'agents') ~ '^[0-9]+$'
        ON CONFLICT DO NOTHING
        """
    )

    op.execute(
        """
        UPDATE organization_subscriptions os
        SET plan_version_id = pv.id
        FROM plan_versions pv
        WHERE pv.legacy_subscription_plan_id = os.subscription_plan_id
          AND os.plan_version_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("idx_org_subscriptions_plan_version_id", "organization_subscriptions")
    op.drop_constraint(
        "fk_org_subscriptions_plan_version_id",
        "organization_subscriptions",
        type_="foreignkey",
    )
    op.drop_column("organization_subscriptions", "plan_version_id")

    op.drop_table("organization_subscription_migrations")
    op.drop_table("plan_version_publish_events")
    op.drop_table("plan_version_entitlements")
    op.drop_table("entitlement_definitions")
    op.drop_index("idx_plan_versions_stripe_price_id", "plan_versions")
    op.drop_index("idx_plan_versions_product_id", "plan_versions")
    op.drop_table("plan_versions")
    op.drop_table("plan_products")
