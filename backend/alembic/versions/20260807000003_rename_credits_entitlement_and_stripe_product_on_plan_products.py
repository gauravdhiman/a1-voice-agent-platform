"""Rename included credits entitlement; add stripe_product_id on plan_products.

Revision ID: 20260807000003
Revises: 20260807000002
Create Date: 2026-08-07

- Renames entitlement key included_credits_monthly -> included_credits_per_billing_period
- Adds plan_products.stripe_product_id for canonical Stripe Product linkage
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260807000003"
down_revision: Union[str, None] = "20260807000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_KEY = "included_credits_monthly"
NEW_KEY = "included_credits_per_billing_period"


def upgrade() -> None:
    op.add_column(
        "plan_products",
        sa.Column("stripe_product_id", sa.VARCHAR(length=255), nullable=True),
    )
    op.create_index(
        "idx_plan_products_stripe_product_id",
        "plan_products",
        ["stripe_product_id"],
        unique=False,
    )

    # Backfill product Stripe ID from the latest version that has one.
    op.execute(
        """
        UPDATE plan_products pp
        SET stripe_product_id = sub.stripe_product_id
        FROM (
            SELECT DISTINCT ON (plan_product_id)
                plan_product_id,
                stripe_product_id
            FROM plan_versions
            WHERE stripe_product_id IS NOT NULL
            ORDER BY plan_product_id, version_number DESC
        ) sub
        WHERE pp.id = sub.plan_product_id
          AND pp.stripe_product_id IS NULL
        """
    )

    op.execute(
        f"""
        INSERT INTO entitlement_definitions (
            key, kind, display_name, value_type, unit, validation_schema,
            enforcement_handler, default_enforcement, default_when_absent,
            is_active, description, created_at, updated_at
        )
        SELECT
            '{NEW_KEY}',
            kind,
            'Included credits per billing period',
            value_type,
            unit,
            validation_schema,
            enforcement_handler,
            default_enforcement,
            default_when_absent,
            is_active,
            'Credits granted each Stripe billing period (monthly or annual)',
            created_at,
            NOW()
        FROM entitlement_definitions
        WHERE key = '{OLD_KEY}'
        ON CONFLICT (key) DO NOTHING
        """
    )

    op.execute(
        f"""
        UPDATE plan_version_entitlements
        SET entitlement_key = '{NEW_KEY}'
        WHERE entitlement_key = '{OLD_KEY}'
        """
    )

    op.execute(
        f"""
        DELETE FROM entitlement_definitions
        WHERE key = '{OLD_KEY}'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        INSERT INTO entitlement_definitions (
            key, kind, display_name, value_type, unit, validation_schema,
            enforcement_handler, default_enforcement, default_when_absent,
            is_active, description, created_at, updated_at
        )
        SELECT
            '{OLD_KEY}',
            kind,
            'Included credits per month',
            value_type,
            unit,
            validation_schema,
            enforcement_handler,
            default_enforcement,
            default_when_absent,
            is_active,
            'Credits granted each billing period',
            created_at,
            NOW()
        FROM entitlement_definitions
        WHERE key = '{NEW_KEY}'
        ON CONFLICT (key) DO NOTHING
        """
    )

    op.execute(
        f"""
        UPDATE plan_version_entitlements
        SET entitlement_key = '{OLD_KEY}'
        WHERE entitlement_key = '{NEW_KEY}'
        """
    )

    op.execute(
        f"""
        DELETE FROM entitlement_definitions
        WHERE key = '{NEW_KEY}'
        """
    )

    op.drop_index("idx_plan_products_stripe_product_id", table_name="plan_products")
    op.drop_column("plan_products", "stripe_product_id")
