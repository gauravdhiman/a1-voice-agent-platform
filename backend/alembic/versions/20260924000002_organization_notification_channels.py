"""Add organization OAuth alert destinations and durable channel states.

Revision ID: 20260924000002
Revises: 20260924000001
Create Date: 2026-09-24 00:00:02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260924000002"
down_revision: Union[str, None] = "20260924000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist tenant alert destinations and extend the retryable outbox."""
    op.create_table(
        "organization_notification_settings",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("alert_email", sa.String(length=320), nullable=True),
        sa.Column("sms_phone", sa.String(length=32), nullable=True),
        sa.Column(
            "sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("telegram_chat_id", sa.String(length=100), nullable=True),
        sa.Column(
            "telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.CheckConstraint(
            "alert_email IS NULL OR length(alert_email) <= 320",
            name="ck_org_notification_alert_email_length",
        ),
        sa.CheckConstraint(
            "sms_phone IS NULL OR sms_phone ~ '^\\+[1-9][0-9]{1,14}$'",
            name="ck_org_notification_sms_phone_e164",
        ),
        sa.CheckConstraint(
            "telegram_chat_id IS NULL OR telegram_chat_id ~ "
            "'^(-?[0-9]{1,20}|@[A-Za-z0-9_]{5,32})$'",
            name="ck_org_notification_telegram_destination",
        ),
        sa.CheckConstraint(
            "NOT sms_enabled OR sms_phone IS NOT NULL",
            name="ck_org_notification_sms_enabled_has_phone",
        ),
        sa.CheckConstraint(
            "NOT telegram_enabled OR telegram_chat_id IS NOT NULL",
            name="ck_org_notification_telegram_enabled_has_chat_id",
        ),
    )
    op.execute(
        "ALTER TABLE organization_notification_settings ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY organization_notification_settings_service_role_all "
        "ON organization_notification_settings FOR ALL TO service_role "
        "USING (true) WITH CHECK (true)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON organization_notification_settings "
        "TO service_role"
    )
    op.execute(
        """
        CREATE FUNCTION update_organization_notification_settings(
            p_organization_id uuid,
            p_updated_by uuid,
            p_updates jsonb
        ) RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            updated_row public.organization_notification_settings%ROWTYPE;
        BEGIN
            IF p_updates IS NULL OR jsonb_typeof(p_updates) <> 'object' THEN
                RAISE EXCEPTION 'notification settings update must be a JSON object';
            END IF;

            INSERT INTO public.organization_notification_settings (
                organization_id,
                alert_email,
                sms_phone,
                sms_enabled,
                telegram_chat_id,
                telegram_enabled,
                updated_by
            ) VALUES (
                p_organization_id,
                nullif(p_updates ->> 'alert_email', ''),
                nullif(p_updates ->> 'sms_phone', ''),
                coalesce((p_updates ->> 'sms_enabled')::boolean, false),
                nullif(p_updates ->> 'telegram_chat_id', ''),
                coalesce((p_updates ->> 'telegram_enabled')::boolean, false),
                p_updated_by
            )
            ON CONFLICT (organization_id) DO UPDATE SET
                alert_email = CASE WHEN p_updates ? 'alert_email'
                    THEN nullif(p_updates ->> 'alert_email', '')
                    ELSE organization_notification_settings.alert_email END,
                sms_phone = CASE WHEN p_updates ? 'sms_phone'
                    THEN nullif(p_updates ->> 'sms_phone', '')
                    ELSE organization_notification_settings.sms_phone END,
                sms_enabled = CASE WHEN p_updates ? 'sms_enabled'
                    THEN coalesce((p_updates ->> 'sms_enabled')::boolean,
                        organization_notification_settings.sms_enabled)
                    ELSE organization_notification_settings.sms_enabled END,
                telegram_chat_id = CASE WHEN p_updates ? 'telegram_chat_id'
                    THEN nullif(p_updates ->> 'telegram_chat_id', '')
                    ELSE organization_notification_settings.telegram_chat_id END,
                telegram_enabled = CASE WHEN p_updates ? 'telegram_enabled'
                    THEN coalesce((p_updates ->> 'telegram_enabled')::boolean,
                        organization_notification_settings.telegram_enabled)
                    ELSE organization_notification_settings.telegram_enabled END,
                updated_by = p_updated_by,
                updated_at = now()
            RETURNING * INTO updated_row;

            RETURN to_jsonb(updated_row);
        END;
        $$;
        REVOKE ALL ON FUNCTION
            update_organization_notification_settings(uuid, uuid, jsonb)
            FROM PUBLIC, anon, authenticated;
        GRANT EXECUTE ON FUNCTION
            update_organization_notification_settings(uuid, uuid, jsonb)
            TO service_role;
        """
    )

    op.add_column(
        "oauth_attention_outbox",
        sa.Column(
            "organization_telegram_state",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "oauth_attention_outbox",
        sa.Column(
            "organization_sms_state",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "oauth_attention_outbox",
        sa.Column(
            "organization_telegram_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "oauth_attention_outbox",
        sa.Column(
            "organization_sms_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_oauth_attention_org_telegram_state",
        "oauth_attention_outbox",
        "organization_telegram_state IN ('pending', 'sent', 'skipped')",
    )
    op.create_check_constraint(
        "ck_oauth_attention_org_sms_state",
        "oauth_attention_outbox",
        "organization_sms_state IN ('pending', 'sent', 'skipped')",
    )
    op.create_check_constraint(
        "ck_oauth_attention_org_attempts_nonnegative",
        "oauth_attention_outbox",
        "organization_telegram_attempts >= 0 AND organization_sms_attempts >= 0",
    )

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
                   AND (
                       telegram_state = 'pending'
                       OR sms_state = 'pending'
                       OR organization_telegram_state = 'pending'
                       OR organization_sms_state = 'pending'
                   )
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
        """
    )

    op.execute(
        "DROP FUNCTION complete_oauth_attention_outbox("
        "uuid, text, text, text, boolean, boolean, text, int)"
    )
    op.execute(
        """
        CREATE FUNCTION complete_oauth_attention_outbox(
            p_id uuid,
            p_claim text,
            p_telegram_state text,
            p_sms_state text,
            p_organization_telegram_state text,
            p_organization_sms_state text,
            p_attempted_telegram boolean,
            p_attempted_sms boolean,
            p_attempted_organization_telegram boolean,
            p_attempted_organization_sms boolean,
            p_error_code text DEFAULT NULL,
            p_retry_seconds int DEFAULT 300
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            updated_id uuid;
        BEGIN
            IF p_telegram_state NOT IN ('pending', 'sent', 'skipped')
               OR p_sms_state NOT IN ('pending', 'sent', 'skipped')
               OR p_organization_telegram_state NOT IN ('pending', 'sent', 'skipped')
               OR p_organization_sms_state NOT IN ('pending', 'sent', 'skipped') THEN
                RAISE EXCEPTION 'invalid OAuth attention delivery state';
            END IF;
            UPDATE oauth_attention_outbox AS outbox
               SET telegram_state = CASE WHEN outbox.telegram_state = 'pending'
                   THEN p_telegram_state ELSE outbox.telegram_state END,
                   sms_state = CASE WHEN outbox.sms_state = 'pending'
                   THEN p_sms_state ELSE outbox.sms_state END,
                   organization_telegram_state = CASE
                       WHEN outbox.organization_telegram_state = 'pending'
                       THEN p_organization_telegram_state
                       ELSE outbox.organization_telegram_state END,
                   organization_sms_state = CASE
                       WHEN outbox.organization_sms_state = 'pending'
                       THEN p_organization_sms_state
                       ELSE outbox.organization_sms_state END,
                   telegram_attempts = outbox.telegram_attempts + CASE
                       WHEN p_attempted_telegram THEN 1 ELSE 0 END,
                   sms_attempts = outbox.sms_attempts + CASE
                       WHEN p_attempted_sms THEN 1 ELSE 0 END,
                   organization_telegram_attempts =
                       outbox.organization_telegram_attempts + CASE
                       WHEN p_attempted_organization_telegram THEN 1 ELSE 0 END,
                   organization_sms_attempts = outbox.organization_sms_attempts + CASE
                       WHEN p_attempted_organization_sms THEN 1 ELSE 0 END,
                   available_at = CASE
                       WHEN p_telegram_state = 'pending'
                         OR p_sms_state = 'pending'
                         OR p_organization_telegram_state = 'pending'
                         OR p_organization_sms_state = 'pending'
                       THEN now() + make_interval(secs => GREATEST(p_retry_seconds, 30))
                       ELSE outbox.available_at END,
                   last_error_code = p_error_code,
                   lease_claim = NULL,
                   lease_until = NULL,
                   delivered_at = CASE
                       WHEN (
                           CASE WHEN outbox.telegram_state = 'pending'
                               THEN p_telegram_state
                               ELSE outbox.telegram_state
                           END
                       ) <> 'pending'
                        AND (CASE WHEN outbox.sms_state = 'pending'
                           THEN p_sms_state ELSE outbox.sms_state END) <> 'pending'
                        AND (CASE WHEN outbox.organization_telegram_state = 'pending'
                           THEN p_organization_telegram_state
                           ELSE outbox.organization_telegram_state END) <> 'pending'
                        AND (CASE WHEN outbox.organization_sms_state = 'pending'
                           THEN p_organization_sms_state
                           ELSE outbox.organization_sms_state END) <> 'pending'
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
    """Restore the platform-only alert outbox and remove organization settings."""
    op.execute(
        "DROP FUNCTION complete_oauth_attention_outbox("
        "uuid, text, text, text, text, text, boolean, boolean, "
        "boolean, boolean, text, int)"
    )
    op.execute(
        "DROP FUNCTION update_organization_notification_settings(uuid, uuid, jsonb)"
    )
    op.drop_constraint(
        "ck_oauth_attention_org_attempts_nonnegative",
        "oauth_attention_outbox",
        type_="check",
    )
    op.drop_constraint(
        "ck_oauth_attention_org_sms_state", "oauth_attention_outbox", type_="check"
    )
    op.drop_constraint(
        "ck_oauth_attention_org_telegram_state",
        "oauth_attention_outbox",
        type_="check",
    )
    op.drop_column("oauth_attention_outbox", "organization_sms_attempts")
    op.drop_column("oauth_attention_outbox", "organization_telegram_attempts")
    op.drop_column("oauth_attention_outbox", "organization_sms_state")
    op.drop_column("oauth_attention_outbox", "organization_telegram_state")
    op.drop_table("organization_notification_settings")

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
                SELECT id FROM oauth_attention_outbox
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

        CREATE FUNCTION complete_oauth_attention_outbox(
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
                       WHEN (
                           CASE WHEN outbox.telegram_state = 'pending'
                               THEN p_telegram_state
                               ELSE outbox.telegram_state
                           END
                       ) <> 'pending'
                        AND (CASE WHEN outbox.sms_state = 'pending'
                           THEN p_sms_state ELSE outbox.sms_state END) <> 'pending'
                       THEN now() ELSE NULL END,
                   updated_at = now()
             WHERE outbox.id = p_id AND outbox.lease_claim = p_claim
            RETURNING outbox.id INTO updated_id;
            RETURN jsonb_build_object('updated', updated_id IS NOT NULL);
        END;
        $$;
        """
    )
