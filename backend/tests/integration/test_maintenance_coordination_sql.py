"""Exercise atomic maintenance claims against a disposable local database."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import psycopg2
import pytest
from src.maintenance.coordinator import PostgresRunCoordinator
from src.maintenance.http import create_maintenance_app
from src.maintenance.runner import MaintenanceRunner

pytestmark = pytest.mark.integration


@pytest.fixture
def database():
    """Require an explicitly selected, local disposable database."""
    url = os.getenv("MAINTENANCE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("MAINTENANCE_TEST_DATABASE_URL must point to a disposable DB")
    if urlsplit(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Maintenance integration tests refuse non-local databases")
    job = f"test-{uuid4()}"
    yield url, job
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM maintenance_runs WHERE job = %s", (job,))


def _claim(url, job, claim):
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute("SELECT claim_maintenance_run(%s, %s)", (job, claim))
            return cursor.fetchone()[0]


def test_parallel_claims_have_one_owner_and_stale_completion_is_rejected(database):
    url, job = database
    claims = [str(uuid4()), str(uuid4())]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda claim: _claim(url, job, claim), claims))
    assert sorted(outcomes) == ["claimed", "running"]
    owner = claims[outcomes.index("claimed")]
    stale = claims[outcomes.index("running")]
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute(
                "SELECT complete_maintenance_run(%s, %s, true)", (job, stale)
            )
            assert cursor.fetchone()[0] is False
            cursor.execute(
                "SELECT complete_maintenance_run(%s, %s, false)", (job, owner)
            )
            assert cursor.fetchone()[0] is True
    assert _claim(url, job, str(uuid4())) == "blocked"
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute("SELECT reconcile_maintenance_run(%s, %s)", (job, stale))
            assert cursor.fetchone()[0] is False
            cursor.execute("SELECT reconcile_maintenance_run(%s, %s)", (job, owner))
            assert cursor.fetchone()[0] is True
    assert _claim(url, job, str(uuid4())) == "claimed"


def test_successful_completion_allows_next_scheduled_run(database):
    url, job = database
    owner = str(uuid4())
    assert _claim(url, job, owner) == "claimed"
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute(
                "SELECT complete_maintenance_run(%s, %s, true)", (job, owner)
            )
            assert cursor.fetchone()[0] is True
    assert _claim(url, job, str(uuid4())) == "claimed"


def test_retry_safe_failure_does_not_record_a_success(database):
    url, job = database
    owner = str(uuid4())
    assert _claim(url, job, owner) == "claimed"
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute("SELECT retry_maintenance_run(%s, %s)", (job, owner))
            assert cursor.fetchone()[0] is True
            cursor.execute("RESET ROLE")
            cursor.execute(
                "SELECT state,last_succeeded_at,last_failed_at IS NOT NULL "
                "FROM maintenance_runs WHERE job=%s",
                (job,),
            )
            assert cursor.fetchone() == ("idle", None, True)
    assert _claim(url, job, str(uuid4())) == "claimed"


def test_cadence_skips_jobs_without_modifying_last_success(database):
    url, job = database
    owner = str(uuid4())
    assert _claim(url, job, owner) == "claimed"
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute(
                "SELECT complete_maintenance_run(%s, %s, true)", (job, owner)
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT claim_maintenance_run(%s, %s, %s)", (job, "new", 3600)
            )
            assert cursor.fetchone()[0] == "not_due"


def test_api_guard_releases_without_changing_scheduled_success(database):
    url, job = database
    owner = str(uuid4())
    assert _claim(url, job, owner) == "claimed"
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE service_role")
            cursor.execute("SELECT release_maintenance_guard(%s,%s)", (job, owner))
            assert cursor.fetchone()[0] is True
            cursor.execute("RESET ROLE")
            cursor.execute(
                "SELECT state,last_succeeded_at,last_failed_at "
                "FROM maintenance_runs WHERE job=%s",
                (job,),
            )
            assert cursor.fetchone() == ("idle", None, None)
    assert _claim(url, job, str(uuid4())) == "claimed"


def test_phone_guards_serialize_one_organization_without_blocking_another(database):
    url, job = database
    first = f"{job}-org-a"
    second = f"{job}-org-b"
    try:
        assert _claim(url, first, "worker") == "claimed"
        assert _claim(url, first, "api") == "running"
        assert _claim(url, second, "other-api") == "claimed"
    finally:
        with psycopg2.connect(url, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM maintenance_runs WHERE job IN (%s,%s)", (first, second)
                )


def test_unprivileged_roles_cannot_claim_jobs(database):
    url, job = database
    with psycopg2.connect(url, connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE anon")
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cursor.execute("SELECT claim_maintenance_run(%s, %s)", (job, "no"))


@pytest.mark.asyncio
async def test_concurrent_http_requests_only_run_the_operation_once(database):
    url, job = database

    class SqlRpcClient:
        def rpc(self, name, params):
            def execute():
                with psycopg2.connect(url, connect_timeout=5) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL ROLE service_role")
                        if name == "claim_maintenance_run":
                            cursor.execute(
                                "SELECT claim_maintenance_run(%s,%s,%s)",
                                (
                                    params["p_job"],
                                    params["p_claim"],
                                    params["p_interval_seconds"],
                                ),
                            )
                        elif name == "complete_maintenance_run":
                            cursor.execute(
                                "SELECT complete_maintenance_run(%s,%s,%s)",
                                (
                                    params["p_job"],
                                    params["p_claim"],
                                    params["p_succeeded"],
                                ),
                            )
                        else:
                            raise AssertionError("Unexpected RPC")
                        return SimpleNamespace(data=cursor.fetchone()[0])

            return SimpleNamespace(execute=execute)

    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def operation():
        calls.append(1)
        entered.set()
        await release.wait()

    runner = MaintenanceRunner({job: operation}, PostgresRunCoordinator(SqlRpcClient()))
    app = create_maintenance_app(runner, "x" * 32)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"Authorization": "Bearer " + "x" * 32}
        first = asyncio.create_task(client.post(f"/v1/jobs/{job}", headers=headers))
        await asyncio.wait_for(entered.wait(), timeout=5)
        second = await client.post(f"/v1/jobs/{job}", headers=headers)
        release.set()
        assert (await first).status_code == 200
        assert second.status_code == 409
    assert len(calls) == 1
