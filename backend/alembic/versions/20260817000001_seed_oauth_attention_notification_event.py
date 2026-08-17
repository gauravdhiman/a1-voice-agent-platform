"""Seed the OAuth connection-attention notification event."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260817000001"
down_revision: Union[str, None] = "20260814000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure OAuth renewal reminders can resolve their built-in template."""
    op.execute(
        """
        INSERT INTO notification_events (
            name, description, event_key, category, is_enabled,
            default_template_id, metadata
        ) VALUES (
            'Tool OAuth Reauthorization Required',
            'Notify organization administrators when a tool connection is expiring, expired, or cannot be renewed automatically.',
            'tools.oauth_reauthorization_required',
            'auth',
            TRUE,
            NULL,
            '{"built_in_template": true, "variables": ["user_name", "tool_name", "agent_name", "organization_name", "status_text", "expires_at", "reason", "action_url", "app_name"]}'::jsonb
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
    """Remove only the built-in OAuth attention event."""
    op.execute(
        """
        DELETE FROM notification_events
        WHERE event_key = 'tools.oauth_reauthorization_required'
        """
    )
