"""Add platform-admin WhatsApp lead notification settings.

Revision ID: 20261001000001
Revises: 20260930000001
Create Date: 2026-10-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261001000001"
down_revision: Union[str, Sequence[str], None] = "20260930000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add an explicit opt-in and E.164 WhatsApp destination."""
    op.add_column(
        "platform_notification_settings",
        sa.Column("platform_admin_whatsapp_phone", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "platform_notification_settings",
        sa.Column(
            "platform_admin_whatsapp_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Remove WhatsApp notification settings."""
    op.drop_column(
        "platform_notification_settings",
        "platform_admin_whatsapp_notifications_enabled",
    )
    op.drop_column("platform_notification_settings", "platform_admin_whatsapp_phone")
