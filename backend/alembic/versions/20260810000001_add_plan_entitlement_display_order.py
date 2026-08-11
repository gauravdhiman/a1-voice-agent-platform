"""Add explicit display ordering to plan-version entitlements.

Revision ID: 20260810000001
Revises: 20260809000003
Create Date: 2026-08-10

Entitlement values and membership remain immutable after publish, while this
column allows administrators to maintain the order in which card rows appear.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260810000001"
down_revision: Union[str, None] = "20260809000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add and backfill the stable plan entitlement display sequence."""
    op.add_column(
        "plan_version_entitlements",
        sa.Column(
            "display_order", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
    )
    op.execute(
        """
        WITH ordered_entitlements AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY plan_version_id
                    ORDER BY created_at, id
                ) - 1 AS display_order
            FROM plan_version_entitlements
        )
        UPDATE plan_version_entitlements AS entitlements
        SET display_order = ordered_entitlements.display_order
        FROM ordered_entitlements
        WHERE entitlements.id = ordered_entitlements.id
        """
    )
    op.alter_column(
        "plan_version_entitlements",
        "display_order",
        server_default=None,
    )
    op.create_index(
        "idx_plan_version_entitlements_display_order",
        "plan_version_entitlements",
        ["plan_version_id", "display_order"],
    )


def downgrade() -> None:
    """Remove the plan entitlement display sequence and its lookup index."""
    op.drop_index(
        "idx_plan_version_entitlements_display_order",
        table_name="plan_version_entitlements",
    )
    op.drop_column("plan_version_entitlements", "display_order")
