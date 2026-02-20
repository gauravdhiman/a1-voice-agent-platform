"""add_agent_embed_configs_table

Revision ID: 20260217004742
Revises: 20260127000001
Create Date: 2026-02-17 00:47:42.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260217004742"
down_revision: Union[str, None] = "20260127000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_embed_configs table
    op.create_table(
        "agent_embed_configs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("button_text", sa.String(length=100), nullable=False, server_default="Call Us"),
        sa.Column("button_color", sa.String(length=7), nullable=False, server_default="#3b82f6"),
        sa.Column("button_text_color", sa.String(length=7), nullable=False, server_default="#ffffff"),
        sa.Column("button_border_radius", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("button_size", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("button_position", sa.String(length=20), nullable=False, server_default="bottom-right"),
        sa.Column("button_style", sa.String(length=20), nullable=False, server_default="filled"),
        sa.Column("allowed_domains", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("custom_css", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("daily_call_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["agent_id"], ["voice_agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )
    
    # Create index on agent_id for faster lookups
    op.create_index(
        "idx_agent_embed_configs_agent_id",
        "agent_embed_configs",
        ["agent_id"],
    )
    
    # Create embed_call_logs table for tracking usage
    op.create_table(
        "embed_call_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("embed_config_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("call_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="started"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["embed_config_id"], ["agent_embed_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create index on embed_config_id for faster lookups
    op.create_index(
        "idx_embed_call_logs_config_id",
        "embed_call_logs",
        ["embed_config_id"],
    )
    
    # Create index on started_at for time-based queries
    op.create_index(
        "idx_embed_call_logs_started_at",
        "embed_call_logs",
        ["started_at"],
    )

    # Enable Row Level Security (RLS) on embed tables
    op.execute("ALTER TABLE agent_embed_configs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE embed_call_logs ENABLE ROW LEVEL SECURITY")

    # RLS Policies for agent_embed_configs
    # SELECT: Org admins and platform admins can view embed configs for their organization's agents
    op.execute(
        """
        CREATE POLICY "Org admins can view embed configs for their agents"
        ON agent_embed_configs FOR SELECT
        TO authenticated
        USING (
            agent_id IN (
                SELECT id FROM voice_agents
                WHERE organization_id IN (
                    SELECT organization_id
                    FROM user_roles
                    JOIN roles ON user_roles.role_id = roles.id
                    WHERE user_roles.user_id = auth.uid()
                    AND roles.name IN ('org_admin', 'platform_admin')
                )
            )
        )
    """
    )

    # INSERT: Org admins and platform admins can create embed configs
    op.execute(
        """
        CREATE POLICY "Org admins can create embed configs for their agents"
        ON agent_embed_configs FOR INSERT
        TO authenticated
        WITH CHECK (
            agent_id IN (
                SELECT id FROM voice_agents
                WHERE organization_id IN (
                    SELECT organization_id
                    FROM user_roles
                    JOIN roles ON user_roles.role_id = roles.id
                    WHERE user_roles.user_id = auth.uid()
                    AND roles.name IN ('org_admin', 'platform_admin')
                )
            )
        )
    """
    )

    # UPDATE: Org admins and platform admins can update embed configs
    op.execute(
        """
        CREATE POLICY "Org admins can update embed configs for their agents"
        ON agent_embed_configs FOR UPDATE
        TO authenticated
        USING (
            agent_id IN (
                SELECT id FROM voice_agents
                WHERE organization_id IN (
                    SELECT organization_id
                    FROM user_roles
                    JOIN roles ON user_roles.role_id = roles.id
                    WHERE user_roles.user_id = auth.uid()
                    AND roles.name IN ('org_admin', 'platform_admin')
                )
            )
        )
        WITH CHECK (
            agent_id IN (
                SELECT id FROM voice_agents
                WHERE organization_id IN (
                    SELECT organization_id
                    FROM user_roles
                    JOIN roles ON user_roles.role_id = roles.id
                    WHERE user_roles.user_id = auth.uid()
                    AND roles.name IN ('org_admin', 'platform_admin')
                )
            )
        )
    """
    )

    # DELETE: Org admins and platform admins can delete embed configs
    op.execute(
        """
        CREATE POLICY "Org admins can delete embed configs for their agents"
        ON agent_embed_configs FOR DELETE
        TO authenticated
        USING (
            agent_id IN (
                SELECT id FROM voice_agents
                WHERE organization_id IN (
                    SELECT organization_id
                    FROM user_roles
                    JOIN roles ON user_roles.role_id = roles.id
                    WHERE user_roles.user_id = auth.uid()
                    AND roles.name IN ('org_admin', 'platform_admin')
                )
            )
        )
    """
    )

    # RLS Policies for embed_call_logs
    # SELECT: Org admins and platform admins can view call logs for their organization
    op.execute(
        """
        CREATE POLICY "Org admins can view embed call logs for their org"
        ON embed_call_logs FOR SELECT
        TO authenticated
        USING (
            embed_config_id IN (
                SELECT id FROM agent_embed_configs
                WHERE agent_id IN (
                    SELECT id FROM voice_agents
                    WHERE organization_id IN (
                        SELECT organization_id
                        FROM user_roles
                        JOIN roles ON user_roles.role_id = roles.id
                        WHERE user_roles.user_id = auth.uid()
                        AND roles.name IN ('org_admin', 'platform_admin')
                    )
                )
            )
        )
    """
    )

    # Note: INSERT for embed_call_logs is handled by backend using service role key
    # which bypasses RLS. This is intentional for the public embed API.


def downgrade() -> None:
    # Drop RLS policies
    op.execute(
        'DROP POLICY IF EXISTS "Org admins can view embed call logs for their org" ON embed_call_logs'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Org admins can delete embed configs for their agents" ON agent_embed_configs'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Org admins can update embed configs for their agents" ON agent_embed_configs'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Org admins can create embed configs for their agents" ON agent_embed_configs'
    )
    op.execute(
        'DROP POLICY IF EXISTS "Org admins can view embed configs for their agents" ON agent_embed_configs'
    )

    # Disable RLS
    op.execute("ALTER TABLE embed_call_logs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_embed_configs DISABLE ROW LEVEL SECURITY")

    # Drop embed_call_logs table
    op.drop_index("idx_embed_call_logs_started_at", table_name="embed_call_logs")
    op.drop_index("idx_embed_call_logs_config_id", table_name="embed_call_logs")
    op.drop_table("embed_call_logs")
    
    # Drop agent_embed_configs table
    op.drop_index("idx_agent_embed_configs_agent_id", table_name="agent_embed_configs")
    op.drop_table("agent_embed_configs")
