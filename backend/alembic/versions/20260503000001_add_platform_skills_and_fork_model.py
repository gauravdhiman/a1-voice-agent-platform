"""add platform_skills table, skill_update_logs, and fork model columns

Revision ID: 20260503000001
Revises: 20260401000001
Create Date: 2026-05-03 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260503000001"
down_revision: Union[str, None] = "20260401000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────
    # 1. Create platform_skills table (immutable platform-level templates)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "platform_skills",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Platform skills are global — no RLS needed (platform admin only)

    # platform_skill_files is also global (child of platform_skills) — no RLS needed

    # ─────────────────────────────────────────────────────────────────────
    # 2. Create platform_skill_files table (default files for platform skills)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "platform_skill_files",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "file_kind",
            sa.String(50),
            nullable=False,
            server_default="reference",
        ),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("skill_id", "file_path", name="uq_platform_skill_file_path"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 3. Create skill_update_logs table (audit trail for refresh operations)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "skill_update_logs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "org_skill_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organization_skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("old_source_version", sa.String(20), nullable=True),
        sa.Column("new_source_version", sa.String(20), nullable=True),
        sa.Column(
            "performed_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 4. Add fork model columns to organization_skills
    # ─────────────────────────────────────────────────────────────────────
    op.add_column(
        "organization_skills",
        sa.Column(
            "source_skill_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_skills.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "organization_skills",
        sa.Column("source_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "organization_skills",
        sa.Column(
            "is_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # Add index for common lookups
    op.create_index(
        "ix_org_skills_source_skill_id",
        "organization_skills",
        ["source_skill_id"],
    )

    # ─────────────────────────────────────────────────────────────────────
    # 5. Remove source_url/source_ref from organization_skills
    #    (imports now create custom skills directly; no source tracking needed)
    # ─────────────────────────────────────────────────────────────────────
    op.drop_column("organization_skills", "source_url")
    op.drop_column("organization_skills", "source_ref")

    # ─────────────────────────────────────────────────────────────────────
    # 6. Update category constraint: remove 'built_in', keep only 'custom'
    #    All org skills are custom (some forked, some created, some imported)
    # ─────────────────────────────────────────────────────────────────────
    # First, update any existing 'built_in' records to 'custom'
    # (data migration script will handle proper forking afterward)
    op.execute("UPDATE organization_skills SET category = 'custom' WHERE category = 'built_in'")

    # Note: We don't add a CHECK constraint here because Alembic/SQLAlchemy
    # doesn't easily modify existing CHECK constraints. The Pydantic model
    # will enforce 'custom' as the only valid value.


def downgrade() -> None:
    # Reverse order of creation

    # 6. Restore source_url/source_ref columns
    op.add_column(
        "organization_skills",
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "organization_skills",
        sa.Column("source_ref", sa.String(100), nullable=True),
    )

    # 5. Remove fork model columns
    op.drop_index("ix_org_skills_source_skill_id", table_name="organization_skills")
    op.drop_column("organization_skills", "is_visible")
    op.drop_column("organization_skills", "source_version")
    op.drop_column("organization_skills", "source_skill_id")

    # 4. Drop skill_update_logs
    op.drop_table("skill_update_logs")

    # 3. Drop platform_skill_files
    op.drop_table("platform_skill_files")

    # 2. Drop platform_skills
    op.drop_table("platform_skills")

    # Note: Downgrade does NOT restore 'built_in' category values.
    # This is a one-way data transformation. If you need to rollback,
    # restore from a database backup taken before the migration.
