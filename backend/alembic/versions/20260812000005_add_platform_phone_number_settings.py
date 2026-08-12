"""Add platform-admin phone-number lifecycle settings singleton.

Revision ID: 20260812000005
Revises: 20260812000004
Create Date: 2026-08-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260812000005"
down_revision: Union[str, None] = "20260812000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SINGLETON_ID = "00000000-0000-0000-0000-000000000002"


def upgrade() -> None:
    """Create the singleton row used by the platform-admin settings API."""
    op.create_table(
        "platform_phone_number_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "billing_grace_period_days",
            sa.Integer(),
            server_default=sa.text("7"),
            nullable=False,
            comment="Days incoming calls remain disabled before unpaid release",
        ),
        sa.Column(
            "billing_check_interval_hours",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("24"),
            nullable=False,
            comment="How often due rental billing is checked",
        ),
        sa.Column(
            "release_retry_interval_hours",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("24"),
            nullable=False,
            comment="How often provider release-pending rows are retried",
        ),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "billing_grace_period_days > 0",
            name="phone_settings_grace_period_positive",
        ),
        sa.CheckConstraint(
            "billing_check_interval_hours > 0",
            name="phone_settings_billing_interval_positive",
        ),
        sa.CheckConstraint(
            "release_retry_interval_hours > 0",
            name="phone_settings_release_interval_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        "INSERT INTO platform_phone_number_settings (id) " f"VALUES ('{SINGLETON_ID}')"
    )
    op.execute("ALTER TABLE platform_phone_number_settings ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY "Service role manages platform phone number settings"
        ON platform_phone_number_settings
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION consume_phone_number_credits(
            p_organization_id uuid,
            p_credit_event_id uuid,
            p_credits_needed integer,
            p_idempotency_key text,
            p_phone_number text,
            p_purpose text
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_admin integer;
            v_purchased integer;
            v_plan_used integer;
            v_admin_used integer;
            v_purchased_used integer;
            v_remaining integer;
            v_balance_after integer;
            v_transaction_id uuid;
            v_existing_balance integer;
        BEGIN
            IF p_credits_needed IS NULL OR p_credits_needed <= 0 THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'invalid_credits_needed'
                );
            END IF;

            -- Lock the organization before checking the key. Concurrent
            -- requests for one organization therefore serialize the lookup,
            -- debit, and ledger insert as one transaction.
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

            IF p_idempotency_key IS NOT NULL THEN
                SELECT id, balance_after
                INTO v_transaction_id, v_existing_balance
                FROM credit_transactions
                WHERE organization_id = p_organization_id
                  AND metadata->>'idempotency_key' = p_idempotency_key
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
            END IF;

            v_plan := COALESCE(v_plan, 0);
            v_admin := COALESCE(v_admin, 0);
            v_purchased := COALESCE(v_purchased, 0);
            IF v_plan + v_admin + v_purchased < p_credits_needed THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'insufficient_credits',
                    'balance_after', v_plan + v_admin + v_purchased
                );
            END IF;

            v_plan_used := LEAST(GREATEST(v_plan, 0), p_credits_needed);
            v_remaining := p_credits_needed - v_plan_used;
            v_admin_used := LEAST(GREATEST(v_admin, 0), v_remaining);
            v_remaining := v_remaining - v_admin_used;
            v_purchased_used := LEAST(GREATEST(v_purchased, 0), v_remaining);
            v_balance_after := v_plan - v_plan_used
                + v_admin - v_admin_used
                + v_purchased - v_purchased_used;

            UPDATE organizations
            SET credit_balance = v_plan - v_plan_used,
                admin_credit_balance = v_admin - v_admin_used,
                purchased_credit_balance = v_purchased - v_purchased_used,
                updated_at = NOW()
            WHERE id = p_organization_id;

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
                'Phone-number rental credit consumption',
                jsonb_build_object(
                    'idempotency_key', p_idempotency_key,
                    'phone_number', p_phone_number,
                    'purpose', COALESCE(p_purpose, 'phone_number_purchase'),
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
                'credits_consumed', p_credits_needed
            );
        END;
        $$;
        """
    )


def downgrade() -> None:
    """Remove the platform phone-number settings table."""
    op.execute(
        "DROP FUNCTION IF EXISTS consume_phone_number_credits(uuid, uuid, integer, text, text, text)"
    )
    op.execute(
        'DROP POLICY IF EXISTS "Service role manages platform phone number settings" '
        "ON platform_phone_number_settings"
    )
    op.execute("ALTER TABLE platform_phone_number_settings DISABLE ROW LEVEL SECURITY")
    op.drop_table("platform_phone_number_settings")
