"""Add the audit ledger used by the on-demand master-data seeder."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260813000001"
down_revision: Union[str, None] = "20260812000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the append-only-ish seed-run ledger for master-data operations."""
    op.create_table(
        "master_data_seed_runs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("domain", sa.VARCHAR(length=100), nullable=False),
        sa.Column("definition_version", sa.VARCHAR(length=100), nullable=False),
        sa.Column("definition_hash", sa.VARCHAR(length=128), nullable=False),
        sa.Column(
            "operation",
            sa.VARCHAR(length=20),
            server_default=sa.text("'seed'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.VARCHAR(length=20),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column("triggered_by", sa.UUID(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.TEXT(), nullable=True),
        sa.Column(
            "started_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "operation IN ('seed', 'reset')",
            name="ck_master_data_seed_runs_operation",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_master_data_seed_runs_status",
        ),
    )
    op.create_index(
        "ix_master_data_seed_runs_domain_completed",
        "master_data_seed_runs",
        ["domain", "status", "completed_at"],
    )
    op.create_index(
        "ux_master_data_seed_runs_running_domain",
        "master_data_seed_runs",
        ["domain"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )

    # The backend uses the service-role client. Keeping RLS enabled prevents a
    # browser session from reading or mutating the audit ledger directly.
    op.execute("ALTER TABLE master_data_seed_runs ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Remove the master-data seed-run ledger."""
    op.drop_index(
        "ix_master_data_seed_runs_domain_completed",
        table_name="master_data_seed_runs",
    )
    op.drop_index(
        "ux_master_data_seed_runs_running_domain",
        table_name="master_data_seed_runs",
    )
    op.drop_table("master_data_seed_runs")
