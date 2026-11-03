"""Security and response contracts for the maintenance HTTP adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from src.maintenance.http import create_maintenance_app
from src.maintenance.runner import JobResult, UnknownJobError

TOKEN = "x" * 32


@pytest.mark.asyncio
async def test_authentication_is_required_before_work():
    runner = AsyncMock()
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            response = await client.post("/v1/jobs/refresh", headers=headers)
            assert response.status_code == 401
    runner.run.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome,code",
    [("succeeded", 200), ("not_due", 200), ("already_running", 409), ("failed", 503)],
)
async def test_run_status_controls_scheduler_response(outcome, code):
    runner = AsyncMock()
    runner.run.return_value = JobResult("refresh", outcome)
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/jobs/refresh", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == code
    runner.run.assert_awaited_once_with("refresh")


@pytest.mark.asyncio
async def test_errors_do_not_disclose_internal_details():
    runner = AsyncMock()
    runner.run.side_effect = RuntimeError("secret internal detail")
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/jobs/refresh", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == 503
    assert "secret internal detail" not in response.text


@pytest.mark.asyncio
async def test_unknown_job_returns_not_found():
    runner = AsyncMock()
    runner.run.side_effect = UnknownJobError("unknown")
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/jobs/unknown", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == 404


def test_missing_or_short_secret_fails_closed():
    with pytest.raises(ValueError):
        create_maintenance_app(AsyncMock(), "short")


@pytest.mark.asyncio
async def test_dedicated_header_can_coexist_with_infrastructure_identity():
    runner = AsyncMock()
    runner.run.return_value = JobResult("refresh", "succeeded")
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/jobs/refresh",
            headers={
                "Authorization": "Bearer identity-token",
                "X-Maintenance-Key": TOKEN,
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tick_attempts_other_jobs_after_a_failure():
    runner = AsyncMock()
    runner.job_names = ("one", "two", "three")
    runner.run.side_effect = [
        RuntimeError("private detail"),
        JobResult("two", "not_due"),
        JobResult("three", "succeeded"),
    ]
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/tick", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == 503
    assert runner.run.await_count == 3
    assert "private detail" not in response.text


@pytest.mark.asyncio
async def test_tick_does_not_fail_just_because_a_job_is_already_running():
    runner = AsyncMock()
    runner.job_names = ("refresh",)
    runner.run.return_value = JobResult("refresh", "already_running")
    app = create_maintenance_app(runner, TOKEN)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/tick", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_status_requires_auth_and_never_exposes_claim_tokens():
    runner = AsyncMock()
    runner.job_names = ("refresh",)
    reader = AsyncMock(
        return_value=[{"job": "refresh", "state": "running", "claim": "private"}]
    )
    app = create_maintenance_app(runner, TOKEN, reader)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/v1/status")).status_code == 401
        response = await client.get(
            "/v1/status", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == 200
    assert response.json() == {
        "expected_jobs": ["refresh"],
        "jobs": [{"job": "refresh", "state": "running"}],
    }
    reader.assert_awaited_once_with(("refresh",))


@pytest.mark.asyncio
async def test_status_returns_503_for_missing_job_history():
    runner = AsyncMock()
    runner.job_names = ("refresh",)
    app = create_maintenance_app(
        runner, TOKEN, AsyncMock(return_value=[]), AsyncMock(return_value=300)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/v1/status", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == 503
    assert response.json()["unhealthy_jobs"] == ["refresh"]


@pytest.mark.asyncio
@pytest.mark.parametrize("healthy", [True, False])
async def test_heartbeat_is_sent_only_when_all_job_state_is_healthy(healthy):
    runner = AsyncMock()
    runner.job_names = ("refresh",)
    runner.run.return_value = JobResult("refresh", "not_due")
    rows = (
        [
            {
                "job": "refresh",
                "state": "idle",
                "last_succeeded_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        if healthy
        else []
    )
    heartbeat = AsyncMock()
    app = create_maintenance_app(
        runner,
        TOKEN,
        AsyncMock(return_value=rows),
        AsyncMock(return_value=300),
        heartbeat,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/tick", headers={"Authorization": f"Bearer {TOKEN}"}
        )
    assert response.status_code == (200 if healthy else 503)
    assert heartbeat.await_count == int(healthy)
