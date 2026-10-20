"""Run the real security migration against an explicitly selected disposable DB.

Use DATA_API_TEST_DATABASE_URL pointing to loopback, migrated to the preceding
revision. Every test rolls back changes, grants, functions, and fixtures.
"""

import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg2
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def security_db(monkeypatch):
    """Apply the actual migration inside a rollback-only local transaction."""
    url = os.getenv("DATA_API_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DATA_API_TEST_DATABASE_URL must select a disposable local DB")
    if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Security mutation tests refuse remote databases")
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/20261019000001_lock_down_data_api.py"
    )
    spec = importlib.util.spec_from_file_location("data_api_lockdown", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    connection = psycopg2.connect(url, connect_timeout=5)
    try:
        with connection.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='10s'")
            # Reproduce Supabase's inherited global and schema-level defaults.
            cur.execute(
                "ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES TO anon, authenticated"
            )
            cur.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS"
                " TO anon, authenticated"
            )
            monkeypatch.setattr(module.op, "execute", cur.execute)
            module.upgrade()
            yield cur
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_private_tables_and_mutating_rpcs_deny_client_roles(security_db, role):
    """RLS and ACLs protect every private table, not just the API paths."""
    cur = security_db
    cur.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity"
    )
    assert cur.fetchall() == []
    cur.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace"
        " WHERE n.nspname='public' AND c.relkind='r' AND c.relname <>"
        " 'agent_change_events' AND has_table_privilege(%s,c.oid,'SELECT')",
        (role,),
    )
    assert cur.fetchall() == []
    for privilege in ["INSERT", "UPDATE", "DELETE", "TRUNCATE"]:
        cur.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON"
            " n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND"
            " has_table_privilege(%s,c.oid,%s)",
            (role, privilege),
        )
        assert cur.fetchall() == []
    cur.execute(
        "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='public' AND p.prosecdef "
        "AND p.proname <> 'can_read_agent_change' "
        "AND has_function_privilege(%s,p.oid,'EXECUTE')",
        (role,),
    )
    assert cur.fetchall() == []


def test_future_object_defaults_do_not_reopen_access(security_db):
    """Global PUBLIC defaults cannot override a schema-only revoke."""
    cur = security_db
    cur.execute("CREATE TABLE public.future_private_row(id int)")
    cur.execute(
        "CREATE FUNCTION public.future_mutation() RETURNS int LANGUAGE sql AS"
        " 'SELECT 1'"
    )
    for role in ["anon", "authenticated"]:
        cur.execute(
            "SELECT has_table_privilege(%s,'public.future_private_row','SELECT'), "
            "has_function_privilege(%s,'public.future_mutation()','EXECUTE')",
            (role, role),
        )
        assert cur.fetchone() == (False, False)


def test_invalidation_rows_are_scoped_and_cannot_be_written_by_clients(security_db):
    """Tenants see their IDs; platform admins see both; missing claims see none."""
    cur = security_db
    org_a, org_b, user_a, user_b, admin, agent_a, agent_b = [
        str(uuid4()) for _ in range(7)
    ]
    for org in [org_a, org_b]:
        cur.execute(
            "INSERT INTO organizations(id,name,slug) VALUES (%s,'Security fixture',%s)",
            (org, org),
        )
    for user in [user_a, user_b, admin]:
        cur.execute(
            "INSERT INTO auth.users(id,email) VALUES (%s,%s)",
            (user, user + "@example.test"),
        )
    for user, org, role in [
        (user_a, org_a, "regular_user"),
        (user_b, org_b, "org_admin"),
        (admin, None, "platform_admin"),
    ]:
        cur.execute(
            "INSERT INTO user_roles(user_id,organization_id,role_id) SELECT %s,%s,id"
            " FROM roles WHERE name=%s",
            (user, org, role),
        )
    for agent, org in [(agent_a, org_a), (agent_b, org_b)]:
        cur.execute(
            "INSERT INTO agent_change_events(agent_id,organization_id) VALUES (%s,%s)",
            (agent, org),
        )
    cur.execute("SET LOCAL ROLE authenticated")
    for user, expected in [
        (user_a, [agent_a]),
        (user_b, [agent_b]),
        (admin, sorted([agent_a, agent_b])),
        ("", []),
    ]:
        cur.execute("SELECT set_config('request.jwt.claim.sub',%s,true)", (user,))
        cur.execute(
            "SELECT agent_id::text FROM agent_change_events ORDER BY agent_id::text"
        )
        assert [r[0] for r in cur.fetchall()] == expected
    cur.execute("RESET ROLE")
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='public'"
        " AND table_name='agent_change_events' ORDER BY ordinal_position"
    )
    assert [r[0] for r in cur.fetchall()] == [
        "agent_id",
        "organization_id",
        "revision",
        "changed_at",
    ]


def test_realtime_publication_excludes_private_tables(security_db):
    """The publication cannot stream prompts or encrypted tool credentials."""
    security_db.execute(
        "SELECT tablename FROM pg_publication_tables WHERE pubname='supabase_realtime'"
        " AND schemaname='public'"
    )
    assert [r[0] for r in security_db.fetchall()] == ["agent_change_events"]


def test_release_guard_detects_regressions(security_db):
    """The postcondition gate fails on a reopened private grant or missing RLS."""
    path = Path(__file__).parents[3] / "scripts/deploy/verify_data_api_security.py"
    spec = importlib.util.spec_from_file_location("data_api_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not any(module.security_violations(security_db).values())
    security_db.execute("GRANT SELECT ON public.call_logs TO anon")
    security_db.execute("ALTER TABLE public.call_logs DISABLE ROW LEVEL SECURITY")
    counts = module.security_violations(security_db)
    assert counts["unsafe_client_table_grants"] == 1
    assert counts["tables_without_rls"] == 1
