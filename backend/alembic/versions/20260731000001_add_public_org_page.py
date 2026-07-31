"""add_public_org_page

Adds org-scoped public showcase pages at ``/o/{slug}`` where visitors can talk
to agents explicitly published by org admins.

- ``organizations.public_page_enabled`` — master toggle for the public page
- ``organizations.public_page_passphrase_enabled`` — optional gate
- ``organizations.public_page_passphrase_hash`` — PBKDF2 hash (never returned)
- ``voice_agents.is_published_on_public_page`` — explicit publish flag
  (distinct from ``is_active`` and embed config)

Revision ID: 20260731000001
Revises: 20260729000002
Create Date: 2026-07-31 00:00:01.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260731000001"
down_revision: Union[str, None] = "20260729000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "public_page_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "public_page_passphrase_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("public_page_passphrase_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "voice_agents",
        sa.Column(
            "is_published_on_public_page",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("voice_agents", "is_published_on_public_page")
    op.drop_column("organizations", "public_page_passphrase_hash")
    op.drop_column("organizations", "public_page_passphrase_enabled")
    op.drop_column("organizations", "public_page_enabled")
