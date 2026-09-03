"""Private interest-lead capture for the controlled-SaaS funnel.

Visitor-submitted interest (``POST /api/v1/public/leads``) is the private
source of truth for follow-up; demo-safe subsets are forwarded to public
proof destinations (shared Sheet/Calendar) by the demo workflow, never the
reverse. Rows are service-role only: RLS enabled, no public policy.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260903000001"
down_revision: Union[str, None] = "20260902000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the isolated interest-leads table and service-role boundary."""
    op.create_table(
        "interest_leads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("business_name", sa.String(length=160), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("vertical", sa.String(length=40), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'request-demo'"),
        ),
        sa.Column("demo_slug", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('new', 'contacted', 'invited', 'converted', 'dropped')",
            name="ck_interest_leads_status",
        ),
        sa.CheckConstraint(
            "source IN ('request-demo', 'outcome-form', 'demo-call', 'manual')",
            name="ck_interest_leads_source",
        ),
    )
    op.create_index(
        "ix_interest_leads_status_created",
        "interest_leads",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_interest_leads_email",
        "interest_leads",
        ["email"],
    )
    op.execute("ALTER TABLE interest_leads ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE interest_leads FROM PUBLIC")
    op.execute("GRANT ALL ON TABLE interest_leads TO service_role")


def downgrade() -> None:
    """Remove the interest-leads table and indexes."""
    op.drop_index("ix_interest_leads_email", table_name="interest_leads")
    op.drop_index("ix_interest_leads_status_created", table_name="interest_leads")
    op.drop_table("interest_leads")
