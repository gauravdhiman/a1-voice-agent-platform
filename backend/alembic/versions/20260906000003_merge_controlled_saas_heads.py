"""Merge the main and controlled-SaaS migration heads.

The main line added organization-level tool visibility while the controlled-
SaaS line continued through auth auditing and atomic invitation claiming.
Both histories are valid independently; this forward-only merge keeps the
integration branch at one Alembic head for ``alembic upgrade head``.
"""

from typing import Sequence, Union


revision: str = "20260906000003"
down_revision: Union[str, Sequence[str], None] = (
    "20260905000001",
    "20260906000002",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the already-defined main and controlled-SaaS branches."""


def downgrade() -> None:
    """Leave both parent branches available for an explicit downgrade."""
