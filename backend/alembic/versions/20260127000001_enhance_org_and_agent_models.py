"""enhance_org_and_agent_models

Revision ID: 20260127000001
Revises: 20260118000001
Create Date: 2026-01-27 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260127000001"
down_revision: Union[str, None] = "20260118000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to organizations
    op.add_column("organizations", sa.Column("industry", sa.String(length=100), nullable=True))
    op.add_column("organizations", sa.Column("location", sa.String(length=255), nullable=True))

    # Add columns to voice_agents
    op.add_column("voice_agents", sa.Column("persona", sa.Text(), nullable=True))
    op.add_column("voice_agents", sa.Column("tone", sa.String(length=100), nullable=True))
    op.add_column("voice_agents", sa.Column("mission", sa.Text(), nullable=True))
    op.add_column("voice_agents", sa.Column("custom_instructions", sa.Text(), nullable=True))
    
    # Remove deprecated system_prompt column (now auto-generated via PromptBuilder)
    op.drop_column("voice_agents", "system_prompt")


def downgrade() -> None:
    # Restore system_prompt column
    op.add_column("voice_agents", sa.Column("system_prompt", sa.Text(), nullable=True))
    
    # Remove columns from voice_agents
    op.drop_column("voice_agents", "custom_instructions")
    op.drop_column("voice_agents", "mission")
    op.drop_column("voice_agents", "tone")
    op.drop_column("voice_agents", "persona")

    # Remove columns from organizations
    op.drop_column("organizations", "location")
    op.drop_column("organizations", "industry")
