"""add skills tables (organization_skills, organization_skill_files, agent_skills)

Revision ID: 20260401000001
Revises: 20260331000001
Create Date: 2026-04-01 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260401000001"
down_revision: Union[str, None] = "20260331000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organization skill library
    op.create_table(
        "organization_skills",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),  # SHA-256 hex digest for change detection
        # Future-proof for Phase 2b (import/versioning)
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "slug", name="uq_org_skill_slug"),
    )
    op.execute("ALTER TABLE organization_skills ENABLE ROW LEVEL SECURITY")

    # Skill reference files (Phase 2b data, table created now)
    op.create_table(
        "organization_skill_files",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("skill_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organization_skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_kind", sa.String(50), nullable=False, server_default="reference"),
        sa.Column("content_hash", sa.String(64), nullable=True),  # SHA-256 hex digest for change detection
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("skill_id", "file_path", name="uq_skill_file_path"),
    )

    # Agent-to-skill assignment junction
    op.create_table(
        "agent_skills",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("voice_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organization_skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("agent_id", "skill_id", name="uq_agent_skill"),
    )


def downgrade() -> None:
    op.drop_table("agent_skills")
    op.drop_table("organization_skill_files")
    op.drop_table("organization_skills")
