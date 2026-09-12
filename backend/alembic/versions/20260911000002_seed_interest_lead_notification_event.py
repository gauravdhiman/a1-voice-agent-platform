"""Seed the built-in interest-lead notification event."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260911000002"
down_revision: Union[str, None] = "20260911000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure lead alerts can use the built-in email template after deploy."""
    op.execute(
        """
        INSERT INTO notification_events (
            name, description, event_key, category, is_enabled,
            default_template_id, metadata
        ) VALUES (
            'Interest Lead Submitted',
            'Notify the configured platform administrator when a visitor submits a demo or interest form.',
            'lead.interest_submitted',
            'system',
            TRUE,
            NULL,
            '{"built_in_template": true, "variables": ["lead_name", "business_name", "lead_email", "lead_phone", "vertical", "message", "source", "demo_slug", "submitted_at", "interests_url", "app_name"]}'::jsonb
        )
        ON CONFLICT (event_key) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove the built-in lead event when no dependent logs remain."""
    op.execute(
        "DELETE FROM notification_events WHERE event_key = 'lead.interest_submitted'"
    )
