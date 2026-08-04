"""Add organizations.timezone for org-scoped voice prompt anchoring.

Revision ID: 20260804000001
Revises: 20260803000001
Create Date: 2026-08-04

Stores an optional IANA timezone (e.g. America/Los_Angeles) on each
organization so voice-ws can inject the correct "current date/time" into
agent prompts for scheduling and business-hours reasoning.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260804000001"
down_revision: Union[str, None] = "20260803000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("timezone", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "timezone")
