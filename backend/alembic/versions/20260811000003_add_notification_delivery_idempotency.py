"""Track idempotent notification delivery attempts."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260811000003"
down_revision: Union[str, None] = "20260811000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add stable delivery keys and retry-attempt metadata to notification logs."""
    op.add_column(
        "notification_logs",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "notification_logs",
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.add_column(
        "notification_logs",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_notification_logs_idempotency_key",
        "notification_logs",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_notification_logs_idempotency_key",
        "notification_logs",
        ["idempotency_key"],
    )


def downgrade() -> None:
    """Remove notification idempotency and retry metadata."""
    op.drop_index(
        "ix_notification_logs_idempotency_key", table_name="notification_logs"
    )
    op.drop_constraint(
        "uq_notification_logs_idempotency_key", "notification_logs", type_="unique"
    )
    op.drop_column("notification_logs", "last_attempt_at")
    op.drop_column("notification_logs", "attempt_count")
    op.drop_column("notification_logs", "idempotency_key")
