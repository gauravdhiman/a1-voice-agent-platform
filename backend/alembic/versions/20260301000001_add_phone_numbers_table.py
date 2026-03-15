"""add phone numbers table

Revision ID: 20260301000001
Revises: 20260222000000
Create Date: 2026-03-01 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260301000001"
down_revision: Union[str, None] = "20260222000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create phone_numbers table for managing purchased phone numbers."""
    op.create_table(
        "phone_numbers",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("organization_id", sa.UUID(), nullable=False, index=True),
        sa.Column("phone_number", sa.String(length=20), nullable=False, index=True),
        sa.Column("provider", sa.String(length=20), nullable=False, default="twilio"),
        sa.Column("provider_sid", sa.String(length=255), nullable=True),
        sa.Column(
            "phone_number_type", sa.String(length=20), nullable=False, default="local"
        ),
        sa.Column("country_code", sa.String(length=2), nullable=False, default="US"),
        sa.Column("area_code", sa.String(length=10), nullable=True),
        sa.Column("monthly_cost_credits", sa.Integer(), nullable=False, default=200),
        sa.Column("status", sa.String(length=20), nullable=False, default="purchased"),
        sa.Column("assigned_agent_id", sa.UUID(), nullable=True, index=True),
        sa.Column(
            "is_incoming_enabled", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "is_outgoing_enabled", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
        sa.ForeignKeyConstraint(
            ["assigned_agent_id"], ["voice_agents.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_sid", name="uq_phone_number_provider_sid"),
    )

    op.create_index(
        "ix_phone_numbers_organization_status",
        "phone_numbers",
        ["organization_id", "status"],
    )

    op.execute("ALTER TABLE phone_numbers ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY "phone_numbers_organization_access"
        ON phone_numbers FOR ALL
        USING (
            organization_id IN (
                SELECT organization_id::uuid
                FROM user_roles
                WHERE user_id::uuid = auth.uid()
            )
        )
    """)


def downgrade() -> None:
    """Drop phone_numbers table."""
    op.execute(
        'DROP POLICY IF EXISTS "phone_numbers_organization_access" ON phone_numbers'
    )
    op.drop_index("ix_phone_numbers_organization_status", table_name="phone_numbers")
    op.drop_table("phone_numbers")
