"""Add bounded call budgets for public demo voice agents.

Revision ID: 20260827000001
Revises: 20260820000002, 20260821000001
Create Date: 2026-08-27

Demo call reservations are created atomically at token issuance. This prevents
concurrent public callers from consuming the same remaining call and gives the
voice WebSocket a one-time reservation to consume before admitting a call.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260827000001"
down_revision: Union[str, Sequence[str], None] = (
    "20260820000002",
    "20260821000001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_agents",
        sa.Column(
            "demo_calls_remaining",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("-1"),
        ),
    )
    op.add_column(
        "voice_agents",
        sa.Column(
            "demo_max_call_duration_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("-1"),
        ),
    )
    op.create_check_constraint(
        "ck_voice_agents_demo_calls_remaining",
        "voice_agents",
        "demo_calls_remaining >= -1",
    )
    op.create_check_constraint(
        "ck_voice_agents_demo_max_call_duration_seconds",
        "voice_agents",
        "demo_max_call_duration_seconds = -1 OR demo_max_call_duration_seconds > 0",
    )

    op.create_table(
        "demo_call_reservations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("voice_agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'reserved'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_id", name="uq_demo_call_reservations_session_id"),
        sa.CheckConstraint(
            "status IN ('reserved', 'consumed')",
            name="ck_demo_call_reservations_status",
        ),
    )
    op.create_index(
        "ix_demo_call_reservations_agent_created_at",
        "demo_call_reservations",
        ["agent_id", "created_at"],
    )
    op.execute("ALTER TABLE demo_call_reservations ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE demo_call_reservations FROM PUBLIC")
    op.execute("GRANT ALL ON TABLE demo_call_reservations TO service_role")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION reserve_demo_voice_call(
            p_agent_id uuid,
            p_session_id text
        )
        RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            v_agent_calls_remaining integer;
            v_max_call_duration_seconds integer;
            v_reservation_id uuid;
            v_existing_agent_id uuid;
            v_existing_status text;
        BEGIN
            IF p_session_id IS NULL OR btrim(p_session_id) = '' THEN
                RETURN jsonb_build_object('success', false, 'error', 'invalid_session');
            END IF;

            SELECT id, agent_id, status
            INTO v_reservation_id, v_existing_agent_id, v_existing_status
            FROM demo_call_reservations
            WHERE session_id = p_session_id
            FOR UPDATE;

            IF FOUND THEN
                IF v_existing_agent_id <> p_agent_id THEN
                    RETURN jsonb_build_object('success', false, 'error', 'invalid_session');
                END IF;
                IF v_existing_status <> 'reserved' THEN
                    RETURN jsonb_build_object('success', false, 'error', 'demo_call_already_used');
                END IF;

                SELECT demo_calls_remaining, demo_max_call_duration_seconds
                INTO v_agent_calls_remaining, v_max_call_duration_seconds
                FROM voice_agents
                WHERE id = p_agent_id AND is_demo = true AND is_active = true;

                IF NOT FOUND THEN
                    RETURN jsonb_build_object('success', false, 'error', 'demo_agent_unavailable');
                END IF;

                RETURN jsonb_build_object(
                    'success', true,
                    'already_reserved', true,
                    'reservation_id', v_reservation_id,
                    'session_id', p_session_id,
                    'calls_remaining', v_agent_calls_remaining,
                    'max_call_duration_seconds', v_max_call_duration_seconds
                );
            END IF;

            SELECT demo_calls_remaining, demo_max_call_duration_seconds
            INTO v_agent_calls_remaining, v_max_call_duration_seconds
            FROM voice_agents
            WHERE id = p_agent_id AND is_demo = true AND is_active = true
            FOR UPDATE;

            IF NOT FOUND THEN
                RETURN jsonb_build_object('success', false, 'error', 'demo_agent_unavailable');
            END IF;

            IF v_agent_calls_remaining = 0 THEN
                RETURN jsonb_build_object(
                    'success', false,
                    'error', 'demo_call_limit_reached',
                    'calls_remaining', 0,
                    'max_call_duration_seconds', v_max_call_duration_seconds
                );
            END IF;

            UPDATE voice_agents
            SET demo_calls_remaining = CASE
                WHEN demo_calls_remaining = -1 THEN -1
                ELSE demo_calls_remaining - 1
            END,
                updated_at = now()
            WHERE id = p_agent_id;

            INSERT INTO demo_call_reservations (agent_id, session_id)
            VALUES (p_agent_id, p_session_id)
            RETURNING id INTO v_reservation_id;

            RETURN jsonb_build_object(
                'success', true,
                'already_reserved', false,
                'reservation_id', v_reservation_id,
                'session_id', p_session_id,
                'calls_remaining', CASE
                    WHEN v_agent_calls_remaining = -1 THEN -1
                    ELSE v_agent_calls_remaining - 1
                END,
                'max_call_duration_seconds', v_max_call_duration_seconds
            );
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION consume_demo_voice_call(
            p_agent_id uuid,
            p_session_id text,
            p_reservation_id uuid
        )
        RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            v_status text;
        BEGIN
            UPDATE demo_call_reservations
            SET status = 'consumed', consumed_at = now()
            WHERE id = p_reservation_id
              AND agent_id = p_agent_id
              AND session_id = p_session_id
              AND status = 'reserved';

            IF FOUND THEN
                RETURN jsonb_build_object('success', true);
            END IF;

            SELECT status
            INTO v_status
            FROM demo_call_reservations
            WHERE id = p_reservation_id
              AND agent_id = p_agent_id
              AND session_id = p_session_id;

            IF v_status = 'consumed' THEN
                RETURN jsonb_build_object('success', false, 'error', 'demo_call_already_used');
            END IF;
            RETURN jsonb_build_object('success', false, 'error', 'demo_call_reservation_not_found');
        END;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION reserve_demo_voice_call(uuid, text) FROM PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION reserve_demo_voice_call(uuid, text) TO service_role"
    )
    op.execute(
        "REVOKE ALL ON FUNCTION consume_demo_voice_call(uuid, text, uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION consume_demo_voice_call(uuid, text, uuid) TO service_role"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS consume_demo_voice_call(uuid, text, uuid)")
    op.execute("DROP FUNCTION IF EXISTS reserve_demo_voice_call(uuid, text)")
    op.drop_index(
        "ix_demo_call_reservations_agent_created_at",
        table_name="demo_call_reservations",
    )
    op.drop_table("demo_call_reservations")
    op.drop_constraint(
        "ck_voice_agents_demo_max_call_duration_seconds",
        "voice_agents",
        type_="check",
    )
    op.drop_constraint(
        "ck_voice_agents_demo_calls_remaining",
        "voice_agents",
        type_="check",
    )
    op.drop_column("voice_agents", "demo_max_call_duration_seconds")
    op.drop_column("voice_agents", "demo_calls_remaining")
