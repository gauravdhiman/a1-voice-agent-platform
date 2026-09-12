"""Add an explicit platform-admin recipient for lead notifications."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260911000001"
down_revision: Union[str, None] = "20260909000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the optional recipient used by public interest notifications."""
    op.add_column(
        "platform_notification_settings",
        sa.Column(
            "platform_admin_email",
            sa.VARCHAR(length=320),
            nullable=True,
            comment="Recipient email for platform-admin interest lead alerts",
        ),
    )


def downgrade() -> None:
    """Remove the platform-admin lead-alert recipient."""
    op.drop_column("platform_notification_settings", "platform_admin_email")
