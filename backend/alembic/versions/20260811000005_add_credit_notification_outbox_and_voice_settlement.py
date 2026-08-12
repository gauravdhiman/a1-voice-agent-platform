"""Add durable low-credit evaluations and final-call overdraft settlement."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260811000005"
down_revision: Union[str, None] = "20260811000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the outbox and replace voice settlement with an atomic final debit."""
    op.create_table(
        "credit_notification_outbox",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("credit_transaction_id", sa.UUID(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column(
            "attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["credit_transaction_id"],
            ["credit_transactions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "credit_transaction_id", name="uq_credit_notification_outbox_transaction"
        ),
    )
    op.create_index(
        "ix_credit_notification_outbox_pending",
        "credit_notification_outbox",
        ["processed_at", "created_at"],
    )
    op.create_index(
        "ix_credit_notification_outbox_organization_id",
        "credit_notification_outbox",
        ["organization_id"],
    )
    op.execute("ALTER TABLE credit_notification_outbox ENABLE ROW LEVEL SECURITY")

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
            v_plan_available integer;
            v_admin_available integer;
            v_purchased_available integer;
            v_plan_used integer;
            v_admin_used integer;
            v_purchased_used integer;
            v_overdraft integer;
            v_plan_after integer;
            v_admin_after integer;
            v_purchased_after integer;
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
            v_plan_available := GREATEST(v_plan, 0);
            v_admin_available := GREATEST(v_admin, 0);
            v_purchased_available := GREATEST(v_purchased, 0);

            v_plan_used := LEAST(v_plan_available, p_credits_needed);
            v_admin_used := LEAST(
                v_admin_available,
                p_credits_needed - v_plan_used
            );
            v_purchased_used := LEAST(
                v_purchased_available,
                p_credits_needed - v_plan_used - v_admin_used
            );
            v_overdraft := p_credits_needed
                - v_plan_used - v_admin_used - v_purchased_used;

            -- The active call is allowed to finish. Keep the debt in the
            -- expiring plan pool so the combined balance reflects the full
            -- charge while purchased/admin pools never become negative.
            v_plan_after := v_plan - v_plan_used - v_overdraft;
            v_admin_after := v_admin - v_admin_used;
            v_purchased_after := v_purchased - v_purchased_used;
            v_balance_after := v_plan_after + v_admin_after + v_purchased_after;

            UPDATE organizations
            SET credit_balance = v_plan_after,
                admin_credit_balance = v_admin_after,
                purchased_credit_balance = v_purchased_after,
                updated_at = NOW()
            WHERE id = p_organization_id;

            INSERT INTO credit_transactions (
                organization_id, transaction_type, amount, balance_after,
                source, source_id, credit_event_id, description, metadata
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
                    'purchased_credits', v_purchased_used,
                    'overdraft_credits', v_overdraft
                )
            )
            RETURNING id INTO v_transaction_id;

            INSERT INTO credit_notification_outbox (
                organization_id, credit_transaction_id, balance_after
            ) VALUES (
                p_organization_id, v_transaction_id, v_balance_after
            )
            ON CONFLICT (credit_transaction_id) DO NOTHING;

            RETURN jsonb_build_object(
                'success', true,
                'transaction_id', v_transaction_id,
                'balance_after', v_balance_after,
                'plan_used', v_plan_used,
                'admin_used', v_admin_used,
                'purchased_used', v_purchased_used,
                'overdraft_used', v_overdraft
            );
        END;
        $$;
        """
    )


def downgrade() -> None:
    """Restore the prior function behavior and remove the outbox table."""
    op.execute(
        "DROP FUNCTION IF EXISTS consume_voice_call_credits(uuid, uuid, integer, uuid, integer)"
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
                organization_id, transaction_type, amount, balance_after,
                source, source_id, credit_event_id, description, metadata
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
    op.drop_index(
        "ix_credit_notification_outbox_organization_id",
        table_name="credit_notification_outbox",
    )
    op.drop_index(
        "ix_credit_notification_outbox_pending",
        table_name="credit_notification_outbox",
    )
    op.drop_table("credit_notification_outbox")
