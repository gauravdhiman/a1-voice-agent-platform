"""Recover abandoned voice sessions without billing unknown crash-time usage."""

from alembic import op

revision = "20261019000004"
down_revision = "20261019000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Expire newly admitted calls whose worker stops renewing its lease."""
    op.execute("""
        ALTER TABLE public.call_logs ADD COLUMN voice_session_id text;
        ALTER TABLE public.call_logs ADD COLUMN voice_last_seen_at timestamptz;
        ALTER TABLE public.call_logs ADD COLUMN voice_lease_expires_at timestamptz;
        CREATE INDEX ix_call_logs_expiring_voice ON
            public.call_logs(voice_lease_expires_at)
            WHERE status IN ('initiated','ringing','answered') AND voice_session_id
                IS NOT NULL;
        CREATE FUNCTION public.initialize_voice_lease() RETURNS trigger
        LANGUAGE plpgsql SET search_path=public,pg_temp AS $lease$
        BEGIN
            IF NEW.voice_session_id IS NOT NULL AND
                (TG_OP='INSERT' OR OLD.voice_session_id IS NULL) THEN
                NEW.voice_last_seen_at=clock_timestamp();
                NEW.voice_lease_expires_at=clock_timestamp()+interval '90 seconds';
            END IF;
            RETURN NEW;
        END $lease$;
        CREATE TRIGGER initialize_voice_lease BEFORE INSERT OR UPDATE OF
            voice_session_id
            ON public.call_logs FOR EACH ROW EXECUTE FUNCTION
                public.initialize_voice_lease();
        CREATE FUNCTION public.touch_voice_call(p_call_log_id uuid,p_session_id text)
        RETURNS boolean LANGUAGE plpgsql SET search_path=public,pg_temp AS $touch$
        BEGIN
            UPDATE public.call_logs SET voice_last_seen_at=clock_timestamp(),
                voice_lease_expires_at=clock_timestamp()+interval '90 seconds'
                WHERE id=p_call_log_id AND voice_session_id=p_session_id
                  AND voice_lease_expires_at>clock_timestamp()
                  AND status IN ('initiated','ringing','answered');
            RETURN FOUND;
        END $touch$;
        CREATE FUNCTION public.reconcile_expired_voice_calls(p_organization_id uuid
            DEFAULT NULL)
        RETURNS integer LANGUAGE plpgsql SET search_path=public,pg_temp AS $recover$
        DECLARE v_count integer;
        BEGIN
            WITH expired AS (
                SELECT id FROM public.call_logs
                WHERE voice_session_id IS NOT NULL
                  AND status IN ('initiated','ringing','answered')
                  AND voice_lease_expires_at<clock_timestamp()
                  AND (p_organization_id IS NULL OR organization_id=p_organization_id)
                ORDER BY voice_lease_expires_at FOR UPDATE SKIP LOCKED LIMIT 100
            )
            UPDATE public.call_logs c SET status='failed',
                ended_at=greatest(c.started_at,c.voice_last_seen_at),
                duration=greatest(0,extract(epoch FROM
                    c.voice_last_seen_at-c.started_at)::integer),
                failure_code='voice_worker_interrupted',
                failure_message='The voice worker stopped renewing this session.',
                updated_at=clock_timestamp()
            FROM expired WHERE c.id=expired.id;
            GET DIAGNOSTICS v_count=ROW_COUNT;
            RETURN v_count;
        END $recover$;
        REVOKE ALL ON FUNCTION public.initialize_voice_lease() FROM
            PUBLIC,anon,authenticated;
        REVOKE ALL ON FUNCTION public.touch_voice_call(uuid,text) FROM
            PUBLIC,anon,authenticated;
        REVOKE ALL ON FUNCTION public.reconcile_expired_voice_calls(uuid) FROM
            PUBLIC,anon,authenticated;
        GRANT EXECUTE ON FUNCTION public.initialize_voice_lease() TO service_role;
        GRANT EXECUTE ON FUNCTION public.touch_voice_call(uuid,text) TO service_role;
        GRANT EXECUTE ON FUNCTION public.reconcile_expired_voice_calls(uuid) TO
            service_role;
    """)


def downgrade() -> None:
    """Preserve recovery state on integrated releases."""
    raise RuntimeError("Voice session leases require a reviewed forward repair")
