"""Serialize voice admission and reject session-token replay."""

from alembic import op

revision = "20261019000005"
down_revision = "20261019000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Claim a tracked slot under the organization lock before provider startup."""
    op.execute("""
        CREATE UNIQUE INDEX ux_call_logs_voice_session ON
            public.call_logs(voice_session_id)
            WHERE voice_session_id IS NOT NULL;
        CREATE FUNCTION public.admit_voice_call(
            p_session_id text, p_call_sid text, p_organization_id uuid,
            p_agent_id uuid, p_concurrent_limit integer,
            p_source_type text, p_source_url text, p_source_domain text
        ) RETURNS jsonb LANGUAGE plpgsql SET search_path=public,pg_temp AS $admit$
        DECLARE v_demo boolean; v_id uuid; v_active integer; v_existing
            public.call_logs%ROWTYPE;
        BEGIN
            IF p_session_id IS NULL OR length(p_session_id) NOT BETWEEN 1 AND 200 THEN
                RETURN jsonb_build_object('success',false,'code','INVALID_SESSION');
            END IF;
            PERFORM 1 FROM public.organizations WHERE id=p_organization_id FOR UPDATE;
            IF NOT FOUND THEN RETURN
                jsonb_build_object('success',false,'code','ORGANIZATION_NOT_FOUND');
                END IF;
            SELECT is_demo INTO v_demo FROM public.voice_agents
                WHERE id=p_agent_id AND organization_id=p_organization_id;
            IF NOT FOUND THEN RETURN
                jsonb_build_object('success',false,'code','AGENT_NOT_FOUND'); END IF;
            IF EXISTS (SELECT 1 FROM public.call_logs WHERE
                voice_session_id=p_session_id) THEN
                RETURN
                    jsonb_build_object('success',false,'code','SESSION_ALREADY_USED');
            END IF;
            SELECT * INTO v_existing FROM public.call_logs
                WHERE call_sid=coalesce(p_call_sid,p_session_id) FOR UPDATE;
            IF FOUND AND (v_existing.organization_id<>p_organization_id
                OR v_existing.agent_id IS DISTINCT FROM p_agent_id
                OR v_existing.voice_session_id IS NOT NULL
                OR v_existing.status NOT IN ('initiated','ringing','answered')) THEN
                RETURN
                    jsonb_build_object('success',false,'code','SESSION_ALREADY_USED');
            END IF;
            PERFORM public.reconcile_expired_voice_calls(p_organization_id);
            SELECT count(*) INTO v_active FROM public.call_logs
                WHERE organization_id=p_organization_id
                  AND status IN ('initiated','ringing','answered')
                  AND id IS DISTINCT FROM v_existing.id;
            IF NOT coalesce(v_demo,false) AND p_concurrent_limit IS NOT NULL
                AND v_active>=p_concurrent_limit THEN
                RETURN
                    jsonb_build_object('success',false,'code','MAX_CONCURRENT_CALLS');
            END IF;
            IF v_existing.id IS NOT NULL THEN
                UPDATE public.call_logs SET voice_session_id=p_session_id,
                    billing_status='pending',started_at=now(),updated_at=now(),
                    source_type=coalesce(p_source_type,source_type),
                    source_url=coalesce(p_source_url,source_url),
                    source_domain=coalesce(p_source_domain,source_domain)
                    WHERE id=v_existing.id RETURNING id INTO v_id;
            ELSE
                INSERT INTO public.call_logs(call_sid,organization_id,agent_id,status,
                    voice_session_id,billing_status,started_at,source_type,source_url,source_domain)
                VALUES(coalesce(p_call_sid,p_session_id),p_organization_id,p_agent_id,'initiated',
                    p_session_id,'pending',now(),p_source_type,p_source_url,p_source_domain)
                RETURNING id INTO v_id;
            END IF;
            RETURN jsonb_build_object('success',true,'call_log_id',v_id);
        END $admit$;
        REVOKE ALL ON FUNCTION
            public.admit_voice_call(text,text,uuid,uuid,integer,text,text,text)
            FROM PUBLIC,anon,authenticated;
        GRANT EXECUTE ON FUNCTION
            public.admit_voice_call(text,text,uuid,uuid,integer,text,text,text)
            TO service_role;
    """)


def downgrade() -> None:
    """Never remove replay protection from an integrated release."""
    raise RuntimeError("Voice admission requires a reviewed forward repair")
