"""add voice agents and tools

Revision ID: 20251220000000
Revises: 20251124111200
Create Date: 2025-12-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251220000000"
down_revision: Union[str, None] = "20251124111200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create platform_tools table
    op.create_table(
        "platform_tools",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "config_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create voice_agents table
    op.create_table(
        "voice_agents",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create agent_tools table
    op.create_table(
        "agent_tools",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("tool_id", sa.UUID(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sensitive_config", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["voice_agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["platform_tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool"),
    )

    # Enable Row Level Security (RLS) on voice agent tables
    op.execute("ALTER TABLE voice_agents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_tools ENABLE ROW LEVEL SECURITY")

    # Platform tools don't need RLS as they're shared across all organizations
    # The platform_tools table contains system-wide tools available to all organizations


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("agent_tools")
    op.drop_table("voice_agents")
    op.drop_table("platform_tools")
