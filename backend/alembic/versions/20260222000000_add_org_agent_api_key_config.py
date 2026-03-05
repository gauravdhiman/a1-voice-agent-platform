"""add_org_agent_api_key_config

Revision ID: 20260222000000
Revises: 20260217004742
Create Date: 2026-02-22 00:00:00.000000

This migration adds support for configurable API keys at organization and agent levels:
- organizations.google_api_key: Organization's own Google API key
- voice_agents.use_platform_credits: Agent override to use platform credits instead of org key

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260222000000"
down_revision: Union[str, None] = "20260217004742"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add google_api_key to organizations table
    op.add_column(
        "organizations",
        sa.Column(
            "google_api_key",
            sa.Text(),
            nullable=True,
            comment="Organization Google API key for voice agents"
        )
    )
    
    # Add use_platform_credits to voice_agents table
    op.add_column(
        "voice_agents",
        sa.Column(
            "use_platform_credits",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Use platform credits instead of organization API key"
        )
    )


def downgrade() -> None:
    op.drop_column("voice_agents", "use_platform_credits")
    op.drop_column("organizations", "google_api_key")
