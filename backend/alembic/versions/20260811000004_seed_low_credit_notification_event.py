"""Seed the built-in low-credit notification event."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260811000004"
down_revision: Union[str, None] = "20260811000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure the billing warning can resolve its built-in template."""
    op.execute(
        """
        INSERT INTO notification_events (
            name, description, event_key, category, is_enabled,
            default_template_id, metadata
        ) VALUES (
            'Low Credit Balance',
            'Warn organization admins when the shared credit balance reaches 20%, 15%, or 5% of the plan allowance.',
            'credits.low_balance',
            'billing',
            TRUE,
            NULL,
            '{"built_in_template": true, "variables": ["user_name", "current_credits", "threshold_percent", "organization_name", "purchase_credits_url", "app_name"]}'::jsonb
        )
        ON CONFLICT (event_key) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            is_enabled = TRUE,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """
    )


def downgrade() -> None:
    """Remove only the seeded billing event when it has no dependent logs."""
    op.execute(
        "DELETE FROM notification_events WHERE event_key = 'credits.low_balance'"
    )
