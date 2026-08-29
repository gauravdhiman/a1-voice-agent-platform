"""Merge the demo-agent and call-log permission migration branches.

The two feature migrations both followed ``20260819000001``. Keeping a
single Alembic head is required because every supported stack startup applies
``alembic upgrade head``.
"""

from typing import Sequence, Union


revision: str = "20260822000001"
down_revision: Union[str, Sequence[str], None] = (
    "20260820000002",
    "20260821000001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Mark both migration branches as joined at one repository head."""


def downgrade() -> None:
    """Leave the merged branches available for an explicit downgrade."""
