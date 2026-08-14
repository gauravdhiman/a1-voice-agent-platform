"""Add the per-agent call recording setting."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260814000001"
down_revision: Union[str, None] = "20260812000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add an opt-in recording flag with a safe disabled default."""
    op.add_column(
        "voice_agents",
        sa.Column(
            "call_recording_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the per-agent recording flag."""
    op.drop_column("voice_agents", "call_recording_enabled")
