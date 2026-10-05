"""Set the toll-free rental rate to the reviewed launch price."""

from typing import Sequence, Union

from alembic import op

revision: str = "20261001000002"
down_revision: Union[str, None] = "20261001000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set a toll-free rental to 120 credits, or $3 at 40 credits per dollar."""
    op.execute(
        """
        UPDATE credit_events
        SET credit_cost = 120,
            description = 'An active toll-free phone number is charged once per rental month at 120 credits ($3 at the launch credit rate).',
            is_active = TRUE
        WHERE name = 'phone_number_toll_free_month'
        """
    )


def downgrade() -> None:
    """Restore the earlier 500-credit toll-free rate."""
    op.execute(
        """
        UPDATE credit_events
        SET credit_cost = 500,
            description = 'An active toll-free phone number is charged once for each rental month.',
            is_active = TRUE
        WHERE name = 'phone_number_toll_free_month'
          AND credit_cost = 120
        """
    )
