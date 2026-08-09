"""Add recording encryption and retention metadata columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809000002"
down_revision: Union[str, None] = "20260809000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add explicit fields used by recording cleanup and key strategy audits."""
    op.add_column(
        "call_artifacts",
        sa.Column(
            "encryption_mode",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'provider_managed'"),
        ),
    )
    op.add_column(
        "call_artifacts",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_call_artifacts_retention_expires_at",
        "call_artifacts",
        ["retention_expires_at"],
    )


def downgrade() -> None:
    """Remove recording retention metadata columns."""
    op.drop_index("ix_call_artifacts_retention_expires_at", table_name="call_artifacts")
    op.drop_column("call_artifacts", "retention_expires_at")
    op.drop_column("call_artifacts", "encryption_mode")
