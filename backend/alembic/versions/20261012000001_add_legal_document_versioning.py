"""Add legal document versioning, acceptance tracking, and update outbox.

Creates the versioned Terms & Conditions / Privacy Policy store mirroring the
billing ``plan_versions`` draft/publish contract:

- ``legal_document_versions``: immutable published versions, one draft per
  document key, one current published version per document key.
- ``legal_document_publish_events``: publish audit rows including whether the
  publish requested user notification and how many users were queued.
- ``legal_document_acceptances``: which user accepted which exact document
  version, captured at signup or OAuth handoff.
- ``legal_update_notification_outbox``: durable per-user notification queue
  enqueued at publish time and drained by the notification retry scheduler.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261012000001"
down_revision: Union[str, None] = "20261008000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create legal document versioning, acceptance, and notification tables."""
    op.create_table(
        "legal_document_versions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_key", sa.VARCHAR(length=20), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.VARCHAR(length=20), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("summary_of_changes", sa.Text(), nullable=True),
        sa.Column(
            "is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_key",
            "version_number",
            name="uq_legal_document_versions_key_version",
        ),
        sa.CheckConstraint(
            "document_key IN ('terms', 'privacy')",
            name="ck_legal_document_versions_key",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'deprecated', 'retired')",
            name="ck_legal_document_versions_status",
        ),
    )
    op.create_index(
        "ix_legal_document_versions_key_status",
        "legal_document_versions",
        ["document_key", "status"],
    )
    op.create_index(
        "ux_legal_document_versions_single_draft",
        "legal_document_versions",
        ["document_key"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )
    op.create_index(
        "ux_legal_document_versions_single_current",
        "legal_document_versions",
        ["document_key"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "legal_document_publish_events",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("legal_document_version_id", sa.UUID(), nullable=False),
        sa.Column("document_key", sa.VARCHAR(length=20), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("previous_legal_document_version_id", sa.UUID(), nullable=True),
        sa.Column(
            "notify_users",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("notified_count", sa.Integer(), nullable=True),
        sa.Column("dispatch_id", sa.UUID(), nullable=True),
        sa.Column("published_by", sa.UUID(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["legal_document_version_id"],
            ["legal_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_legal_document_version_id"],
            ["legal_document_versions.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "document_key IN ('terms', 'privacy')",
            name="ck_legal_document_publish_events_key",
        ),
    )
    op.create_index(
        "ix_legal_document_publish_events_version",
        "legal_document_publish_events",
        ["legal_document_version_id"],
    )
    op.create_index(
        "ix_legal_document_publish_events_dispatch",
        "legal_document_publish_events",
        ["dispatch_id"],
    )

    op.create_table(
        "legal_document_acceptances",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("document_key", sa.VARCHAR(length=20), nullable=False),
        sa.Column("legal_document_version_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.VARCHAR(length=20), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.VARCHAR(length=45), nullable=True),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["legal_document_version_id"],
            ["legal_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "document_key",
            "version_number",
            name="uq_legal_document_acceptances_user_key_version",
        ),
        sa.CheckConstraint(
            "document_key IN ('terms', 'privacy')",
            name="ck_legal_document_acceptances_key",
        ),
        sa.CheckConstraint(
            "source IN ('signup', 'oauth', 'reaccept')",
            name="ck_legal_document_acceptances_source",
        ),
    )
    op.create_index(
        "ix_legal_document_acceptances_user",
        "legal_document_acceptances",
        ["user_id"],
    )
    op.create_index(
        "ix_legal_document_acceptances_version",
        "legal_document_acceptances",
        ["legal_document_version_id"],
    )

    op.create_table(
        "legal_update_notification_outbox",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dispatch_id", sa.UUID(), nullable=False),
        sa.Column("legal_document_version_id", sa.UUID(), nullable=False),
        sa.Column("document_key", sa.VARCHAR(length=20), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("recipient_email", sa.Text(), nullable=False),
        sa.Column("recipient_name", sa.Text(), nullable=True),
        sa.Column("summary_of_changes", sa.Text(), nullable=True),
        sa.Column(
            "attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["legal_document_version_id"],
            ["legal_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "dispatch_id",
            "user_id",
            name="uq_legal_update_notification_outbox_dispatch_user",
        ),
        sa.CheckConstraint(
            "document_key IN ('terms', 'privacy')",
            name="ck_legal_update_notification_outbox_key",
        ),
    )
    op.create_index(
        "ix_legal_update_notification_outbox_pending",
        "legal_update_notification_outbox",
        ["processed_at", "created_at"],
    )
    op.create_index(
        "ix_legal_update_notification_outbox_dispatch",
        "legal_update_notification_outbox",
        ["dispatch_id"],
    )

    # Application access uses the service-role client; direct table access is
    # denied for anon/authenticated roles, matching credit_notification_outbox.
    for table_name in (
        "legal_document_versions",
        "legal_document_publish_events",
        "legal_document_acceptances",
        "legal_update_notification_outbox",
    ):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Drop the legal document tables and their indexes."""
    for table_name in (
        "legal_update_notification_outbox",
        "legal_document_acceptances",
        "legal_document_publish_events",
        "legal_document_versions",
    ):
        op.drop_table(table_name)
