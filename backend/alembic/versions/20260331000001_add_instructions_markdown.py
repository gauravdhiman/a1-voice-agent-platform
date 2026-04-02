"""add instructions_markdown column to voice_agents

Revision ID: 20260331000001
Revises: 20260329000002
Create Date: 2026-03-31 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260331000001"
down_revision: Union[str, None] = "20260329000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_agents",
        sa.Column("instructions_markdown", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voice_agents", "instructions_markdown")
