"""Persist and retry platform-admin contact lead alerts.

Revision ID: 20261001000004
Revises: 20261001000003
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261001000004"
down_revision: Union[str, Sequence[str], None] = "20261001000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create one retryable delivery record for every persisted interest lead."""
    op.drop_constraint(
        "ck_interest_leads_source", "interest_leads", type_="check"
    )
    op.create_check_constraint(
        "ck_interest_leads_source",
        "interest_leads",
        "source IN ('request-demo', 'contact-us', 'outcome-form', 'demo-call', 'manual')",
    )
    op.execute(
        """
        CREATE TABLE interest_lead_notification_outbox (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            lead_id uuid NOT NULL UNIQUE
                REFERENCES interest_leads(id) ON DELETE CASCADE,
            email_state text NOT NULL DEFAULT 'pending'
                CHECK (email_state IN ('pending', 'sent', 'skipped')),
            telegram_state text NOT NULL DEFAULT 'pending'
                CHECK (telegram_state IN ('pending', 'sent', 'skipped')),
            whatsapp_state text NOT NULL DEFAULT 'pending'
                CHECK (whatsapp_state IN ('pending', 'sent', 'skipped')),
            email_attempts integer NOT NULL DEFAULT 0 CHECK (email_attempts >= 0),
            telegram_attempts integer NOT NULL DEFAULT 0 CHECK (telegram_attempts >= 0),
            whatsapp_attempts integer NOT NULL DEFAULT 0 CHECK (whatsapp_attempts >= 0),
            available_at timestamptz NOT NULL DEFAULT now(),
            lease_claim text,
            lease_until timestamptz,
            last_error_code text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            delivered_at timestamptz
        );

        CREATE INDEX ix_interest_lead_notification_outbox_due
            ON interest_lead_notification_outbox (available_at, created_at)
            WHERE delivered_at IS NULL;

        ALTER TABLE interest_lead_notification_outbox ENABLE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE interest_lead_notification_outbox
            FROM PUBLIC, anon, authenticated;
        GRANT ALL ON TABLE interest_lead_notification_outbox TO service_role;

        CREATE FUNCTION enqueue_interest_lead_notification()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO interest_lead_notification_outbox (lead_id)
            VALUES (NEW.id)
            ON CONFLICT (lead_id) DO NOTHING;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER interest_lead_notification_outbox_after_insert
        AFTER INSERT ON interest_leads
        FOR EACH ROW EXECUTE FUNCTION enqueue_interest_lead_notification();

        REVOKE ALL ON FUNCTION enqueue_interest_lead_notification() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION enqueue_interest_lead_notification() TO service_role;

        CREATE FUNCTION claim_interest_lead_notification_outbox(
            p_claim text,
            p_lead_id uuid DEFAULT NULL,
            p_limit int DEFAULT 50,
            p_lease_seconds int DEFAULT 60
        ) RETURNS SETOF interest_lead_notification_outbox
        LANGUAGE sql
        AS $$
            WITH due AS (
                SELECT id
                  FROM interest_lead_notification_outbox
                 WHERE delivered_at IS NULL
                   AND available_at <= now()
                   AND (lease_until IS NULL OR lease_until < now())
                   AND (email_state = 'pending'
                        OR telegram_state = 'pending'
                        OR whatsapp_state = 'pending')
                   AND (p_lead_id IS NULL OR lead_id = p_lead_id)
                 ORDER BY available_at, created_at
                 FOR UPDATE SKIP LOCKED
                 LIMIT LEAST(GREATEST(p_limit, 1), 100)
            )
            UPDATE interest_lead_notification_outbox AS outbox
               SET lease_claim = p_claim,
                   lease_until = now() + make_interval(secs => p_lease_seconds),
                   updated_at = now()
              FROM due
             WHERE outbox.id = due.id
            RETURNING outbox.*;
        $$;

        CREATE FUNCTION complete_interest_lead_notification_outbox(
            p_id uuid,
            p_claim text,
            p_email_state text,
            p_telegram_state text,
            p_whatsapp_state text,
            p_attempted_email boolean,
            p_attempted_telegram boolean,
            p_attempted_whatsapp boolean,
            p_error_code text DEFAULT NULL,
            p_retry_seconds int DEFAULT 300
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            updated_id uuid;
        BEGIN
            IF p_email_state NOT IN ('pending', 'sent', 'skipped')
               OR p_telegram_state NOT IN ('pending', 'sent', 'skipped')
               OR p_whatsapp_state NOT IN ('pending', 'sent', 'skipped') THEN
                RAISE EXCEPTION 'invalid interest lead notification state';
            END IF;

            UPDATE interest_lead_notification_outbox AS outbox
               SET email_state = CASE WHEN outbox.email_state = 'pending'
                   THEN p_email_state ELSE outbox.email_state END,
                   telegram_state = CASE WHEN outbox.telegram_state = 'pending'
                   THEN p_telegram_state ELSE outbox.telegram_state END,
                   whatsapp_state = CASE WHEN outbox.whatsapp_state = 'pending'
                   THEN p_whatsapp_state ELSE outbox.whatsapp_state END,
                   email_attempts = outbox.email_attempts + CASE
                       WHEN p_attempted_email THEN 1 ELSE 0 END,
                   telegram_attempts = outbox.telegram_attempts + CASE
                       WHEN p_attempted_telegram THEN 1 ELSE 0 END,
                   whatsapp_attempts = outbox.whatsapp_attempts + CASE
                       WHEN p_attempted_whatsapp THEN 1 ELSE 0 END,
                   available_at = CASE
                       WHEN p_email_state = 'pending'
                         OR p_telegram_state = 'pending'
                         OR p_whatsapp_state = 'pending'
                       THEN now() + make_interval(secs => GREATEST(p_retry_seconds, 30))
                       ELSE outbox.available_at END,
                   last_error_code = p_error_code,
                   lease_claim = NULL,
                   lease_until = NULL,
                   updated_at = now(),
                   delivered_at = CASE
                       WHEN (CASE WHEN outbox.email_state = 'pending'
                                  THEN p_email_state ELSE outbox.email_state END) <> 'pending'
                        AND (CASE WHEN outbox.telegram_state = 'pending'
                                  THEN p_telegram_state ELSE outbox.telegram_state END) <> 'pending'
                        AND (CASE WHEN outbox.whatsapp_state = 'pending'
                                  THEN p_whatsapp_state ELSE outbox.whatsapp_state END) <> 'pending'
                       THEN COALESCE(outbox.delivered_at, now())
                       ELSE NULL END
             WHERE outbox.id = p_id AND outbox.lease_claim = p_claim
            RETURNING outbox.id INTO updated_id;

            RETURN jsonb_build_object('updated', updated_id IS NOT NULL);
        END;
        $$;

        REVOKE ALL ON FUNCTION claim_interest_lead_notification_outbox(
            text, uuid, int, int
        ) FROM PUBLIC;
        REVOKE ALL ON FUNCTION complete_interest_lead_notification_outbox(
            uuid, text, text, text, text, boolean, boolean, boolean, text, int
        ) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION claim_interest_lead_notification_outbox(
            text, uuid, int, int
        ) TO service_role;
        GRANT EXECUTE ON FUNCTION complete_interest_lead_notification_outbox(
            uuid, text, text, text, text, boolean, boolean, boolean, text, int
        ) TO service_role;
        """
    )


def downgrade() -> None:
    """Remove the retry queue and its automatic enqueue trigger."""
    op.execute(
        """
        DROP FUNCTION complete_interest_lead_notification_outbox(
            uuid, text, text, text, text, boolean, boolean, boolean, text, int
        );
        DROP FUNCTION claim_interest_lead_notification_outbox(text, uuid, int, int);
        DROP TRIGGER interest_lead_notification_outbox_after_insert ON interest_leads;
        DROP FUNCTION enqueue_interest_lead_notification();
        DROP INDEX ix_interest_lead_notification_outbox_due;
        DROP TABLE interest_lead_notification_outbox;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM interest_leads WHERE source = 'contact-us') THEN
                RAISE EXCEPTION 'Cannot remove contact-us source while contact leads exist';
            END IF;
        END;
        $$;
        """
    )
    op.drop_constraint(
        "ck_interest_leads_source", "interest_leads", type_="check"
    )
    op.create_check_constraint(
        "ck_interest_leads_source",
        "interest_leads",
        "source IN ('request-demo', 'outcome-form', 'demo-call', 'manual')",
    )
