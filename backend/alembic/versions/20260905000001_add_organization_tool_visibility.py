"""Add organization-level visibility overrides for published tools.

Published platform tools are visible to every organization by default. This
table stores only the organization-specific override, so publishing a new
tool does not require backfilling a row for every organization.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260905000001"
down_revision: Union[str, None] = "20260902000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the sparse organization-to-platform-tool visibility table."""
    op.create_table(
        "organization_tool_visibility",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "organization_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tool_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "is_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.UniqueConstraint(
            "organization_id",
            "tool_id",
            name="uq_organization_tool_visibility",
        ),
    )
    op.create_index(
        "ix_organization_tool_visibility_organization_id",
        "organization_tool_visibility",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_tool_visibility_tool_id",
        "organization_tool_visibility",
        ["tool_id"],
    )
    op.execute("ALTER TABLE organization_tool_visibility ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Remove organization-level platform-tool visibility overrides."""
    op.drop_index(
        "ix_organization_tool_visibility_tool_id",
        table_name="organization_tool_visibility",
    )
    op.drop_index(
        "ix_organization_tool_visibility_organization_id",
        table_name="organization_tool_visibility",
    )
    op.drop_table("organization_tool_visibility")
