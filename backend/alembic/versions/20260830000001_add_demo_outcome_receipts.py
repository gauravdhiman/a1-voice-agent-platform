"""Store short-lived, visitor-safe results for public demo workflows.

The receipt is deliberately not an observability trace. It contains only the
allowlisted fields needed to show a single visitor what the demo changed in a
provider. Access is through a signed token and service-role queries; no public
database policy is created.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830000001"
down_revision: Union[str, None] = "20260828000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the isolated demo receipt table and its service-role boundary."""
    op.create_table(
        "demo_outcome_receipts",
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
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "captured_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "provider_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + interval '7 days'"),
        ),
        sa.CheckConstraint(
            "action_type IN ('lead_capture', 'appointment_booking')",
            name="ck_demo_outcome_receipts_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'pending')",
            name="ck_demo_outcome_receipts_status",
        ),
    )
    op.create_index(
        "ix_demo_outcome_receipts_session_created",
        "demo_outcome_receipts",
        ["session_id", "created_at"],
    )
    op.create_index(
        "ix_demo_outcome_receipts_expires_at",
        "demo_outcome_receipts",
        ["expires_at"],
    )
    op.execute("ALTER TABLE demo_outcome_receipts ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE demo_outcome_receipts FROM PUBLIC")
    op.execute("GRANT ALL ON TABLE demo_outcome_receipts TO service_role")


def downgrade() -> None:
    """Remove the demo receipt table and indexes."""
    op.drop_index(
        "ix_demo_outcome_receipts_expires_at", table_name="demo_outcome_receipts"
    )
    op.drop_index(
        "ix_demo_outcome_receipts_session_created",
        table_name="demo_outcome_receipts",
    )
    op.drop_table("demo_outcome_receipts")
