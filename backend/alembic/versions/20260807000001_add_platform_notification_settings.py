"""Add platform notification settings singleton table.

Revision ID: 20260807000001
Revises: 20260806000001
Create Date: 2026-08-07

Stores platform-admin configurable notification settings:
- Verification email sender (from_email / from_name)
- Telegram bot token (encrypted) and chat ID for admin alerts
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260807000001"
down_revision: Union[str, None] = "20260806000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SINGLETON_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "platform_notification_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "verification_from_email",
            sa.VARCHAR(length=255),
            nullable=True,
            comment="Sender email for verification emails (Resend)",
        ),
        sa.Column(
            "verification_from_name",
            sa.VARCHAR(length=100),
            nullable=True,
            comment="Sender display name for verification emails",
        ),
        sa.Column(
            "telegram_bot_token_encrypted",
            sa.TEXT(),
            nullable=True,
            comment="Encrypted Telegram bot token",
        ),
        sa.Column(
            "telegram_chat_id",
            sa.VARCHAR(length=100),
            nullable=True,
            comment="Telegram chat ID for platform admin alerts",
        ),
        sa.Column(
            "telegram_notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether Telegram admin alerts are enabled",
        ),
        sa.Column(
            "updated_by",
            sa.UUID(),
            nullable=True,
            comment="Last platform admin who updated settings",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        f"INSERT INTO platform_notification_settings (id) VALUES ('{SINGLETON_ID}')"
    )

    op.execute(
        "ALTER TABLE platform_notification_settings ENABLE ROW LEVEL SECURITY"
    )

    op.execute(
        """
        CREATE POLICY "Service role manages platform notification settings"
        ON platform_notification_settings
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
        """
    )


def downgrade() -> None:
    op.execute(
        'DROP POLICY IF EXISTS "Service role manages platform notification settings" '
        "ON platform_notification_settings"
    )
    op.execute(
        "ALTER TABLE platform_notification_settings DISABLE ROW LEVEL SECURITY"
    )
    op.drop_table("platform_notification_settings")
