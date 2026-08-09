"""Add an atomic, idempotent subscription credit grant RPC.

Subscription activation and renewal previously updated the organization
balance before inserting the credit ledger row. A serialization or database
failure could therefore leave an untracked balance increase. This function
keeps expiry bookkeeping, balance mutation, and ledger insertion in one
transaction and uses the stable grant key to make retries safe.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260808000012"
down_revision: Union[str, None] = "20260808000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the atomic subscription credit grant function."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION grant_subscription_credits(
            p_organization_id uuid,
            p_credits integer,
            p_subscription_id uuid,
            p_expires_at timestamptz,
            p_metadata jsonb,
            p_description text,
            p_idempotency_key text
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_purchased integer;
            v_new_plan integer;
            v_balance_after integer;
            v_existing credit_transactions;
            v_transaction credit_transactions;
        BEGIN
            IF p_credits IS NULL OR p_credits <= 0 THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'invalid_credits'
                );
            END IF;

            IF p_subscription_id IS NULL THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'subscription_not_found'
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

            IF p_idempotency_key IS NOT NULL THEN
                SELECT *
                INTO v_existing
                FROM credit_transactions
                WHERE organization_id = p_organization_id
                  AND source = 'subscription'
                  AND metadata->>'grant_key' = p_idempotency_key
                ORDER BY created_at
                LIMIT 1;

                IF FOUND THEN
                    RETURN jsonb_build_object(
                        'success', true,
                        'already_applied', true,
                        'transaction', to_jsonb(v_existing),
                        'plan_balance', v_plan,
                        'purchased_balance', v_purchased,
                        'balance_after', v_plan + v_purchased
                    );
                END IF;
            END IF;

            -- A recurring grant replaces leftover plan credits at renewal.
            -- The organization row remains locked until the expiry row and
            -- the new grant row have both been written.
            IF p_expires_at IS NOT NULL AND v_plan > 0 THEN
                INSERT INTO credit_transactions (
                    organization_id,
                    transaction_type,
                    amount,
                    balance_after,
                    source,
                    description,
                    metadata
                ) VALUES (
                    p_organization_id,
                    'expired',
                    -v_plan,
                    v_purchased,
                    'expiry',
                    'Plan credits expired at period end',
                    jsonb_build_object('expired_by_grant_key', p_idempotency_key)
                );
                v_plan := 0;
            END IF;

            v_new_plan := v_plan + p_credits;
            v_balance_after := v_new_plan + v_purchased;

            UPDATE organizations
            SET credit_balance = v_new_plan,
                low_credit_threshold_notified = NULL,
                updated_at = NOW()
            WHERE id = p_organization_id;

            INSERT INTO credit_transactions (
                organization_id,
                transaction_type,
                amount,
                balance_after,
                source,
                source_id,
                expires_at,
                description,
                metadata
            ) VALUES (
                p_organization_id,
                'earned',
                p_credits,
                v_balance_after,
                'subscription',
                p_subscription_id,
                p_expires_at,
                p_description,
                p_metadata
            )
            RETURNING * INTO v_transaction;

            RETURN jsonb_build_object(
                'success', true,
                'already_applied', false,
                'transaction', to_jsonb(v_transaction),
                'plan_balance', v_new_plan,
                'purchased_balance', v_purchased,
                'balance_after', v_balance_after
            );
        END;
        $$;
        """
    )


def downgrade() -> None:
    """Remove the atomic subscription credit grant function."""
    op.execute(
        "DROP FUNCTION IF EXISTS grant_subscription_credits(uuid, integer, uuid, timestamptz, jsonb, text, text)"
    )
