"""Add durable, fenced maintenance run ownership.

Interrupted or failed runs remain held for reconciliation. A scheduler retry
must not repeat an external mutation whose provider outcome is unknown.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261102000001"
down_revision = "20261031000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create service-role-only coordination records and atomic RPCs."""
    op.create_table(
        "maintenance_runs",
        sa.Column("job", sa.Text(), primary_key=True),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("last_succeeded_at", sa.DateTime(timezone=True)),
        sa.Column("last_failed_at", sa.DateTime(timezone=True)),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('idle', 'running', 'failed')",
            name="maintenance_runs_state_check",
        ),
    )
    op.execute("ALTER TABLE public.maintenance_runs ENABLE ROW LEVEL SECURITY")
    op.create_index(
        "ix_maintenance_runs_active",
        "maintenance_runs",
        ["state", "started_at"],
        postgresql_where=sa.text("state <> 'idle'"),
    )
    op.execute("REVOKE ALL ON public.maintenance_runs FROM PUBLIC, anon, authenticated")
    op.execute("GRANT ALL ON public.maintenance_runs TO service_role")
    op.execute(
        """
        CREATE FUNCTION public.claim_maintenance_run(
            p_job text, p_claim text, p_interval_seconds double precision DEFAULT 0
        ) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        DECLARE current_state text;
        BEGIN
            IF p_job IS NULL OR p_job = '' OR p_claim IS NULL OR p_claim = ''
               OR p_interval_seconds IS NULL OR p_interval_seconds < 0 THEN
                RAISE EXCEPTION 'job, claim, and a nonnegative interval are required';
            END IF;
            INSERT INTO public.maintenance_runs(job, claim, state)
            VALUES (p_job, p_claim, 'running')
            ON CONFLICT (job) DO UPDATE
                SET claim = EXCLUDED.claim, state = 'running',
                    started_at = now(), finished_at = NULL
              WHERE maintenance_runs.state = 'idle'
                AND (maintenance_runs.last_succeeded_at IS NULL
                     OR maintenance_runs.last_reconciled_at
                        > maintenance_runs.last_succeeded_at
                     OR maintenance_runs.last_succeeded_at +
                        make_interval(secs => p_interval_seconds) <= now());
            IF FOUND THEN RETURN 'claimed'; END IF;
            SELECT state INTO current_state FROM public.maintenance_runs
             WHERE job = p_job;
            IF current_state = 'idle' THEN RETURN 'not_due'; END IF;
            IF current_state = 'failed' THEN RETURN 'blocked'; END IF;
            IF current_state = 'running' THEN RETURN 'running'; END IF;
            RAISE EXCEPTION 'maintenance state is unavailable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.complete_maintenance_run(
            p_job text, p_claim text, p_succeeded boolean
        ) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        BEGIN
            IF p_succeeded THEN
                UPDATE public.maintenance_runs
                   SET state = 'idle', finished_at = now(), last_succeeded_at = now()
                 WHERE job = p_job AND claim = p_claim AND state = 'running';
            ELSE
                UPDATE public.maintenance_runs
                   SET state = 'failed', finished_at = now(), last_failed_at = now()
                 WHERE job = p_job AND claim = p_claim AND state = 'running';
            END IF;
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.retry_maintenance_run(p_job text, p_claim text)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        BEGIN
            UPDATE public.maintenance_runs
               SET state = 'idle', finished_at = now(), last_failed_at = now()
             WHERE job = p_job AND claim = p_claim AND state = 'running';
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.release_maintenance_guard(p_job text, p_claim text)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        BEGIN
            UPDATE public.maintenance_runs
               SET state = 'idle', finished_at = now()
             WHERE job = p_job AND claim = p_claim AND state = 'running';
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.reconcile_maintenance_run(p_job text, p_claim text)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $$
        BEGIN
            UPDATE public.maintenance_runs
               SET state = 'idle', finished_at = now(), last_reconciled_at = now()
             WHERE job = p_job AND claim = p_claim AND state IN ('running', 'failed');
            RETURN FOUND;
        END;
        $$
        """
    )
    for function in (
        "claim_maintenance_run(text,text,double precision)",
        "complete_maintenance_run(text,text,boolean)",
        "retry_maintenance_run(text,text)",
        "release_maintenance_guard(text,text)",
        "reconcile_maintenance_run(text,text)",
    ):
        op.execute(
            f"REVOKE ALL ON FUNCTION public.{function} FROM PUBLIC, anon, authenticated"
        )
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO service_role")


def downgrade() -> None:
    """Remove coordination objects after operators have stopped all workers."""
    op.execute("DROP FUNCTION public.reconcile_maintenance_run(text,text)")
    op.execute("DROP FUNCTION public.release_maintenance_guard(text,text)")
    op.execute("DROP FUNCTION public.retry_maintenance_run(text,text)")
    op.execute("DROP FUNCTION public.complete_maintenance_run(text,text,boolean)")
    op.execute("DROP FUNCTION public.claim_maintenance_run(text,text,double precision)")
    op.drop_table("maintenance_runs")
