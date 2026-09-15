"""Store visitor star ratings for public demo calls.

Ratings are PII-free (demo slug plus 1-5 score, no names or contact
details) and are recorded per voice session so repeat taps update one row
instead of ballot-stuffing. Like demo outcome receipts, the table is
service-role only with no public database policy; visitors write through
the signed receipt-token endpoint and platform admins read through the
service-role API.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9f2c4a7b1e3d"
down_revision: Union[str, None] = "20260911000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the demo feedback table and its service-role boundary."""
    op.create_table(
        "demo_feedback",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            sa.String(length=100),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("voice_agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("demo_slug", sa.String(length=100), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
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
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_demo_feedback_rating_range",
        ),
    )
    op.create_index(
        "ix_demo_feedback_slug_created",
        "demo_feedback",
        ["demo_slug", "created_at"],
    )
    op.execute("ALTER TABLE demo_feedback ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE demo_feedback FROM PUBLIC")
    op.execute("GRANT ALL ON TABLE demo_feedback TO service_role")


def downgrade() -> None:
    """Remove the demo feedback table and indexes."""
    op.drop_index("ix_demo_feedback_slug_created", table_name="demo_feedback")
    op.drop_table("demo_feedback")
