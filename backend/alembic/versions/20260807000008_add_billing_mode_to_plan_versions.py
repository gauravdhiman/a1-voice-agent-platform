"""Add explicit payment mode to immutable plan versions.

The billing mode is the authoritative activation decision. It prevents runtime
code from inferring free versus paid behavior from price amounts, Stripe IDs, or
marketing names. Existing versions are backfilled from the current catalog
slug once, during migration; runtime behavior uses this column thereafter.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260807000008"
down_revision: Union[str, None] = "20260807000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add and backfill the required plan-version billing mode."""
    op.add_column(
        "plan_versions",
        sa.Column(
            "billing_mode",
            sa.VARCHAR(length=20),
            nullable=True,
            comment="Authoritative activation path: free or paid",
        ),
    )

    op.execute(
        """
        UPDATE plan_versions pv
        SET billing_mode = CASE
            WHEN pp.slug = 'free' THEN 'free'
            ELSE 'paid'
        END
        FROM plan_products pp
        WHERE pp.id = pv.plan_product_id
        """
    )

    op.alter_column("plan_versions", "billing_mode", nullable=False)
    op.create_check_constraint(
        "ck_plan_versions_billing_mode",
        "plan_versions",
        "billing_mode IN ('free', 'paid')",
    )
    op.create_index(
        "idx_plan_versions_billing_mode",
        "plan_versions",
        ["billing_mode"],
    )


def downgrade() -> None:
    """Remove the explicit plan-version billing mode."""
    op.drop_index("idx_plan_versions_billing_mode", table_name="plan_versions")
    op.drop_constraint("ck_plan_versions_billing_mode", "plan_versions", type_="check")
    op.drop_column("plan_versions", "billing_mode")
