"""Make organization notification channels destination-driven.

Revision ID: 20260925000001
Revises: 20260924000002
Create Date: 2026-09-25 00:00:01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260925000001"
down_revision: Union[str, None] = "20260924000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store org-owned Telegram credentials and derive channel opt-in from fields."""
    op.add_column(
        "organization_notification_settings",
        sa.Column("telegram_bot_token_encrypted", sa.Text(), nullable=True),
    )

    # The old independent switches could be off while a destination remained
    # saved. Clear those values before dropping the switches so the new
    # destination-driven behavior never opts a previously disabled channel in.
    op.execute(
        """
        UPDATE organization_notification_settings
           SET sms_phone = CASE WHEN sms_enabled THEN sms_phone ELSE NULL END,
               telegram_chat_id = CASE
                   WHEN telegram_enabled THEN telegram_chat_id ELSE NULL END
        """
    )
    op.drop_constraint(
        "ck_org_notification_sms_enabled_has_phone",
        "organization_notification_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_org_notification_telegram_enabled_has_chat_id",
        "organization_notification_settings",
        type_="check",
    )
    op.drop_column("organization_notification_settings", "sms_enabled")
    op.drop_column("organization_notification_settings", "telegram_enabled")

    op.execute(
        "DROP FUNCTION update_organization_notification_settings(uuid, uuid, jsonb)"
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
                telegram_chat_id,
                telegram_bot_token_encrypted,
                updated_by
            ) VALUES (
                p_organization_id,
                nullif(p_updates ->> 'alert_email', ''),
                nullif(p_updates ->> 'sms_phone', ''),
                nullif(p_updates ->> 'telegram_chat_id', ''),
                nullif(p_updates ->> 'telegram_bot_token_encrypted', ''),
                p_updated_by
            )
            ON CONFLICT (organization_id) DO UPDATE SET
                alert_email = CASE WHEN p_updates ? 'alert_email'
                    THEN nullif(p_updates ->> 'alert_email', '')
                    ELSE organization_notification_settings.alert_email END,
                sms_phone = CASE WHEN p_updates ? 'sms_phone'
                    THEN nullif(p_updates ->> 'sms_phone', '')
                    ELSE organization_notification_settings.sms_phone END,
                telegram_chat_id = CASE WHEN p_updates ? 'telegram_chat_id'
                    THEN nullif(p_updates ->> 'telegram_chat_id', '')
                    ELSE organization_notification_settings.telegram_chat_id END,
                telegram_bot_token_encrypted = CASE
                    WHEN p_updates ? 'telegram_bot_token_encrypted'
                    THEN nullif(p_updates ->> 'telegram_bot_token_encrypted', '')
                    ELSE organization_notification_settings.telegram_bot_token_encrypted
                END,
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


def downgrade() -> None:
    """Restore legacy switches only when no organization bot token would be lost."""
    connection = op.get_bind()
    configured_tokens = connection.execute(
        sa.text(
            "SELECT count(*) FROM organization_notification_settings "
            "WHERE telegram_bot_token_encrypted IS NOT NULL "
            "OR telegram_chat_id IS NOT NULL"
        )
    ).scalar_one()
    if configured_tokens:
        raise RuntimeError(
            "Cannot downgrade organization notification settings while an "
            "organization Telegram destination or bot token is configured. "
            "Clear those values first; the legacy schema cannot safely restore "
            "the previous Telegram channel state."
        )

    op.execute(
        "DROP FUNCTION update_organization_notification_settings(uuid, uuid, jsonb)"
    )
    op.add_column(
        "organization_notification_settings",
        sa.Column(
            "sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "organization_notification_settings",
        sa.Column(
            "telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.execute(
        "UPDATE organization_notification_settings "
        "SET sms_enabled = sms_phone IS NOT NULL, telegram_enabled = false"
    )
    op.create_check_constraint(
        "ck_org_notification_sms_enabled_has_phone",
        "organization_notification_settings",
        "NOT sms_enabled OR sms_phone IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_org_notification_telegram_enabled_has_chat_id",
        "organization_notification_settings",
        "NOT telegram_enabled OR telegram_chat_id IS NOT NULL",
    )
    op.drop_column("organization_notification_settings", "telegram_bot_token_encrypted")

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
                organization_id, alert_email, sms_phone, sms_enabled,
                telegram_chat_id, telegram_enabled, updated_by
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
