"""Close direct Data API access; publish only tenant-scoped invalidation IDs."""

from alembic import op

revision = "20261019000001"
down_revision = "20261012000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove inherited client grants and replace credential-bearing feeds."""
    op.execute("""
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, anon, authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, anon, authenticated;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC, anon, authenticated;
        GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
        -- Schema defaults add to global defaults; both must be revoked.
        ALTER DEFAULT PRIVILEGES
            REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
        ALTER DEFAULT PRIVILEGES
            REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
        ALTER DEFAULT PRIVILEGES
            REVOKE ALL ON FUNCTIONS FROM PUBLIC, anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON FUNCTIONS FROM PUBLIC, anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT USAGE, SELECT ON SEQUENCES TO service_role;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT EXECUTE ON FUNCTIONS TO service_role;

        DO $lockdown$
        DECLARE target record;
        BEGIN
            FOR target IN SELECT c.relname FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
            LOOP
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',
                               target.relname);
            END LOOP;
        END $lockdown$;
        DROP POLICY IF EXISTS
            "Allow authenticated users to subscribe to agent_tools changes"
            ON public.agent_tools;
        DROP POLICY IF EXISTS
            "Allow authenticated users to subscribe to voice_agents changes"
            ON public.voice_agents;

        CREATE TABLE public.agent_change_events (
            agent_id uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES public.organizations(id)
                ON DELETE CASCADE,
            revision bigint NOT NULL DEFAULT 1,
            changed_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_agent_change_events_organization
            ON public.agent_change_events(organization_id);
        ALTER TABLE public.agent_change_events ENABLE ROW LEVEL SECURITY;
        REVOKE ALL ON public.agent_change_events FROM PUBLIC, anon, authenticated;
        GRANT ALL ON public.agent_change_events TO service_role;
        GRANT SELECT ON public.agent_change_events TO authenticated;
        CREATE FUNCTION public.can_read_agent_change(p_organization_id uuid)
        RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = '' AS $access$
            SELECT EXISTS (
                SELECT 1 FROM public.user_roles ur
                JOIN public.roles r ON r.id = ur.role_id
                WHERE ur.user_id = auth.uid()
                  AND (ur.organization_id = p_organization_id
                       OR r.name = 'platform_admin')
            );
        $access$;
        REVOKE ALL ON FUNCTION public.can_read_agent_change(uuid)
            FROM PUBLIC, anon, authenticated;
        GRANT EXECUTE ON FUNCTION public.can_read_agent_change(uuid)
            TO authenticated, service_role;
        CREATE POLICY agent_change_tenant_read ON public.agent_change_events
            FOR SELECT TO authenticated
            USING (public.can_read_agent_change(organization_id));

        CREATE FUNCTION public.publish_agent_change()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
        AS $publish$
        DECLARE agent uuid; organization uuid;
        BEGIN
            IF TG_TABLE_NAME = 'voice_agents' THEN
                IF TG_OP = 'DELETE' THEN
                    agent := OLD.id; organization := OLD.organization_id;
                ELSE
                    agent := NEW.id; organization := NEW.organization_id;
                END IF;
            ELSE
                IF TG_OP = 'DELETE' THEN agent := OLD.agent_id;
                ELSE agent := NEW.agent_id; END IF;
                SELECT a.organization_id INTO organization
                    FROM public.voice_agents a WHERE a.id = agent;
            END IF;
            IF organization IS NOT NULL AND EXISTS (
                SELECT 1 FROM public.organizations o WHERE o.id = organization
            ) THEN
                INSERT INTO public.agent_change_events (agent_id, organization_id)
                VALUES (agent, organization)
                ON CONFLICT (agent_id) DO UPDATE
                    SET organization_id = EXCLUDED.organization_id,
                        revision = public.agent_change_events.revision + 1,
                        changed_at = clock_timestamp();
            END IF;
            RETURN NULL;
        END $publish$;
        REVOKE ALL ON FUNCTION public.publish_agent_change()
            FROM PUBLIC, anon, authenticated;
        GRANT EXECUTE ON FUNCTION public.publish_agent_change() TO service_role;
        CREATE TRIGGER voice_agent_change_notification
            AFTER INSERT OR UPDATE OR DELETE ON public.voice_agents
            FOR EACH ROW EXECUTE FUNCTION public.publish_agent_change();
        CREATE TRIGGER agent_tool_change_notification
            AFTER INSERT OR UPDATE OR DELETE ON public.agent_tools
            FOR EACH ROW EXECUTE FUNCTION public.publish_agent_change();

        DO $realtime$
        DECLARE target text;
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_publication
                       WHERE pubname = 'supabase_realtime') THEN
                FOREACH target IN ARRAY ARRAY['voice_agents', 'agent_tools'] LOOP
                    IF EXISTS (SELECT 1 FROM pg_publication_tables
                               WHERE pubname = 'supabase_realtime'
                                 AND schemaname = 'public' AND tablename = target) THEN
                        EXECUTE format('ALTER PUBLICATION supabase_realtime '
                                       'DROP TABLE public.%I', target);
                    END IF;
                END LOOP;
                ALTER PUBLICATION supabase_realtime ADD TABLE
                    public.agent_change_events;
            END IF;
        END $realtime$;
        """)


def downgrade() -> None:
    """Never restore anonymous writes or credential-bearing feeds."""
    raise RuntimeError("Data API lockdown requires a reviewed forward repair")
