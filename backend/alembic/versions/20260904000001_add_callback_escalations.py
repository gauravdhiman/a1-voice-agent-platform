"""Owner-visible callback requests from soft escalation.

Production voice calls (never demos) record one row per accepted
``request_human_callback`` tool result via the voice runtime hook, so the
owner workflow (list/acknowledge/resolve) survives the call. Service-role
only: RLS enabled, no public policy.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260904000001"
down_revision: Union[str, None] = "20260903000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the callback escalations table and service-role boundary."""
    op.create_table(
        "callback_escalations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
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
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("caller_phone", sa.String(length=32), nullable=False),
        sa.Column("caller_name", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "urgency",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'normal'"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column(
            "notified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "urgency IN ('normal', 'urgent')",
            name="ck_callback_escalations_urgency",
        ),
        sa.CheckConstraint(
            "status IN ('new', 'acknowledged', 'resolved')",
            name="ck_callback_escalations_status",
        ),
    )
    op.create_index(
        "ix_callback_escalations_org_status",
        "callback_escalations",
        ["organization_id", "status", "created_at"],
    )
    op.execute("ALTER TABLE callback_escalations ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE callback_escalations FROM PUBLIC")
    op.execute("GRANT ALL ON TABLE callback_escalations TO service_role")


def downgrade() -> None:
    """Remove the callback escalations table and indexes."""
    op.drop_index(
        "ix_callback_escalations_org_status", table_name="callback_escalations"
    )
    op.drop_table("callback_escalations")
