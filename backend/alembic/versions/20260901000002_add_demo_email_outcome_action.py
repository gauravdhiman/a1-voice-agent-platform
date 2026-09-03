"""Allow independent email actions in public demo receipts.

Email delivery is recorded as a separate allowlisted action when an agent
chooses an attached Gmail or Resend tool. This does not make email a provider
tool dependency; it only gives the demo receipt a truthful presentation of the
independent tool call.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260901000002"
down_revision: Union[str, None] = "20260901000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Permit email delivery as a visitor-visible demo action."""
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


def downgrade() -> None:
    """Restore the original primary-workflow action constraint."""
    op.drop_constraint(
        "ck_demo_outcome_receipts_action_type",
        "demo_outcome_receipts",
        type_="check",
    )
    op.create_check_constraint(
        "ck_demo_outcome_receipts_action_type",
        "demo_outcome_receipts",
        "action_type IN ('lead_capture', 'appointment_booking')",
    )
