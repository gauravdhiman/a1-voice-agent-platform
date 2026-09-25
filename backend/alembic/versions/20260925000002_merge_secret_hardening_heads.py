"""Merge the secret-hardening and notification migration heads.

The secret-hardening branch and the later notification-channel branch are both
valid forward histories. This no-op merge keeps the integration branch at one
Alembic head for ``alembic upgrade head``.
"""

from typing import Sequence, Union


revision: str = "20260925000002"
down_revision: Union[str, Sequence[str], None] = (
    "20260922000002",
    "20260925000001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the already-defined secret-hardening and notification branches."""


def downgrade() -> None:
    """Leave both parent branches available for an explicit downgrade."""
