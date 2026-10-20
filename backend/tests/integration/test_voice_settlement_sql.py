"""Real transaction and concurrent-retry tests on a disposable loopback DB."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg2
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def settlement_db():
    """Create synthetic tenant data only after the new migration is installed."""
    url = os.getenv("SETTLEMENT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("SETTLEMENT_TEST_DATABASE_URL must select a disposable DB at head")
    if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Financial mutation tests refuse remote databases")
    conn = psycopg2.connect(url, connect_timeout=5)
    org, agent, call = [str(uuid4()) for _ in range(3)]
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizations(id,name,slug,credit_balance) VALUES"
                " (%s,'Settlement fixture',%s,100)",
                (org, org),
            )
            cur.execute(
                "INSERT INTO voice_agents(id,organization_id,name) VALUES"
                " (%s,%s,'Fixture')",
                (agent, org),
            )
            now = datetime.now(timezone.utc)
            cur.execute(
                """INSERT INTO call_logs(id,call_sid,organization_id,agent_id,
                status,duration,started_at,ended_at,billing_status)
                VALUES (%s,%s,%s,%s,'completed',61,%s,%s,'pending')""",
                (call, call, org, agent, now - timedelta(seconds=61), now),
            )
        conn.commit()
        yield conn, url, org, agent, call
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM organizations WHERE id=%s", (org,))
        conn.commit()
        conn.close()


def _settle(url, call):
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='10s'")
            cur.execute("SET LOCAL ROLE service_role")
            cur.execute("SELECT settle_voice_call(%s)", (call,))
            return cur.fetchone()[0]


def test_parallel_settlement_has_one_ledger_row_and_one_charge(settlement_db):
    conn, url, org, _, call = settlement_db
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _settle(url, call), range(2)))
    assert all(result["success"] for result in results)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*),sum(-amount) FROM credit_transactions WHERE"
            " metadata->>'call_log_id'=%s",
            (call,),
        )
        assert cur.fetchone() == (1, 20)
        cur.execute("SELECT credit_balance FROM organizations WHERE id=%s", (org,))
        assert cur.fetchone()[0] == 80
        cur.execute(
            "SELECT billing_status,credits_consumed,credit_transaction_id IS NOT NULL"
            " FROM call_logs WHERE id=%s",
            (call,),
        )
        assert cur.fetchone() == ("settled", 20, True)


@pytest.mark.parametrize("demo,rate", [(True, 10), (False, 0)])
def test_demo_and_zero_rate_calls_are_settled_without_debit(settlement_db, demo, rate):
    conn, _, org, agent, call = settlement_db
    with conn.cursor() as cur:
        cur.execute("UPDATE voice_agents SET is_demo=%s WHERE id=%s", (demo, agent))
        cur.execute(
            "UPDATE credit_events SET credit_cost=%s WHERE name='voice_call_minute'",
            (rate,),
        )
        cur.execute("SELECT settle_voice_call(%s)", (call,))
        assert cur.fetchone()[0]["success"] is True
        cur.execute(
            "SELECT billing_status,credits_consumed,credit_transaction_id FROM"
            " call_logs WHERE id=%s",
            (call,),
        )
        assert cur.fetchone() == ("settled", 0, None)
        cur.execute("SELECT credit_balance FROM organizations WHERE id=%s", (org,))
        assert cur.fetchone()[0] == 100


def test_unavailable_rate_keeps_work_pending_then_retries(settlement_db):
    conn, _, _, _, call = settlement_db
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE credit_events SET is_active=false WHERE name='voice_call_minute'"
        )
        cur.execute("SELECT settle_voice_call(%s)", (call,))
        assert cur.fetchone()[0]["success"] is False
        cur.execute("SELECT billing_status FROM call_logs WHERE id=%s", (call,))
        assert cur.fetchone()[0] == "pending"
        cur.execute(
            "UPDATE credit_events SET is_active=true WHERE name='voice_call_minute'"
        )
        cur.execute("SELECT settle_voice_call(%s)", (call,))
        assert cur.fetchone()[0]["success"] is True


def test_history_is_never_rebilled_and_overdraft_policy_is_preserved(settlement_db):
    conn, _, org, _, call = settlement_db
    with conn.cursor() as cur:
        cur.execute("UPDATE call_logs SET billing_status='legacy' WHERE id=%s", (call,))
        cur.execute("SELECT settle_voice_call(%s)", (call,))
        assert cur.fetchone()[0]["already_settled"] is True
        cur.execute(
            "SELECT count(*) FROM credit_transactions WHERE organization_id=%s", (org,)
        )
        assert cur.fetchone()[0] == 0
        cur.execute(
            "UPDATE call_logs SET billing_status='pending' WHERE id=%s", (call,)
        )
        cur.execute("UPDATE organizations SET credit_balance=1 WHERE id=%s", (org,))
        cur.execute("SELECT settle_voice_call(%s)", (call,))
        assert cur.fetchone()[0]["success"] is True
        cur.execute("SELECT credit_balance FROM organizations WHERE id=%s", (org,))
        assert cur.fetchone()[0] == -19


def test_linkage_failure_rolls_back_debit_and_leaves_pending(settlement_db):
    conn, _, org, _, call = settlement_db
    with conn.cursor() as cur:
        cur.execute("""CREATE FUNCTION fail_test_settlement() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN IF NEW.billing_status='settled' THEN
                RAISE EXCEPTION 'synthetic failure'; END IF;
            RETURN NEW; END $$""")
        cur.execute(
            "CREATE TRIGGER fail_test_settlement BEFORE UPDATE ON call_logs FOR EACH"
            " ROW EXECUTE FUNCTION fail_test_settlement()"
        )
        cur.execute("SAVEPOINT settlement_attempt")
        with pytest.raises(psycopg2.errors.RaiseException):
            cur.execute("SELECT settle_voice_call(%s)", (call,))
        cur.execute("ROLLBACK TO SAVEPOINT settlement_attempt")
        cur.execute("SELECT credit_balance FROM organizations WHERE id=%s", (org,))
        assert cur.fetchone()[0] == 100
        cur.execute(
            "SELECT count(*) FROM credit_transactions WHERE organization_id=%s", (org,)
        )
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT billing_status FROM call_logs WHERE id=%s", (call,))
        assert cur.fetchone()[0] == "pending"


def test_private_agent_and_tool_changes_emit_only_safe_ids(settlement_db):
    conn, _, org, agent, _ = settlement_db
    with conn.cursor() as cur:
        cur.execute(
            "SELECT revision FROM agent_change_events WHERE agent_id=%s", (agent,)
        )
        initial = cur.fetchone()[0]
        cur.execute("SET LOCAL ROLE service_role")
        cur.execute(
            "UPDATE voice_agents SET instructions_markdown='private fixture prompt'"
            " WHERE id=%s",
            (agent,),
        )
        tool = str(uuid4())
        cur.execute("INSERT INTO platform_tools(id,name) VALUES (%s,%s)", (tool, tool))
        cur.execute(
            "INSERT INTO agent_tools(agent_id,tool_id,sensitive_config) VALUES"
            " (%s,%s,'private fixture credential')",
            (agent, tool),
        )
        cur.execute(
            "SELECT revision FROM agent_change_events WHERE agent_id=%s", (agent,)
        )
        assert cur.fetchone()[0] == initial + 2
        cur.execute("DELETE FROM agent_tools WHERE agent_id=%s", (agent,))
        cur.execute(
            "SELECT row_to_json(e)::text FROM agent_change_events e WHERE agent_id=%s",
            (agent,),
        )
        payload = cur.fetchone()[0]
        assert "private fixture" not in payload
        assert agent in payload and org in payload
        cur.execute("RESET ROLE")
        cur.execute("SAVEPOINT client_denial")
        cur.execute("SET LOCAL ROLE authenticated")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "UPDATE agent_change_events SET revision=999 WHERE agent_id=%s",
                (agent,),
            )
        cur.execute("ROLLBACK TO SAVEPOINT client_denial")


def _admit(url, org, agent, session, limit=1, call_sid=None):
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='10s'")
            cur.execute("SET LOCAL ROLE service_role")
            cur.execute(
                "SELECT admit_voice_call(%s,%s,%s,%s,%s,NULL,NULL,NULL)",
                (session, call_sid, org, agent, limit),
            )
            return cur.fetchone()[0]


def test_simultaneous_calls_cannot_exceed_the_org_quota(settlement_db):
    conn, url, org, agent, _ = settlement_db
    sessions = [str(uuid4()), str(uuid4())]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda session: _admit(url, org, agent, session), sessions)
        )
    assert sum(result["success"] for result in results) == 1
    assert [r["code"] for r in results if not r["success"]] == ["MAX_CONCURRENT_CALLS"]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM call_logs WHERE organization_id=%s AND"
            " status='initiated'",
            (org,),
        )
        assert cur.fetchone()[0] == 1


def test_voice_session_is_single_use_and_twilio_row_is_reused(settlement_db):
    conn, url, org, agent, _ = settlement_db
    sid, session, row_id = [str(uuid4()) for _ in range(3)]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO call_logs(id,call_sid,organization_id,agent_id,status) VALUES"
            " (%s,%s,%s,%s,'ringing')",
            (row_id, sid, org, agent),
        )
    conn.commit()
    assert _admit(url, org, agent, session, call_sid=sid)["call_log_id"] == row_id
    assert (
        _admit(url, org, agent, session, call_sid=sid)["code"] == "SESSION_ALREADY_USED"
    )
    assert (
        _admit(url, org, agent, str(uuid4()), call_sid=sid)["code"]
        == "SESSION_ALREADY_USED"
    )


def test_admission_rejects_zero_limit_and_foreign_agent(settlement_db):
    _, url, org, agent, _ = settlement_db
    assert (
        _admit(url, org, agent, str(uuid4()), limit=0)["code"] == "MAX_CONCURRENT_CALLS"
    )
    assert _admit(url, org, str(uuid4()), str(uuid4()))["code"] == "AGENT_NOT_FOUND"


def test_worker_crash_expires_slot_and_settles_only_confirmed_duration(settlement_db):
    conn, url, org, agent, _ = settlement_db
    session = str(uuid4())
    call = _admit(url, org, agent, session)["call_log_id"]
    with conn.cursor() as cur:
        cur.execute("SELECT touch_voice_call(%s,'wrong-session')", (call,))
        assert cur.fetchone()[0] is False
        cur.execute("SELECT touch_voice_call(%s,%s)", (call, session))
        assert cur.fetchone()[0] is True
        cur.execute(
            """UPDATE call_logs SET started_at=now()-interval '40 seconds',
            voice_last_seen_at=now()-interval '15 seconds',
            voice_lease_expires_at=now()-interval '1 second'
            WHERE id=%s""",
            (call,),
        )
        cur.execute("SELECT touch_voice_call(%s,%s)", (call, session))
        assert cur.fetchone()[0] is False
        cur.execute("SELECT reconcile_expired_voice_calls(%s)", (org,))
        assert cur.fetchone()[0] == 1
        cur.execute(
            "SELECT status,duration,billing_status FROM call_logs WHERE id=%s", (call,)
        )
        assert cur.fetchone() == ("failed", 25, "pending")
        cur.execute("SELECT settle_voice_call(%s)", (call,))
        assert cur.fetchone()[0]["credits"] == 10
        cur.execute("SELECT reconcile_expired_voice_calls(%s)", (org,))
        assert cur.fetchone()[0] == 0
