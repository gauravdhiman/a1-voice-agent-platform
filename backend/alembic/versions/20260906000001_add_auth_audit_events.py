"""Tamper-evident authentication audit trail (Epic E hardening).

Security-relevant auth events are appended to ``auth_audit_events`` by the
backend only. Rows are never updated or deleted by application code; reads
are platform-admin only. Emails are stored for investigation; full request
bodies, tokens, and secrets are never recorded.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260906000001"
down_revision: Union[str, None] = "20260904000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the append-only auth audit table and service-role boundary."""
    op.create_table(
        "auth_audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("event", sa.String(length=60), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "event IN ("
            "'signup', 'signup_denied', 'signin', 'signin_denied', "
            "'signout', 'invitation_processed', 'password_reset_requested', "
            "'oauth_signin', 'oauth_denied'"
            ")",
            name="ck_auth_audit_events_event",
        ),
    )
    op.create_index(
        "ix_auth_audit_events_email_created",
        "auth_audit_events",
        ["email", "created_at"],
    )
    op.create_index(
        "ix_auth_audit_events_event_created",
        "auth_audit_events",
        ["event", "created_at"],
    )
    op.execute("ALTER TABLE auth_audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE auth_audit_events FROM PUBLIC")
    op.execute("GRANT ALL ON TABLE auth_audit_events TO service_role")


def downgrade() -> None:
    """Remove the auth audit table and indexes."""
    op.drop_index("ix_auth_audit_events_event_created", table_name="auth_audit_events")
    op.drop_index("ix_auth_audit_events_email_created", table_name="auth_audit_events")
    op.drop_table("auth_audit_events")
