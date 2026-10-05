"""Make Stripe credit top-up grants atomic and idempotent.

Revision ID: 20261001000003
Revises: 20261001000002
Create Date: 2026-10-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261001000003"
down_revision: Union[str, Sequence[str], None] = "20261001000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Deduplicate purchased credit grants by Stripe payment intent."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM credit_transactions
                WHERE source = 'purchase'
                  AND stripe_payment_intent_id IS NOT NULL
                GROUP BY stripe_payment_intent_id
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Duplicate purchased credit transactions exist for a Stripe payment intent; reconcile them before applying 20261001000003';
            END IF;
        END;
        $$;
        """
    )
    op.create_index(
        "uq_credit_transactions_purchase_payment_intent",
        "credit_transactions",
        ["stripe_payment_intent_id"],
        unique=True,
        postgresql_where=sa.text(
            "source = 'purchase' AND stripe_payment_intent_id IS NOT NULL"
        ),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION grant_purchased_credits(
            p_organization_id uuid,
            p_credits integer,
            p_payment_intent_id text,
            p_description text
        ) RETURNS jsonb
        LANGUAGE plpgsql
        SET search_path = public
        AS $$
        DECLARE
            v_plan integer;
            v_admin integer;
            v_purchased integer;
            v_existing credit_transactions;
            v_transaction credit_transactions;
            v_balance_after integer;
        BEGIN
            IF p_credits IS NULL OR p_credits <= 0 THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_credits');
            END IF;
            IF p_payment_intent_id IS NULL OR btrim(p_payment_intent_id) = '' THEN
                RETURN jsonb_build_object('success', false, 'error', 'payment_intent_required');
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

            SELECT * INTO v_existing
            FROM credit_transactions
            WHERE source = 'purchase'
              AND stripe_payment_intent_id = p_payment_intent_id
            LIMIT 1;

            IF FOUND THEN
                IF v_existing.organization_id <> p_organization_id THEN
                    RETURN jsonb_build_object('success', false, 'error', 'payment_intent_already_used');
                END IF;
                RETURN jsonb_build_object(
                    'success', true,
                    'already_applied', true,
                    'transaction', to_jsonb(v_existing),
                    'balance_after', v_plan + v_admin + v_purchased
                );
            END IF;

            v_balance_after := v_plan + v_admin + v_purchased + p_credits;

            -- The organization row lock serializes retries for one customer.
            -- The unique index also prevents one Stripe payment from being
            -- granted to two organizations concurrently.
            BEGIN
                UPDATE organizations
                SET purchased_credit_balance = v_purchased + p_credits,
                    low_credit_threshold_notified = NULL,
                    updated_at = NOW()
                WHERE id = p_organization_id;

                INSERT INTO credit_transactions (
                    organization_id,
                    transaction_type,
                    amount,
                    balance_after,
                    source,
                    stripe_payment_intent_id,
                    description,
                    metadata
                ) VALUES (
                    p_organization_id,
                    'purchased',
                    p_credits,
                    v_balance_after,
                    'purchase',
                    p_payment_intent_id,
                    p_description,
                    jsonb_build_object('grant_key', 'stripe-payment-intent:' || p_payment_intent_id)
                )
                RETURNING * INTO v_transaction;
            EXCEPTION WHEN unique_violation THEN
                -- Roll back the balance update in this block, then report an
                -- already-applied grant only when it belongs to this org.
                SELECT * INTO v_existing
                FROM credit_transactions
                WHERE source = 'purchase'
                  AND stripe_payment_intent_id = p_payment_intent_id
                LIMIT 1;
                IF FOUND AND v_existing.organization_id = p_organization_id THEN
                    RETURN jsonb_build_object(
                        'success', true,
                        'already_applied', true,
                        'transaction', to_jsonb(v_existing),
                        'balance_after', v_plan + v_admin + v_purchased
                    );
                END IF;
                RETURN jsonb_build_object('success', false, 'error', 'payment_intent_already_used');
            END;

            RETURN jsonb_build_object(
                'success', true,
                'already_applied', false,
                'transaction', to_jsonb(v_transaction),
                'balance_after', v_balance_after
            );
        END;
        $$;
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION grant_purchased_credits(uuid, integer, text, text) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION grant_purchased_credits(uuid, integer, text, text) TO service_role"
    )


def downgrade() -> None:
    """Restore the prior grant implementation after removing its RPC."""
    op.execute(
        "DROP FUNCTION IF EXISTS grant_purchased_credits(uuid, integer, text, text)"
    )
    op.drop_index(
        "uq_credit_transactions_purchase_payment_intent",
        table_name="credit_transactions",
    )
