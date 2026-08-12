"""Align the seeded low-credit event with the 20/10/5 warning policy."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260812000003"
down_revision: Union[str, None] = "20260812000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update the existing built-in event without requiring a reseed command."""
    op.execute(
        """
        UPDATE notification_events
        SET description = 'Warn organization admins when the shared credit balance reaches 20%, 10%, or 5% of the plan allowance.',
            metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{thresholds}',
                '[20, 10, 5]'::jsonb,
                TRUE
            ),
            updated_at = NOW()
        WHERE event_key = 'credits.low_balance'
        """
    )


def downgrade() -> None:
    """Restore the previous event description and threshold metadata."""
    op.execute(
        """
        UPDATE notification_events
        SET description = 'Warn organization admins when the shared credit balance reaches 20%, 15%, or 5% of the plan allowance.',
            metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{thresholds}',
                '[20, 15, 5]'::jsonb,
                TRUE
            ),
            updated_at = NOW()
        WHERE event_key = 'credits.low_balance'
        """
    )
