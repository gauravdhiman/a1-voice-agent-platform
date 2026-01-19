"""add_last_refreshed_at_to_agent_tools

Revision ID: 20260118000001
Revises: 20260111000001
Create Date: 2026-01-18 00:00:01.000000

This migration adds a `last_refreshed_at` column to track when OAuth tokens
were last refreshed by the auto-refresh service.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260118000001"
down_revision: Union[str, None] = "20260111000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_tools",
        sa.Column(
            "last_refreshed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when OAuth tokens were last auto-refreshed",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_tools", "last_refreshed_at")
