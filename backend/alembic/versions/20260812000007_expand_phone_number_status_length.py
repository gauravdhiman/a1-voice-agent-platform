"""Widen phone-number status values for verification lifecycle states."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260812000007"
down_revision: Union[str, None] = "20260812000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow the 21-character ``verification_required`` status value."""
    op.alter_column(
        "phone_numbers",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore the previous width when no long lifecycle values remain."""
    op.alter_column(
        "phone_numbers",
        "status",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
