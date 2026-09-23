"""Add non-secret reference notes for organization provider credentials."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260923000001"
down_revision: Union[str, None] = "20260922000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store optional per-provider notes separately from encrypted secrets."""
    op.add_column(
        "organizations",
        sa.Column(
            "provider_credentials_descriptions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "Non-secret per-provider reference notes for the API credentials "
                "UI; values are never used by the voice runtime."
            ),
        ),
    )


def downgrade() -> None:
    """Remove provider credential reference notes."""
    op.drop_column("organizations", "provider_credentials_descriptions")
