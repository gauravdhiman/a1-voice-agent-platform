"""Merge the two existing migration heads.

Revision ID: 20260827000001
Revises: 20260820000002, 20260821000001
Create Date: 2026-08-27

The demo/public-description migrations and the call-log-delete permission
migration were both based on ``20260819000001``. This no-op merge gives fresh
local databases and deployed environments one canonical Alembic head; it does
not change the schema or data.
"""

from typing import Sequence, Union


revision: str = "20260827000001"
down_revision: Union[str, Sequence[str], None] = (
    "20260820000002",
    "20260821000001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the existing migration branches without changing the schema."""


def downgrade() -> None:
    """Re-expose the two historical heads when rolling back the merge."""
