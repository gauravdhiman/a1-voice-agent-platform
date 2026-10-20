"""Index bounded recording-retention cleanup passes."""

from alembic import op

revision = "20261019000002"
down_revision = "20261019000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Support oldest-expired-first scans without scanning completed history."""
    op.execute("""CREATE INDEX ix_call_artifacts_pending_retention
        ON public.call_artifacts (retention_expires_at)
        WHERE artifact_type = 'recording' AND status = 'completed'
          AND retention_expires_at IS NOT NULL""")


def downgrade() -> None:
    """Remove only the cleanup index; preserve artifact data."""
    op.drop_index("ix_call_artifacts_pending_retention", table_name="call_artifacts")
