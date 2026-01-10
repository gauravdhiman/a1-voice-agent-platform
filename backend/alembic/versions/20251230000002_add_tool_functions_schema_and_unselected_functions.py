"""add_tool_functions_schema_and_unselected_functions

Revision ID: 20251230000002
Revises: 20251220000000
Create Date: 2025-12-30 00:00:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251230000002"
down_revision: Union[str, None] = "20251220000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_tools",
        sa.Column(
            "tool_functions_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.add_column(
        "agent_tools",
        sa.Column("unselected_functions", postgresql.ARRAY(sa.String()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_tools", "tool_functions_schema")
    op.drop_column("agent_tools", "unselected_functions")
