"""Add purchased credit pool and low-credit notification tracking.

Revision ID: 20260807000005
Revises: 20260807000004
Create Date: 2026-08-07

Two-pool credit model:
- ``organizations.credit_balance`` — plan credits (granted per billing period,
  expire at period end; replaced on renewal).
- ``organizations.purchased_credit_balance`` — one-off purchased credit packs
  (never expire). Consumption always drains plan credits first, then purchased.

Also adds ``organizations.low_credit_threshold_notified`` to make low-balance
emails fire at most once per percentage threshold per billing cycle.

Backfill: attribute as much of each org's current balance to the purchased
pool as its ledger supports (sum of PURCHASED grants with no expiry), then
reduce the plan pool by that amount.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260807000005"
down_revision: Union[str, None] = "20260807000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("purchased_credit_balance", sa.INTEGER(), server_default="0", nullable=False),
    )
    op.add_column(
        "organizations",
        sa.Column("low_credit_threshold_notified", sa.INTEGER(), nullable=True),
    )

    op.execute(
        """
        UPDATE organizations o
        SET purchased_credit_balance = LEAST(sub.purchased, o.credit_balance),
            credit_balance = GREATEST(
                0,
                o.credit_balance - LEAST(sub.purchased, o.credit_balance)
            )
        FROM (
            SELECT organization_id, COALESCE(SUM(amount), 0) AS purchased
            FROM credit_transactions
            WHERE source = 'purchase'
              AND transaction_type = 'purchased'
              AND expires_at IS NULL
            GROUP BY organization_id
        ) sub
        WHERE o.id = sub.organization_id
        """
    )


def downgrade() -> None:
    # Cannot un-attribute the split pools reliably; restore single-pool total.
    op.execute(
        """
        UPDATE organizations
        SET credit_balance = credit_balance + purchased_credit_balance
        """
    )
    op.drop_column("organizations", "low_credit_threshold_notified")
    op.drop_column("organizations", "purchased_credit_balance")
