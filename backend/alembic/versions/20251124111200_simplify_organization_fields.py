"""Simplify organization fields - add business_details field to store all business information

Revision ID: 20251124111200
Revises: 20250902100001
Create Date: 2025-11-24 11:12:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251124111200"
down_revision: Union[str, None] = "20250902100001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add business_details field to organizations table to store all business information for AI agent."""

    # Add business_details field to organizations table
    op.add_column(
        "organizations", sa.Column("business_details", sa.TEXT(), nullable=True)
    )


def downgrade() -> None:
    """Remove the business_details field from organizations table."""

    op.drop_column("organizations", "business_details")
