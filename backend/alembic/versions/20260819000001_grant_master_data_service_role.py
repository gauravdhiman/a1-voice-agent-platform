"""Grant the backend service role access to the application schema.

Fresh local Supabase projects create application tables through Alembic using
the database owner, while the application accesses them through Supabase's
``service_role``.  The hosted database already has these grants, but a new
worktree database does not inherit them automatically.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260819000001"
down_revision: Union[str, None] = "20260818000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow the backend service role to use current and future app tables.

    Existing tables and sequences are granted dynamically so this migration
    remains correct as the application schema evolves.  Default privileges
    cover tables and identity sequences created by later Alembic migrations
    under the same database owner.
    """
    op.execute("GRANT USAGE ON SCHEMA public TO service_role")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO service_role"
    )
    op.execute(
        """
        DO $$
        DECLARE
            table_name text;
        BEGIN
            FOR table_name IN
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I '
                    'TO service_role',
                    table_name
                );
            END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            current_sequence_name text;
        BEGIN
            FOR current_sequence_name IN
                SELECT sequences.sequence_name
                FROM information_schema.sequences AS sequences
                WHERE sequences.sequence_schema = 'public'
            LOOP
                EXECUTE format(
                    'GRANT USAGE, SELECT ON SEQUENCE public.%I '
                    'TO service_role',
                    current_sequence_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Stop granting future access without removing existing role access.

    Current table and sequence grants are intentionally retained during a
    downgrade because they may have been established by the platform before
    this migration.  Removing them could break a running backend.
    """
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM service_role"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE USAGE, SELECT ON SEQUENCES FROM service_role"
    )
