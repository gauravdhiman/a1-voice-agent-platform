"""Add audited platform-granted credits and include them in prepaid debits.

Platform allocations are intentionally kept in a separate balance pool from
subscription and purchased credits. The grant table provides an immutable
actor/reason audit trail, while the existing credit ledger remains the single
reporting stream for all credit movements.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260809000003"
down_revision: Union[str, None] = "20260809000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the platform grant audit table and three-pool credit RPCs."""
    op.add_column(
        "organizations",
        sa.Column(
            "admin_credit_balance",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "platform_credit_grants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("credit_transactions.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("amount > 0", name="ck_platform_credit_grants_amount"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_platform_credit_grants_org_idempotency",
        ),
    )
    op.create_index(
        "ix_platform_credit_grants_organization_id",
        "platform_credit_grants",
        ["organization_id"],
    )
    op.create_index(
        "ix_platform_credit_grants_created_at",
        "platform_credit_grants",
        ["created_at"],
    )
    op.execute("ALTER TABLE platform_credit_grants ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION grant_admin_credits(
            p_organization_id uuid,
            p_credits integer,
            p_created_by uuid,
            p_reason text,
            p_idempotency_key text
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_admin integer;
            v_purchased integer;
            v_new_admin integer;
            v_balance_after integer;
            v_grant_id uuid;
            v_transaction credit_transactions;
            v_existing platform_credit_grants;
        BEGIN
            IF p_credits IS NULL OR p_credits <= 0 THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_credits');
            END IF;
            IF p_created_by IS NULL THEN
                RETURN jsonb_build_object('success', false, 'error', 'actor_required');
            END IF;
            IF p_reason IS NULL OR length(btrim(p_reason)) < 3 THEN
                RETURN jsonb_build_object('success', false, 'error', 'reason_required');
            END IF;

            SELECT credit_balance, admin_credit_balance, purchased_credit_balance
            INTO v_plan, v_admin, v_purchased
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
            v_admin := COALESCE(v_admin, 0);
            v_purchased := COALESCE(v_purchased, 0);

            IF NULLIF(btrim(p_idempotency_key), '') IS NOT NULL THEN
                SELECT *
                INTO v_existing
                FROM platform_credit_grants
                WHERE organization_id = p_organization_id
                  AND idempotency_key = NULLIF(btrim(p_idempotency_key), '')
                LIMIT 1;

                IF FOUND THEN
                    SELECT *
                    INTO v_transaction
                    FROM credit_transactions
                    WHERE id = v_existing.transaction_id;
                    RETURN jsonb_build_object(
                        'success', true,
                        'created', false,
                        'grant_id', v_existing.id,
                        'transaction', to_jsonb(v_transaction),
                        'plan_balance', v_plan,
                        'admin_balance', v_admin,
                        'purchased_balance', v_purchased,
                        'balance_after', v_plan + v_admin + v_purchased
                    );
                END IF;
            END IF;

            v_grant_id := gen_random_uuid();
            v_new_admin := v_admin + p_credits;
            v_balance_after := v_plan + v_new_admin + v_purchased;

            UPDATE organizations
            SET admin_credit_balance = v_new_admin,
                low_credit_threshold_notified = NULL,
                updated_at = NOW()
            WHERE id = p_organization_id;

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
                'earned',
                p_credits,
                v_balance_after,
                'admin_adjustment',
                'Platform admin credit allocation',
                jsonb_build_object(
                    'grant_id', v_grant_id,
                    'grant_key', NULLIF(btrim(p_idempotency_key), ''),
                    'admin_user_id', p_created_by,
                    'reason', btrim(p_reason),
                    'credit_pool', 'admin_bonus'
                )
            )
            RETURNING * INTO v_transaction;

            INSERT INTO platform_credit_grants (
                id,
                organization_id,
                transaction_id,
                amount,
                reason,
                created_by,
                idempotency_key
            ) VALUES (
                v_grant_id,
                p_organization_id,
                v_transaction.id,
                p_credits,
                btrim(p_reason),
                p_created_by,
                NULLIF(btrim(p_idempotency_key), '')
            );

            RETURN jsonb_build_object(
                'success', true,
                'created', true,
                'grant_id', v_grant_id,
                'transaction', to_jsonb(v_transaction),
                'plan_balance', v_plan,
                'admin_balance', v_new_admin,
                'purchased_balance', v_purchased,
                'balance_after', v_balance_after
            );
        END;
        $$;
        """
    )

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
            v_admin integer;
            v_purchased integer;
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
            v_total := v_plan + v_admin + v_purchased;

            v_plan_used := LEAST(v_plan, p_credits_needed);
            v_remaining := p_credits_needed - v_plan_used;
            v_admin_used := LEAST(v_admin, v_remaining);
            v_remaining := v_remaining - v_admin_used;
            v_purchased_used := LEAST(v_purchased, v_remaining);

            IF v_plan_used + v_admin_used + v_purchased_used < p_credits_needed THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'balance_after', v_total,
                    'plan_balance', v_plan,
                    'admin_balance', v_admin,
                    'purchased_balance', v_purchased
                );
            END IF;

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
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION consume_voice_call_credits(
            p_organization_id uuid,
            p_credit_event_id uuid,
            p_credits_needed integer,
            p_call_log_id uuid,
            p_duration_seconds integer
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_admin integer;
            v_purchased integer;
            v_plan_used integer;
            v_admin_used integer;
            v_remaining integer;
            v_purchased_used integer;
            v_balance_after integer;
            v_transaction_id uuid;
            v_existing_balance integer;
        BEGIN
            IF p_credits_needed IS NULL OR p_credits_needed <= 0 THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_credits_needed');
            END IF;

            SELECT id, balance_after
            INTO v_transaction_id, v_existing_balance
            FROM credit_transactions
            WHERE organization_id = p_organization_id
              AND source = 'event_consumption'
              AND metadata->>'call_log_id' = p_call_log_id::text
            ORDER BY created_at DESC
            LIMIT 1;

            IF v_transaction_id IS NOT NULL THEN
                RETURN jsonb_build_object(
                    'success', true,
                    'already_recorded', true,
                    'transaction_id', v_transaction_id,
                    'balance_after', v_existing_balance
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
            v_plan_used := LEAST(v_plan, p_credits_needed);
            v_remaining := p_credits_needed - v_plan_used;
            v_admin_used := LEAST(v_admin, v_remaining);
            v_remaining := v_remaining - v_admin_used;
            v_purchased_used := v_remaining;

            IF v_purchased_used > v_purchased THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'insufficient_credits',
                    'balance_after', v_plan + v_admin + v_purchased
                );
            END IF;

            UPDATE organizations
            SET credit_balance = v_plan - v_plan_used,
                admin_credit_balance = v_admin - v_admin_used,
                purchased_credit_balance = v_purchased - v_purchased_used,
                updated_at = NOW()
            WHERE id = p_organization_id;

            v_balance_after := v_plan - v_plan_used
                + v_admin - v_admin_used
                + v_purchased - v_purchased_used;

            INSERT INTO credit_transactions (
                organization_id,
                transaction_type,
                amount,
                balance_after,
                source,
                source_id,
                credit_event_id,
                description,
                metadata
            ) VALUES (
                p_organization_id,
                'consumed',
                -p_credits_needed,
                v_balance_after,
                'event_consumption',
                p_credit_event_id,
                p_credit_event_id,
                'Voice call credit consumption',
                jsonb_build_object(
                    'call_log_id', p_call_log_id,
                    'duration_seconds', p_duration_seconds,
                    'plan_credits', v_plan_used,
                    'admin_credits', v_admin_used,
                    'purchased_credits', v_purchased_used
                )
            )
            RETURNING id INTO v_transaction_id;

            RETURN jsonb_build_object(
                'success', true,
                'transaction_id', v_transaction_id,
                'balance_after', v_balance_after,
                'plan_used', v_plan_used,
                'admin_used', v_admin_used,
                'purchased_used', v_purchased_used
            );
        END;
        $$;
        """
    )

    # Keep the subscription RPC's balance_after accurate when a platform
    # grant exists; it still mutates only the subscription pool.
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
            v_admin integer;
            v_purchased integer;
            v_new_plan integer;
            v_balance_after integer;
            v_existing credit_transactions;
            v_transaction credit_transactions;
        BEGIN
            IF p_credits IS NULL OR p_credits <= 0 THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_credits');
            END IF;
            IF p_subscription_id IS NULL THEN
                RETURN jsonb_build_object('success', false, 'error', 'subscription_not_found');
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

            IF p_idempotency_key IS NOT NULL THEN
                SELECT * INTO v_existing
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
                        'admin_balance', v_admin,
                        'purchased_balance', v_purchased,
                        'balance_after', v_plan + v_admin + v_purchased
                    );
                END IF;
            END IF;

            IF p_expires_at IS NOT NULL AND v_plan > 0 THEN
                INSERT INTO credit_transactions (
                    organization_id, transaction_type, amount, balance_after,
                    source, description, metadata
                ) VALUES (
                    p_organization_id, 'expired', -v_plan,
                    v_admin + v_purchased, 'expiry',
                    'Plan credits expired at period end',
                    jsonb_build_object('expired_by_grant_key', p_idempotency_key)
                );
                v_plan := 0;
            END IF;

            v_new_plan := v_plan + p_credits;
            v_balance_after := v_new_plan + v_admin + v_purchased;
            UPDATE organizations
            SET credit_balance = v_new_plan,
                low_credit_threshold_notified = NULL,
                updated_at = NOW()
            WHERE id = p_organization_id;

            INSERT INTO credit_transactions (
                organization_id, transaction_type, amount, balance_after,
                source, source_id, expires_at, description, metadata
            ) VALUES (
                p_organization_id, 'earned', p_credits, v_balance_after,
                'subscription', p_subscription_id, p_expires_at,
                p_description, p_metadata
            )
            RETURNING * INTO v_transaction;

            RETURN jsonb_build_object(
                'success', true,
                'already_applied', false,
                'transaction', to_jsonb(v_transaction),
                'plan_balance', v_new_plan,
                'admin_balance', v_admin,
                'purchased_balance', v_purchased,
                'balance_after', v_balance_after
            );
        END;
        $$;
        """
    )


def downgrade() -> None:
    """Remove platform grants and restore the prior two-pool functions."""
    op.execute(
        "DROP FUNCTION IF EXISTS grant_admin_credits(uuid, integer, uuid, text, text)"
    )
    op.drop_index(
        "ix_platform_credit_grants_created_at", table_name="platform_credit_grants"
    )
    op.drop_index(
        "ix_platform_credit_grants_organization_id", table_name="platform_credit_grants"
    )
    op.drop_table("platform_credit_grants")
    op.drop_column("organizations", "admin_credit_balance")

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
                RETURN jsonb_build_object('success', false, 'error', 'invalid_credits');
            END IF;
            IF p_subscription_id IS NULL THEN
                RETURN jsonb_build_object('success', false, 'error', 'subscription_not_found');
            END IF;

            SELECT credit_balance, purchased_credit_balance
            INTO v_plan, v_purchased
            FROM organizations
            WHERE id = p_organization_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RETURN jsonb_build_object('success', false, 'error', 'organization_not_found');
            END IF;

            v_plan := COALESCE(v_plan, 0);
            v_purchased := COALESCE(v_purchased, 0);
            IF p_idempotency_key IS NOT NULL THEN
                SELECT * INTO v_existing
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

            IF p_expires_at IS NOT NULL AND v_plan > 0 THEN
                INSERT INTO credit_transactions (
                    organization_id, transaction_type, amount, balance_after,
                    source, description, metadata
                ) VALUES (
                    p_organization_id, 'expired', -v_plan, v_purchased,
                    'expiry', 'Plan credits expired at period end',
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
                organization_id, transaction_type, amount, balance_after,
                source, source_id, expires_at, description, metadata
            ) VALUES (
                p_organization_id, 'earned', p_credits, v_balance_after,
                'subscription', p_subscription_id, p_expires_at,
                p_description, p_metadata
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

    op.execute(
        """
        CREATE OR REPLACE FUNCTION consume_voice_call_credits(
            p_organization_id uuid,
            p_credit_event_id uuid,
            p_credits_needed integer,
            p_call_log_id uuid,
            p_duration_seconds integer
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_purchased integer;
            v_plan_used integer;
            v_purchased_used integer;
            v_balance_after integer;
            v_transaction_id uuid;
            v_existing_balance integer;
        BEGIN
            IF p_credits_needed IS NULL OR p_credits_needed <= 0 THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_credits_needed');
            END IF;

            SELECT id, balance_after INTO v_transaction_id, v_existing_balance
            FROM credit_transactions
            WHERE organization_id = p_organization_id
              AND source = 'event_consumption'
              AND metadata->>'call_log_id' = p_call_log_id::text
            ORDER BY created_at DESC
            LIMIT 1;
            IF v_transaction_id IS NOT NULL THEN
                RETURN jsonb_build_object(
                    'success', true,
                    'already_recorded', true,
                    'transaction_id', v_transaction_id,
                    'balance_after', v_existing_balance
                );
            END IF;

            SELECT credit_balance, purchased_credit_balance
            INTO v_plan, v_purchased
            FROM organizations
            WHERE id = p_organization_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RETURN jsonb_build_object('success', false, 'error', 'organization_not_found');
            END IF;

            v_plan := COALESCE(v_plan, 0);
            v_purchased := COALESCE(v_purchased, 0);
            v_plan_used := LEAST(v_plan, p_credits_needed);
            v_purchased_used := p_credits_needed - v_plan_used;
            IF v_purchased_used > v_purchased THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'insufficient_credits',
                    'balance_after', v_plan + v_purchased
                );
            END IF;

            UPDATE organizations
            SET credit_balance = v_plan - v_plan_used,
                purchased_credit_balance = v_purchased - v_purchased_used,
                updated_at = NOW()
            WHERE id = p_organization_id;

            v_balance_after := v_plan - v_plan_used + v_purchased - v_purchased_used;
            INSERT INTO credit_transactions (
                organization_id, transaction_type, amount, balance_after,
                source, source_id, credit_event_id, description, metadata
            ) VALUES (
                p_organization_id, 'consumed', -p_credits_needed, v_balance_after,
                'event_consumption', p_credit_event_id, p_credit_event_id,
                'Voice call credit consumption',
                jsonb_build_object(
                    'call_log_id', p_call_log_id,
                    'duration_seconds', p_duration_seconds,
                    'plan_credits', v_plan_used,
                    'purchased_credits', v_purchased_used
                )
            )
            RETURNING id INTO v_transaction_id;

            RETURN jsonb_build_object(
                'success', true,
                'transaction_id', v_transaction_id,
                'balance_after', v_balance_after,
                'plan_used', v_plan_used,
                'purchased_used', v_purchased_used
            );
        END;
        $$;
        """
    )
