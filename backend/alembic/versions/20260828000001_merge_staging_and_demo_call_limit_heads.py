"""Join the staging merge revision with the demo call-limit migration.

The staging validation work applied ``20260822000001`` to the shared staging
database. Remote ``main`` subsequently added ``20260827000001`` from the two
original feature heads. This forward-only merge keeps both histories valid and
gives every environment one connected Alembic head.
"""

from typing import Sequence, Union


revision: str = "20260828000001"
down_revision: Union[str, Sequence[str], None] = (
    "20260822000001",
    "20260827000001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the already-defined migration branches."""


def downgrade() -> None:
    """Leave both parent branches available for an explicit downgrade."""
