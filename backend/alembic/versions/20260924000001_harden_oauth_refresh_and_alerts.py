"""Fence OAuth token refreshes and persist urgent admin alerts.

Revision ID: 20260924000001
Revises: 20260923000001
Create Date: 2026-09-24 00:00:01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924000001"
down_revision: Union[str, None] = "20260923000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add refresh fencing/state, SMS routing, and a durable channel outbox."""
    op.add_column(
        "agent_tools",
        sa.Column(
            "oauth_credential_version",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "agent_tools",
        sa.Column(
            "oauth_refresh_status", sa.Text(), nullable=False, server_default="ready"
        ),
    )
    op.add_column(
        "agent_tools",
        sa.Column(
            "oauth_refresh_started_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "agent_tools", sa.Column("oauth_refresh_error_code", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "ck_agent_tools_oauth_refresh_status",
        "agent_tools",
        "oauth_refresh_status IN ('ready', 'refreshing', 'outcome_unknown', "
        "'reauth_required', 'configuration_error', 'credentials_unreadable')",
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION reset_oauth_refresh_state_on_credentials_change()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.sensitive_config IS DISTINCT FROM OLD.sensitive_config THEN
                NEW.oauth_credential_version := OLD.oauth_credential_version + 1;
                NEW.oauth_refresh_status := 'ready';
                NEW.oauth_refresh_started_at := NULL;
                NEW.oauth_refresh_error_code := NULL;
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_reset_oauth_refresh_state_on_credentials_change
        BEFORE UPDATE OF sensitive_config ON agent_tools
        FOR EACH ROW EXECUTE FUNCTION reset_oauth_refresh_state_on_credentials_change();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION begin_token_refresh(
            p_tool_id uuid,
            p_claim text,
            p_expected_version bigint,
            p_lease_seconds int DEFAULT 180
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE agent_tools AS tool
               SET oauth_refresh_status = 'refreshing',
                   oauth_refresh_started_at = now(),
                   oauth_refresh_error_code = NULL,
                   updated_at = now()
             WHERE tool.id = p_tool_id
               AND tool.oauth_credential_version = p_expected_version
               AND tool.oauth_refresh_status = 'ready'
               AND EXISTS (
                   SELECT 1 FROM token_refresh_leases AS lease
                    WHERE lease.agent_tool_id = p_tool_id
                      AND lease.claim = p_claim
                       AND lease.locked_at >= now() - make_interval(
                           secs => p_lease_seconds
                       )
               );
            RETURN jsonb_build_object('begun', FOUND);
        END;
        $$;

        CREATE OR REPLACE FUNCTION update_token_refresh_status(
            p_tool_id uuid,
            p_claim text,
            p_expected_version bigint,
            p_status text,
            p_error_code text DEFAULT NULL,
            p_lease_seconds int DEFAULT 180
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF p_status NOT IN (
                'ready', 'outcome_unknown', 'reauth_required', 'configuration_error'
            ) THEN
                RAISE EXCEPTION 'invalid OAuth refresh status';
            END IF;
            UPDATE agent_tools AS tool
               SET oauth_refresh_status = p_status,
                   oauth_refresh_started_at = CASE WHEN p_status = 'outcome_unknown'
                       THEN tool.oauth_refresh_started_at ELSE NULL END,
                   oauth_refresh_error_code = p_error_code,
                   updated_at = now()
             WHERE tool.id = p_tool_id
               AND tool.oauth_credential_version = p_expected_version
               AND EXISTS (
                   SELECT 1 FROM token_refresh_leases AS lease
                    WHERE lease.agent_tool_id = p_tool_id
                      AND lease.claim = p_claim
                       AND lease.locked_at >= now() - make_interval(
                           secs => p_lease_seconds
                       )
               );
            RETURN jsonb_build_object('updated', FOUND);
        END;
        $$;

        CREATE OR REPLACE FUNCTION mark_oauth_credentials_unreadable(
            p_tool_id uuid,
            p_expected_version bigint
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE agent_tools
               SET oauth_refresh_status = 'credentials_unreadable',
                   oauth_refresh_error_code = 'encryption_key_unavailable',
                   updated_at = now()
             WHERE id = p_tool_id
               AND oauth_credential_version = p_expected_version
               AND oauth_refresh_status = 'ready';
            RETURN jsonb_build_object('updated', FOUND);
        END;
        $$;

        CREATE OR REPLACE FUNCTION recover_oauth_credentials_unreadable(
            p_tool_id uuid,
            p_expected_version bigint
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE agent_tools
               SET oauth_refresh_status = 'ready',
                   oauth_refresh_started_at = NULL,
                   oauth_refresh_error_code = NULL,
                   updated_at = now()
             WHERE id = p_tool_id
               AND oauth_credential_version = p_expected_version
               AND oauth_refresh_status = 'credentials_unreadable';
            RETURN jsonb_build_object('updated', FOUND);
        END;
        $$;

        CREATE OR REPLACE FUNCTION complete_token_refresh(
            p_tool_id uuid,
            p_claim text,
            p_expected_version bigint,
            p_encrypted_config text,
            p_refreshed_at timestamptz,
            p_lease_seconds int DEFAULT 180
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE agent_tools AS tool
               SET sensitive_config = p_encrypted_config,
                   last_refreshed_at = p_refreshed_at,
                   updated_at = now()
             WHERE tool.id = p_tool_id
               AND tool.oauth_credential_version = p_expected_version
               AND tool.oauth_refresh_status = 'refreshing'
               AND EXISTS (
                   SELECT 1 FROM token_refresh_leases AS lease
                    WHERE lease.agent_tool_id = p_tool_id
                      AND lease.claim = p_claim
                       AND lease.locked_at >= now() - make_interval(
                           secs => p_lease_seconds
                       )
               );
            RETURN jsonb_build_object('updated', FOUND);
        END;
        $$;
        """
    )

    op.add_column(
        "platform_notification_settings",
        sa.Column("platform_admin_sms_phone", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "platform_notification_settings",
        sa.Column(
            "platform_admin_sms_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_check_constraint(
        "ck_platform_admin_sms_phone_e164",
        "platform_notification_settings",
        "platform_admin_sms_phone IS NULL OR "
        "platform_admin_sms_phone ~ '^\\+[1-9][0-9]{1,14}$'",
    )

    op.create_table(
        "oauth_attention_outbox",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_key", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "agent_tool_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "telegram_state", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column("sms_state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "telegram_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("sms_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("lease_claim", sa.Text(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "telegram_state IN ('pending', 'sent', 'skipped')",
            name="ck_oauth_attention_telegram_state",
        ),
        sa.CheckConstraint(
            "sms_state IN ('pending', 'sent', 'skipped')",
            name="ck_oauth_attention_sms_state",
        ),
    )
    op.create_index(
        "ix_oauth_attention_outbox_due",
        "oauth_attention_outbox",
        ["available_at", "created_at"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )
    op.execute("ALTER TABLE oauth_attention_outbox ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION claim_oauth_attention_outbox(
            p_claim text,
            p_event_key text DEFAULT NULL,
            p_limit int DEFAULT 50,
            p_lease_seconds int DEFAULT 60
        ) RETURNS SETOF oauth_attention_outbox
        LANGUAGE sql
        AS $$
            WITH due AS (
                SELECT id
                  FROM oauth_attention_outbox
                 WHERE delivered_at IS NULL
                   AND available_at <= now()
                   AND (lease_until IS NULL OR lease_until < now())
                   AND (telegram_state = 'pending' OR sms_state = 'pending')
                   AND (p_event_key IS NULL OR event_key = p_event_key)
                 ORDER BY available_at, created_at
                 FOR UPDATE SKIP LOCKED
                 LIMIT LEAST(GREATEST(p_limit, 1), 100)
            )
            UPDATE oauth_attention_outbox AS outbox
               SET lease_claim = p_claim,
                   lease_until = now() + make_interval(secs => p_lease_seconds),
                   updated_at = now()
              FROM due
             WHERE outbox.id = due.id
            RETURNING outbox.*;
        $$;

        CREATE OR REPLACE FUNCTION complete_oauth_attention_outbox(
            p_id uuid,
            p_claim text,
            p_telegram_state text,
            p_sms_state text,
            p_attempted_telegram boolean,
            p_attempted_sms boolean,
            p_error_code text DEFAULT NULL,
            p_retry_seconds int DEFAULT 300
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            updated_id uuid;
        BEGIN
            IF p_telegram_state NOT IN ('pending', 'sent', 'skipped')
               OR p_sms_state NOT IN ('pending', 'sent', 'skipped') THEN
                RAISE EXCEPTION 'invalid OAuth attention delivery state';
            END IF;
            UPDATE oauth_attention_outbox AS outbox
               SET telegram_state = CASE WHEN outbox.telegram_state = 'pending'
                   THEN p_telegram_state ELSE outbox.telegram_state END,
                   sms_state = CASE WHEN outbox.sms_state = 'pending'
                   THEN p_sms_state ELSE outbox.sms_state END,
                    telegram_attempts = outbox.telegram_attempts + CASE
                        WHEN p_attempted_telegram THEN 1 ELSE 0 END,
                    sms_attempts = outbox.sms_attempts + CASE
                        WHEN p_attempted_sms THEN 1 ELSE 0 END,
                   available_at = CASE
                       WHEN p_telegram_state = 'pending' OR p_sms_state = 'pending'
                       THEN now() + make_interval(secs => GREATEST(p_retry_seconds, 30))
                       ELSE outbox.available_at END,
                   last_error_code = p_error_code,
                   lease_claim = NULL,
                   lease_until = NULL,
                   delivered_at = CASE
                        WHEN (CASE
                            WHEN outbox.telegram_state = 'pending' THEN p_telegram_state
                            ELSE outbox.telegram_state
                        END) <> 'pending'
                         AND (CASE
                            WHEN outbox.sms_state = 'pending' THEN p_sms_state
                            ELSE outbox.sms_state
                        END) <> 'pending'
                       THEN now() ELSE NULL END,
                   updated_at = now()
             WHERE outbox.id = p_id AND outbox.lease_claim = p_claim
            RETURNING outbox.id INTO updated_id;
            RETURN jsonb_build_object('updated', updated_id IS NOT NULL);
        END;
        $$;
        """
    )


def downgrade() -> None:
    """Remove OAuth alert delivery and refresh hardening fields/functions."""
    op.execute(
        "DROP FUNCTION IF EXISTS complete_oauth_attention_outbox("
        "uuid, text, text, text, boolean, boolean, text, int)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS claim_oauth_attention_outbox(text, text, int, int)"
    )
    op.drop_index("ix_oauth_attention_outbox_due", table_name="oauth_attention_outbox")
    op.drop_table("oauth_attention_outbox")
    op.drop_constraint(
        "ck_platform_admin_sms_phone_e164",
        "platform_notification_settings",
        type_="check",
    )
    op.drop_column(
        "platform_notification_settings", "platform_admin_sms_notifications_enabled"
    )
    op.drop_column("platform_notification_settings", "platform_admin_sms_phone")
    op.execute(
        "DROP FUNCTION IF EXISTS complete_token_refresh("
        "uuid, text, bigint, text, timestamptz, int)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS mark_oauth_credentials_unreadable(uuid, bigint)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS recover_oauth_credentials_unreadable(uuid, bigint)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS update_token_refresh_status("
        "uuid, text, bigint, text, text, int)"
    )
    op.execute("DROP FUNCTION IF EXISTS begin_token_refresh(uuid, text, bigint, int)")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_reset_oauth_refresh_state_on_credentials_change "
        "ON agent_tools"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS reset_oauth_refresh_state_on_credentials_change()"
    )
    op.drop_constraint(
        "ck_agent_tools_oauth_refresh_status", "agent_tools", type_="check"
    )
    op.drop_column("agent_tools", "oauth_refresh_error_code")
    op.drop_column("agent_tools", "oauth_refresh_started_at")
    op.drop_column("agent_tools", "oauth_refresh_status")
    op.drop_column("agent_tools", "oauth_credential_version")
