"""Add voice_agents.is_demo + demo_slug for credit-exempt demo agents.

Revision ID: 20260820000001
Revises: 20260819000001
Create Date: 2026-08-20

Demo agents bypass both the pre-call ``assert_voice_session_allowed``
credit/concurrency gate and the post-call ``consume_voice_call_credits``
debit in ``voice-ws``. The flag is platform_admin-only (API enforces
``has_role("platform_admin")`` on writes) and defaults to false so existing
rows remain non-demo. A dedicated public page ``/demo/{slug}`` is available
only for demo agents; ``demo_slug`` is unique when set and only valid when
``is_demo`` is true. Partial indexes keep the demo-agent lookup and slug
uniqueness cheap and document the intent.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260820000001"
down_revision: Union[str, None] = "20260819000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_agents",
        sa.Column(
            "is_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "voice_agents",
        sa.Column(
            "demo_slug",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_voice_agents_is_demo",
        "voice_agents",
        ["is_demo"],
        postgresql_where=sa.text("is_demo = true"),
    )
    # Unique slug only for demo agents; NULLs are not considered equal.
    op.create_index(
        "uq_voice_agents_demo_slug",
        "voice_agents",
        ["demo_slug"],
        unique=True,
        postgresql_where=sa.text("demo_slug IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_voice_agents_demo_slug", table_name="voice_agents")
    op.drop_index("ix_voice_agents_is_demo", table_name="voice_agents")
    op.drop_column("voice_agents", "demo_slug")
    op.drop_column("voice_agents", "is_demo")
