"""Add explicit credit grant cadence to immutable plan versions.

``recurring`` grants are issued at activation and at each billing period. The
free-plan scheduler handles the latter without Stripe; paid plans receive
renewal grants from invoice webhooks. ``one_time`` grants are issued only when
the subscription is first activated.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260808000010"
down_revision: Union[str, None] = "20260807000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add and constrain the plan-version credit grant cadence."""
    op.add_column(
        "plan_versions",
        sa.Column(
            "credit_grant_policy",
            sa.VARCHAR(length=20),
            server_default="recurring",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_plan_versions_credit_grant_policy",
        "plan_versions",
        "credit_grant_policy IN ('recurring', 'one_time')",
    )


def downgrade() -> None:
    """Remove the credit grant cadence column and constraint."""
    op.drop_constraint(
        "ck_plan_versions_credit_grant_policy", "plan_versions", type_="check"
    )
    op.drop_column("plan_versions", "credit_grant_policy")
