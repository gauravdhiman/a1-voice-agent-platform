"""Track the single included US local phone number per organization.

Revision ID: 20260930000001
Revises: 20260925000002
Create Date: 2026-09-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260930000001"
down_revision: Union[str, Sequence[str], None] = "20260925000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIVE_STATUSES = (
    "'provisioning', 'purchased', 'active', 'verification_required', 'release_pending'"
)


def upgrade() -> None:
    """Mark one platform-owned US local line as included and price add-ons."""
    op.add_column(
        "phone_numbers",
        sa.Column(
            "is_included_in_plan",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        sa.text(
            f"""
            WITH ranked_numbers AS (
                SELECT candidate.id,
                       ROW_NUMBER() OVER (
                           PARTITION BY candidate.organization_id
                           ORDER BY candidate.purchased_at ASC, candidate.id ASC
                       ) AS number_rank
                FROM phone_numbers AS candidate
                WHERE candidate.management_mode = 'platform_managed'
                  AND candidate.billing_mode = 'platform_rental'
                  AND candidate.phone_number_type = 'local'
                  AND candidate.country_code = 'US'
                  AND candidate.status IN ({ACTIVE_STATUSES})
                  AND EXISTS (
                      SELECT 1
                      FROM organization_subscriptions AS subscription
                      JOIN plan_versions AS version
                        ON version.id = subscription.plan_version_id
                      WHERE subscription.organization_id = candidate.organization_id
                        AND subscription.status IN ('active', 'trial')
                        AND version.billing_mode = 'paid'
                        AND (
                            subscription.cancel_at_period_end IS FALSE
                            OR subscription.current_period_end > CURRENT_TIMESTAMP
                        )
                  )
            )
            UPDATE phone_numbers AS phone
            SET is_included_in_plan = TRUE
            FROM ranked_numbers
            WHERE phone.id = ranked_numbers.id
              AND ranked_numbers.number_rank = 1
            """
        )
    )
    op.execute(
        "UPDATE phone_numbers SET monthly_cost_credits = 0 "
        "WHERE is_included_in_plan IS TRUE"
    )
    op.execute(
        "UPDATE phone_numbers SET monthly_cost_credits = 80 "
        "WHERE management_mode = 'platform_managed' "
        "AND billing_mode = 'platform_rental' "
        "AND phone_number_type = 'local' "
        "AND country_code = 'US' "
        "AND is_included_in_plan IS FALSE "
        "AND status IN ('provisioning', 'purchased', 'active', "
        "'verification_required', 'release_pending')"
    )
    op.create_index(
        "uq_phone_numbers_one_included_us_local_per_org",
        "phone_numbers",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_included_in_plan IS TRUE "
            "AND management_mode = 'platform_managed' "
            "AND billing_mode = 'platform_rental' "
            "AND phone_number_type = 'local' AND country_code = 'US' "
            f"AND status IN ({ACTIVE_STATUSES})"
        ),
    )


def downgrade() -> None:
    """Restore the pre-allowance local-number rental price before dropping it."""
    op.execute(
        "UPDATE phone_numbers SET monthly_cost_credits = 200 "
        "WHERE management_mode = 'platform_managed' "
        "AND billing_mode = 'platform_rental' "
        "AND phone_number_type = 'local' "
        "AND country_code = 'US' "
        "AND (is_included_in_plan IS TRUE OR monthly_cost_credits = 80) "
        f"AND status IN ({ACTIVE_STATUSES})"
    )
    op.drop_index(
        "uq_phone_numbers_one_included_us_local_per_org",
        table_name="phone_numbers",
    )
    op.drop_column("phone_numbers", "is_included_in_plan")
