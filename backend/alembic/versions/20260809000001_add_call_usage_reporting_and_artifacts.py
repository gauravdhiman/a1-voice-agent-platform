"""Add per-call credit linkage and call artifact metadata.

Audio bytes remain in private object storage; this migration stores only the
organization-scoped metadata needed to locate and authorize those artifacts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809000001"
down_revision: Union[str, None] = "20260808000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add credit reporting columns and the normalized call artifact table."""
    op.execute(
        """
        INSERT INTO credit_events (name, description, credit_cost, category)
        VALUES ('voice_call_minute', 'One connected voice-call minute', 10, 'voice')
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.add_column(
        "call_logs",
        sa.Column("credits_consumed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "call_logs",
        sa.Column(
            "credit_transaction_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_call_logs_credit_transaction_id",
        "call_logs",
        "credit_transactions",
        ["credit_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_call_logs_credit_transaction_id",
        "call_logs",
        ["credit_transaction_id"],
    )

    op.create_table(
        "call_artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "call_log_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_type", sa.String(length=30), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("storage_bucket", sa.String(length=120), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "call_log_id", "artifact_type", name="uq_call_artifacts_call_type"
        ),
        sa.CheckConstraint(
            "artifact_type IN ('recording', 'transcript', 'summary')",
            name="ck_call_artifacts_type",
        ),
    )
    op.create_index(
        "ix_call_artifacts_organization_id",
        "call_artifacts",
        ["organization_id"],
    )
    op.create_index("ix_call_artifacts_call_log_id", "call_artifacts", ["call_log_id"])

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
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'invalid_credits_needed'
                );
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

            v_balance_after := v_plan - v_plan_used
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


def downgrade() -> None:
    """Remove call artifact metadata and per-call billing linkage."""
    op.execute(
        "DROP FUNCTION IF EXISTS consume_voice_call_credits(uuid, uuid, integer, uuid, integer)"
    )
    op.drop_index("ix_call_artifacts_call_log_id", table_name="call_artifacts")
    op.drop_index("ix_call_artifacts_organization_id", table_name="call_artifacts")
    op.drop_table("call_artifacts")
    op.drop_index("ix_call_logs_credit_transaction_id", table_name="call_logs")
    op.drop_constraint(
        "fk_call_logs_credit_transaction_id", "call_logs", type_="foreignkey"
    )
    op.drop_column("call_logs", "credit_transaction_id")
    op.drop_column("call_logs", "credits_consumed")
