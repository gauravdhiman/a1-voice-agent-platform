"""add_auth_columns_to_platform_tools

Revision ID: 20260111000001
Revises: 20251230000002
Create Date: 2026-01-11 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260111000001"
down_revision: Union[str, None] = "20251230000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_tools",
        sa.Column(
            "auth_type",
            sa.String(length=50),
            nullable=True,
            comment="Authentication type (e.g., 'oauth2', 'api_key')",
        ),
    )
    op.add_column(
        "platform_tools",
        sa.Column(
            "requires_auth",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Whether the tool requires authentication",
        ),
    )
    op.add_column(
        "platform_tools",
        sa.Column(
            "auth_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Authentication configuration (e.g., OAuth URLs, scopes, provider)",
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_tools", "auth_config")
    op.drop_column("platform_tools", "auth_type")
    op.drop_column("platform_tools", "requires_auth")
