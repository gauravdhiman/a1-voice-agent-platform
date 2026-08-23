"""Add voice_agents.public_description for customer-facing demo copy.

Revision ID: 20260820000002
Revises: 20260820000001
Create Date: 2026-08-21

Customer-facing description shown on the dedicated public demo page
``/demo/{demo_slug}``. Distinct from LLM prompt fields
(``persona``/``mission``/``custom_instructions``) — this is what a
potential customer sees before calling. Nullable TEXT so existing rows
remain valid; UI shows it under the ``is_demo`` amber card only when
demo is enabled, with fallback to ``mission`` → ``persona`` on the
public page. No unique constraint.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260820000002"
down_revision: Union[str, None] = "20260820000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_agents",
        sa.Column("public_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voice_agents", "public_description")
