"""Add indexes for agent and phone-number lookup hot paths."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260812000009"
down_revision: Union[str, None] = "20260812000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Index organization-scoped agent and assigned-number lookups."""
    op.create_index(
        "ix_voice_agents_organization_active",
        "voice_agents",
        ["organization_id", "is_active"],
    )
    op.create_index(
        "ix_phone_numbers_organization_agent_active",
        "phone_numbers",
        ["organization_id", "assigned_agent_id"],
        postgresql_where=sa.text("status NOT IN ('cancelled', 'disconnected')"),
    )


def downgrade() -> None:
    """Remove the organization-scoped lookup indexes."""
    op.drop_index(
        "ix_phone_numbers_organization_agent_active", table_name="phone_numbers"
    )
    op.drop_index("ix_voice_agents_organization_active", table_name="voice_agents")
