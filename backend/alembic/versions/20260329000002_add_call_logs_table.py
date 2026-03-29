"""add call_logs table

Revision ID: 20260329000002
Revises: 20260329000001
Create Date: 2026-03-29 00:00:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260329000002"
down_revision: Union[str, None] = "20260329000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("call_sid", sa.String(length=100), nullable=False, unique=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("voice_agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("caller_number", sa.String(length=30), nullable=True),
        sa.Column("called_number", sa.String(length=30), nullable=True),
        # status: initiated, ringing, answered, completed, missed, failed, busy, no-answer
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'initiated'"),
        ),
        sa.Column("duration", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_call_logs_organization_id", "call_logs", ["organization_id"])
    op.create_index("ix_call_logs_agent_id", "call_logs", ["agent_id"])
    op.create_index("ix_call_logs_created_at", "call_logs", ["created_at"])
    op.create_index("ix_call_logs_status", "call_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_call_logs_status", table_name="call_logs")
    op.drop_index("ix_call_logs_created_at", table_name="call_logs")
    op.drop_index("ix_call_logs_agent_id", table_name="call_logs")
    op.drop_index("ix_call_logs_organization_id", table_name="call_logs")
    op.drop_table("call_logs")
