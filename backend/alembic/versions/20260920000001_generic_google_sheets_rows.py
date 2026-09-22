"""Replace the Jordan-only Sheets action with generic row operations.

The native Google_Sheets catalog entry is now the supported Sheets integration
for new attachments. The old catalog row is retired, while saved legacy links
remain runtime-compatible until an administrator moves them to the generic
attachment.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260920000001"
down_revision: Union[str, None] = "9f2c4a7b1e3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow generic Sheets row receipts and retire the lead-only catalog row."""
    op.drop_constraint(
        "ck_demo_outcome_receipts_action_type",
        "demo_outcome_receipts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_demo_outcome_receipts_action_type",
        "demo_outcome_receipts",
        "action_type IN ('lead_capture', 'appointment_booking', 'email_delivery', 'sheet_row_created')",
    )
    op.execute(
        """
        UPDATE platform_tools
        SET is_active = FALSE
        WHERE name = 'Google_Sheets_lead_capture'
        """
    )


def downgrade() -> None:
    """Restore the previous receipt vocabulary and legacy catalog visibility."""
    op.execute(
        """
        UPDATE demo_outcome_receipts
        SET action_type = 'lead_capture'
        WHERE action_type = 'sheet_row_created'
        """
    )
    op.drop_constraint(
        "ck_demo_outcome_receipts_action_type",
        "demo_outcome_receipts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_demo_outcome_receipts_action_type",
        "demo_outcome_receipts",
        "action_type IN ('lead_capture', 'appointment_booking', 'email_delivery')",
    )
    op.execute(
        """
        UPDATE platform_tools
        SET is_active = TRUE
        WHERE name = 'Google_Sheets_lead_capture'
        """
    )
