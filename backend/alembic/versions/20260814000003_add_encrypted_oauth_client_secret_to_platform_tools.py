"""Add encrypted OAuth client-secret storage to platform tools.

Revision ID: 20260814000003
Revises: 20260814000001, 20260814000002
Create Date: 2026-08-14

OAuth endpoint metadata remains in ``platform_tools.auth_config`` as public
configuration. Confidential client secrets belong in a separate Fernet-
encrypted column so catalog responses, OAuth state, and worker metadata cannot
accidentally serialize them.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260814000003"
down_revision: Union[str, Sequence[str], None] = (
    "20260814000001",
    "20260814000002",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the nullable encrypted OAuth client-secret column."""
    op.add_column(
        "platform_tools",
        sa.Column("oauth_client_secret_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove encrypted OAuth client-secret storage."""
    op.drop_column("platform_tools", "oauth_client_secret_encrypted")
