"""add token_refresh_leases table + claim/release functions (distributed lock)

Revision ID: 20260623000001
Revises: 20260503000001
Create Date: 2026-06-23 00:00:01.000000

Prevents the TokenRefreshService race condition when multiple backend instances
run: only one instance can hold a per-agent_tool refresh lease at a time. The
lease auto-expires (TTL) so a crashed holder does not block refresh forever.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260623000001"
down_revision: Union[str, None] = "20260503000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────
    # 1. token_refresh_leases — one row per agent_tool while a refresh is in flight
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "token_refresh_leases",
        sa.Column(
            "agent_tool_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_tools.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "locked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("claim", sa.Text(), nullable=False),
    )
    # Internal table — only the backend service (service role, bypasses RLS) uses it.
    op.execute("ALTER TABLE token_refresh_leases ENABLE ROW LEVEL SECURITY")

    # ─────────────────────────────────────────────────────────────────────
    # 2. claim_token_refresh — atomic lease acquisition with TTL.
    #    INSERT ... ON CONFLICT DO UPDATE ... WHERE locked_at < now()-lease:
    #      * no existing row        -> INSERT succeeds  -> claim granted
    #      * existing, lease expired -> UPDATE succeeds -> claim granted (re-acquire)
    #      * existing, lease active -> WHERE fails (0 rows) -> claim denied
    #    Returns jsonb {"claimed": bool, "claim": text}.
    # ─────────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION claim_token_refresh(
            p_tool_id uuid,
            p_claim text,
            p_lease_seconds int DEFAULT 120
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            won text;
        BEGIN
            INSERT INTO token_refresh_leases (agent_tool_id, locked_at, claim)
            VALUES (p_tool_id, now(), p_claim)
            ON CONFLICT (agent_tool_id) DO UPDATE
                SET locked_at = now(),
                    claim = p_claim
                WHERE token_refresh_leases.locked_at < now() - make_interval(secs => p_lease_seconds)
            RETURNING claim INTO won;
            RETURN jsonb_build_object('claimed', won IS NOT NULL, 'claim', COALESCE(won, ''));
        END;
        $$;
        """
    )

    # ─────────────────────────────────────────────────────────────────────
    # 3. release_token_refresh — release only if the row still belongs to this caller.
    #    Returns jsonb {"released": bool}.
    # ─────────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION release_token_refresh(
            p_tool_id uuid,
            p_claim text
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        BEGIN
            DELETE FROM token_refresh_leases
             WHERE agent_tool_id = p_tool_id
               AND claim = p_claim;
            RETURN jsonb_build_object('released', FOUND);
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS release_token_refresh(uuid, text)")
    op.execute("DROP FUNCTION IF EXISTS claim_token_refresh(uuid, text, int)")
    op.drop_table("token_refresh_leases")
