"""Preserve voice-call overdraft debt when charging later activities."""

from typing import Sequence, Union

from alembic import op

revision: str = "20260812000002"
down_revision: Union[str, None] = "20260812000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _debit_function_sql(*, allow_overdraft: bool) -> str:
    """Build the organization debit function for the requested balance policy.

    Args:
        allow_overdraft: Whether a negative plan balance from a completed voice
            call should be preserved while positive pools are consumed.

    Returns:
        SQL defining ``debit_organization_credits``.
    """
    if allow_overdraft:
        availability = """
            v_plan_available := GREATEST(v_plan, 0);
            v_admin_available := GREATEST(v_admin, 0);
            v_purchased_available := GREATEST(v_purchased, 0);
            v_total := v_plan + v_admin + v_purchased;

            IF v_total < p_credits_needed THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'balance_after', v_total,
                    'plan_balance', v_plan,
                    'admin_balance', v_admin,
                    'purchased_balance', v_purchased
                );
            END IF;
        """
    else:
        availability = """
            v_plan_available := v_plan;
            v_admin_available := v_admin;
            v_purchased_available := v_purchased;
            v_total := v_plan + v_admin + v_purchased;

            IF v_total < p_credits_needed THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'balance_after', v_total,
                    'plan_balance', v_plan,
                    'admin_balance', v_admin,
                    'purchased_balance', v_purchased
                );
            END IF;
        """

    return f"""
        CREATE OR REPLACE FUNCTION debit_organization_credits(
            p_organization_id uuid,
            p_credits_needed integer
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_admin integer;
            v_purchased integer;
            v_plan_available integer;
            v_admin_available integer;
            v_purchased_available integer;
            v_total integer;
            v_plan_used integer;
            v_admin_used integer;
            v_remaining integer;
            v_purchased_used integer;
            v_new_plan integer;
            v_new_admin integer;
            v_new_purchased integer;
        BEGIN
            IF p_credits_needed IS NULL OR p_credits_needed <= 0 THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'invalid_credits_needed'
                );
            END IF;

            SELECT credit_balance, admin_credit_balance, purchased_credit_balance
            INTO v_plan, v_admin, v_purchased
            FROM organizations
            WHERE id = p_organization_id
            FOR UPDATE;

            IF NOT FOUND THEN
                RETURN jsonb_build_object('success', false, 'error', 'organization_not_found');
            END IF;

            v_plan := COALESCE(v_plan, 0);
            v_admin := COALESCE(v_admin, 0);
            v_purchased := COALESCE(v_purchased, 0);
{availability}

            v_plan_used := LEAST(v_plan_available, p_credits_needed);
            v_remaining := p_credits_needed - v_plan_used;
            v_admin_used := LEAST(v_admin_available, v_remaining);
            v_remaining := v_remaining - v_admin_used;
            v_purchased_used := LEAST(v_purchased_available, v_remaining);

            v_new_plan := v_plan - v_plan_used;
            v_new_admin := v_admin - v_admin_used;
            v_new_purchased := v_purchased - v_purchased_used;

            UPDATE organizations
            SET credit_balance = v_new_plan,
                admin_credit_balance = v_new_admin,
                purchased_credit_balance = v_new_purchased,
                updated_at = NOW()
            WHERE id = p_organization_id;

            RETURN jsonb_build_object(
                'success', true,
                'balance_after', v_new_plan + v_new_admin + v_new_purchased,
                'plan_balance', v_new_plan,
                'admin_balance', v_new_admin,
                'purchased_balance', v_new_purchased,
                'plan_used', v_plan_used,
                'admin_used', v_admin_used,
                'purchased_used', v_purchased_used
            );
        END;
        $$;
    """


def upgrade() -> None:
    """Make regular debits compatible with completed-call overdraft settlement."""
    op.execute(_debit_function_sql(allow_overdraft=True))


def downgrade() -> None:
    """Restore strict prepaid debits when reverting this compatibility fix."""
    op.execute(_debit_function_sql(allow_overdraft=False))
