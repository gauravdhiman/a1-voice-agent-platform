"""Guard plan-change operations and credit-period webhook handoff.

Revision ID: 20261001000006
Revises: 20261001000005
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261001000006"
down_revision: Union[str, Sequence[str], None] = "20261001000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add atomic claim and transition-ID-guarded release operations."""
    op.execute(
        "ALTER TABLE organization_subscriptions "
        "ADD COLUMN pending_plan_transition JSONB NULL"
    )
    op.execute(
        """
        CREATE FUNCTION claim_subscription_plan_transition(
            p_subscription_id uuid,
            p_transition jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            affected_rows integer;
        BEGIN
            IF p_transition IS NULL
               OR jsonb_typeof(p_transition) <> 'object'
               OR coalesce(p_transition->>'transition_id', '') = '' THEN
                RAISE EXCEPTION 'plan transition must include a transition_id';
            END IF;

            UPDATE organization_subscriptions
               SET pending_plan_transition = p_transition,
                   updated_at = now()
             WHERE id = p_subscription_id
               AND pending_plan_transition IS NULL;

            GET DIAGNOSTICS affected_rows = ROW_COUNT;
            RETURN affected_rows = 1;
        END;
        $$;

        REVOKE ALL ON FUNCTION claim_subscription_plan_transition(uuid, jsonb)
            FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION claim_subscription_plan_transition(uuid, jsonb)
            TO service_role;
        """
    )
    op.execute(
        """
        CREATE FUNCTION clear_subscription_plan_transition(
            p_subscription_id uuid,
            p_transition_id text
        ) RETURNS boolean
        LANGUAGE plpgsql
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            affected_rows integer;
        BEGIN
            UPDATE organization_subscriptions
               SET pending_plan_transition = NULL,
                   updated_at = now()
             WHERE id = p_subscription_id
               AND pending_plan_transition->>'transition_id' = p_transition_id;

            GET DIAGNOSTICS affected_rows = ROW_COUNT;
            RETURN affected_rows = 1;
        END;
        $$;

        REVOKE ALL ON FUNCTION clear_subscription_plan_transition(uuid, text)
            FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION clear_subscription_plan_transition(uuid, text)
            TO service_role;
        """
    )


def downgrade() -> None:
    """Remove transition functions and their subscription marker column."""
    op.execute("DROP FUNCTION clear_subscription_plan_transition(uuid, text)")
    op.execute("DROP FUNCTION claim_subscription_plan_transition(uuid, jsonb)")
    op.drop_column("organization_subscriptions", "pending_plan_transition")
