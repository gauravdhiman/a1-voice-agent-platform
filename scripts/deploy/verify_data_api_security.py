#!/usr/bin/env python3
"""Read-only Data API release gate. Report counts, never customer rows or DSNs."""

import os
from argparse import ArgumentParser

import psycopg2
from dotenv import dotenv_values


def security_violations(cursor) -> dict[str, int]:
    """Count unsafe ACLs, RLS, RPCs and publications on the current database."""
    counts = {}
    cursor.execute("""SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p') AND NOT c.relrowsecurity""")
    counts["tables_without_rls"] = cursor.fetchone()[0]
    cursor.execute("""SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN (VALUES ('anon'),('authenticated')) AS roles(name)
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
        AND (has_table_privilege(roles.name,c.oid,
                'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          OR (has_table_privilege(roles.name,c.oid,'SELECT')
              AND NOT (c.relname='agent_change_events'
                  AND roles.name='authenticated')))""")
    counts["unsafe_client_table_grants"] = cursor.fetchone()[0]
    cursor.execute("""SELECT count(*) FROM pg_proc p
        JOIN pg_namespace n ON n.oid=p.pronamespace
        CROSS JOIN (VALUES ('anon'),('authenticated')) AS roles(name)
        WHERE n.nspname='public' AND p.prosecdef
        AND has_function_privilege(roles.name,p.oid,'EXECUTE')
        AND NOT (p.proname='can_read_agent_change' AND roles.name='authenticated'
                 AND pg_get_function_identity_arguments(p.oid)=
                     'p_organization_id uuid')""")
    counts["unsafe_definer_rpc_grants"] = cursor.fetchone()[0]
    cursor.execute("""SELECT count(*) FROM pg_publication_tables
        WHERE pubname='supabase_realtime' AND schemaname='public'
        AND tablename IN ('voice_agents','agent_tools')""")
    counts["private_agent_publications"] = cursor.fetchone()[0]
    cursor.execute("""SELECT count(*) FROM pg_policies WHERE schemaname='public'
        AND tablename='agent_change_events' AND policyname='agent_change_tenant_read'
        AND cmd='SELECT' AND qual='can_read_agent_change(organization_id)'""")
    counts["missing_tenant_invalidation_policy"] = int(cursor.fetchone()[0] != 1)
    return counts


def main() -> int:
    """Check committed security postconditions in a read-only transaction."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.prod")
    args = parser.parse_args()
    url = dotenv_values(args.env_file).get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL is required")
    try:
        with psycopg2.connect(url, connect_timeout=10) as connection:
            connection.set_session(readonly=True)
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='15s'")
                counts = security_violations(cursor)
    except Exception as exc:
        print(
            f"Data API security verification could not finish ({type(exc).__name__})."
        )
        return 1
    print(
        "Data API security violations: "
        + ", ".join(f"{key}={count}" for key, count in counts.items())
    )
    return int(any(counts.values()))


if __name__ == "__main__":
    raise SystemExit(main())
