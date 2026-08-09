"""Add atomic debit_organization_credits RPC for concurrent-safe consumption.

Revision ID: 20260807000007
Revises: 20260807000006
Create Date: 2026-08-08

Locks the organization row (``SELECT … FOR UPDATE``) while allocating and
debiting plan + purchased credit pools. Prevents concurrent voice sessions from
overspending the combined prepaid balance.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260807000007"
down_revision: Union[str, None] = "20260807000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION debit_organization_credits(
            p_organization_id uuid,
            p_credits_needed integer
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_purchased integer;
            v_total integer;
            v_plan_used integer;
            v_remaining integer;
            v_purchased_used integer;
            v_new_plan integer;
            v_new_purchased integer;
        BEGIN
            IF p_credits_needed IS NULL OR p_credits_needed <= 0 THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'invalid_credits_needed'
                );
            END IF;

            SELECT credit_balance, purchased_credit_balance
            INTO v_plan, v_purchased
            FROM organizations
            WHERE id = p_organization_id
            FOR UPDATE;

            IF NOT FOUND THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'organization_not_found'
                );
            END IF;

            v_plan := COALESCE(v_plan, 0);
            v_purchased := COALESCE(v_purchased, 0);
            v_total := v_plan + v_purchased;

            v_plan_used := LEAST(v_plan, p_credits_needed);
            v_remaining := p_credits_needed - v_plan_used;
            v_purchased_used := LEAST(v_purchased, v_remaining);

            IF v_plan_used + v_purchased_used < p_credits_needed THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'balance_after', v_total,
                    'plan_balance', v_plan,
                    'purchased_balance', v_purchased
                );
            END IF;

            v_new_plan := v_plan - v_plan_used;
            v_new_purchased := v_purchased - v_purchased_used;

            UPDATE organizations
            SET credit_balance = v_new_plan,
                purchased_credit_balance = v_new_purchased,
                updated_at = NOW()
            WHERE id = p_organization_id;

            RETURN jsonb_build_object(
                'success', true,
                'balance_after', v_new_plan + v_new_purchased,
                'plan_balance', v_new_plan,
                'purchased_balance', v_new_purchased,
                'plan_used', v_plan_used,
                'purchased_used', v_purchased_used
            );
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS debit_organization_credits(uuid, integer)")
