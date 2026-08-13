"""Store customer webhook tokens encrypted for pending setup details."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260812000008"
down_revision: Union[str, None] = "20260812000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add encrypted storage for customer-owned pending webhook tokens."""
    op.add_column(
        "phone_numbers",
        sa.Column("connection_token_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove encrypted pending webhook-token storage."""
    op.drop_column("phone_numbers", "connection_token_encrypted")
