"""Add source metadata to call logs.

Revision ID: 20260906000004
Revises: 20260906000003
Create Date: 2026-09-06 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260906000004"
down_revision: Union[str, None] = "20260906000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source type, URL, and domain columns used for call traceability."""
    op.add_column(
        "call_logs",
        sa.Column("source_type", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "call_logs",
        sa.Column("source_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "call_logs",
        sa.Column("source_domain", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_call_logs_source_type",
        "call_logs",
        ["source_type"],
    )
    op.create_index(
        "ix_call_logs_source_domain",
        "call_logs",
        ["source_domain"],
    )


def downgrade() -> None:
    """Remove call source metadata and its indexes."""
    op.drop_index("ix_call_logs_source_domain", table_name="call_logs")
    op.drop_index("ix_call_logs_source_type", table_name="call_logs")
    op.drop_column("call_logs", "source_domain")
    op.drop_column("call_logs", "source_url")
    op.drop_column("call_logs", "source_type")
