"""Dashboard aggregates remain complete, scoped, and safely authorized."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.auth.middleware import get_authenticated_user
from src.call_logs.routes import call_logs_router
from src.call_logs.service import CallLogService


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", [False, True])
async def test_analytics_reads_past_first_database_page(platform):
    """A full first page must not silently truncate totals at 1,000 calls."""
    org = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "organization_id": str(org),
        "agent_id": None,
        "created_at": now,
        "duration": 30,
        "status": "completed",
    }
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [MagicMock(data=[row] * 1000), MagicMock(data=[row])]
    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(None if platform else org)
    assert error is None
    assert result.total_calls_month == 1001
    assert result.total_calls_week == 1001
    assert result.active_organizations == 1
    assert result.avg_duration_seconds == 30
    assert sum(item["count"] for item in result.calls_by_status) == 1001
    assert query.range.call_args_list[-1].args == (1000, 1999)
    if platform:
        query.eq.assert_not_called()
    else:
        assert all(
            call.args == ("organization_id", str(org))
            for call in query.eq.call_args_list
        )


@pytest.mark.asyncio
async def test_analytics_empty_and_provider_failure():
    """Only a successful empty query is represented as zero."""
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[])
    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(uuid4())
        assert error is None
        assert result.total_calls_month == 0
        query.execute.side_effect = RuntimeError("provider-private-detail")
        result, error = await CallLogService().get_analytics(uuid4())
    assert result is None
    assert error == "Call analytics unavailable"


@pytest.fixture
def client():
    """Exercise the actual API dependency and response validation boundary."""
    app = FastAPI()
    app.include_router(call_logs_router)
    return TestClient(app)


@pytest.mark.parametrize("role", ["regular_user", "org_admin", "platform_admin"])
def test_platform_analytics_requires_platform_role(client, role):
    profile = MagicMock()
    profile.has_role.side_effect = lambda name, *args: name == role
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    payload = {
        "total_calls_week": 0,
        "total_calls_month": 0,
        "avg_duration_seconds": 0,
        "calls_by_agent": [],
        "calls_by_hour": [],
        "calls_by_status": [],
    }
    with patch(
        "src.call_logs.routes.call_log_service.get_analytics", new_callable=AsyncMock
    ) as service:
        service.return_value = (payload, None)
        response = client.get("/api/v1/calls/platform/analytics")
    assert response.status_code == (200 if role == "platform_admin" else 403)
    if role == "platform_admin":
        service.assert_awaited_once_with(
            organization_id=None,
            period_days=30,
            calendar_period=None,
            call_status=None,
            timezone_name="UTC",
        )
    else:
        service.assert_not_awaited()


def test_platform_analytics_applies_filters_and_rejects_unsupported_period(client):
    profile = MagicMock()
    profile.has_role.return_value = True
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    payload = {
        "total_calls_week": 4,
        "total_calls_month": 9,
        "avg_duration_seconds": 12,
        "selected_period_days": 7,
        "selected_status": "failed",
        "selected_total_calls": 1,
        "selected_average_duration_seconds": None,
        "calls_by_day": [],
        "available_statuses": ["completed", "failed"],
        "calls_by_agent": [],
        "calls_by_hour": [],
        "calls_by_status": [{"status": "failed", "count": 1}],
    }
    with patch(
        "src.call_logs.routes.call_log_service.get_analytics", new_callable=AsyncMock
    ) as service:
        service.return_value = (payload, None)
        response = client.get(
            "/api/v1/calls/platform/analytics?period_days=7&status=failed"
        )
        assert response.status_code == 200, response.text
        assert response.json()["selected_status"] == "failed"
        service.assert_awaited_once_with(
            organization_id=None,
            period_days=7,
            calendar_period=None,
            call_status="failed",
            timezone_name="UTC",
        )

        service.reset_mock()
        fifteen_days = client.get("/api/v1/calls/platform/analytics?period_days=15")
        assert fifteen_days.status_code == 200, fifteen_days.text
        service.assert_awaited_once_with(
            organization_id=None,
            period_days=15,
            calendar_period=None,
            call_status=None,
            timezone_name="UTC",
        )

        service.reset_mock()
        unsupported_period = client.get(
            "/api/v1/calls/platform/analytics?period_days=14"
        )
        assert unsupported_period.status_code == 422
        service.assert_not_awaited()


def test_org_analytics_denies_other_tenant_and_invalid_id(client):
    org = uuid4()
    profile = MagicMock()
    profile.has_role.side_effect = (
        lambda role, scope=None: role == "regular_user" and scope == str(org)
    )
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    with patch(
        "src.call_logs.routes.call_log_service.get_analytics", new_callable=AsyncMock
    ) as service:
        assert (
            client.get(f"/api/v1/calls/organization/{uuid4()}/analytics").status_code
            == 403
        )
        assert (
            client.get("/api/v1/calls/organization/invalid/analytics").status_code
            == 422
        )
        service.assert_not_awaited()


def test_org_analytics_accepts_shared_dashboard_filters_and_validates_timezone(client):
    org = uuid4()
    profile = MagicMock()
    profile.has_role.side_effect = (
        lambda role, scope=None: role == "regular_user" and scope == str(org)
    )
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    payload = {
        "active_organizations": 1,
        "total_calls_week": 3,
        "total_calls_month": 8,
        "avg_duration_seconds": 24,
        "selected_period_days": 7,
        "selected_status": "failed",
        "selected_total_calls": 2,
        "selected_average_duration_seconds": None,
        "available_statuses": ["completed", "failed"],
        "calls_by_day": [],
        "calls_by_agent": [],
        "calls_by_hour": [],
        "calls_by_status": [{"status": "failed", "count": 2}],
    }
    with patch(
        "src.call_logs.routes.call_log_service.get_analytics", new_callable=AsyncMock
    ) as service:
        service.return_value = (payload, None)
        response = client.get(
            f"/api/v1/calls/organization/{org}/analytics"
            "?period_days=7&status=failed&timezone_name=America%2FPhoenix"
        )
        assert response.status_code == 200, response.text
        assert response.json()["selected_total_calls"] == 2
        service.assert_awaited_once_with(
            organization_id=org,
            period_days=7,
            calendar_period=None,
            call_status="failed",
            timezone_name="America/Phoenix",
        )

        invalid_timezone = client.get(
            f"/api/v1/calls/organization/{org}/analytics?timezone_name=NotARealZone"
        )
        unsupported_period = client.get(
            f"/api/v1/calls/organization/{org}/analytics?period_days=14"
        )
        assert invalid_timezone.status_code == 422
        assert invalid_timezone.json()["detail"] == "Invalid organization timezone"
        assert unsupported_period.status_code == 422
        service.assert_awaited_once()


def test_org_calendar_period_uses_workspace_timezone_and_rejects_mixed_ranges(client):
    org = uuid4()
    profile = MagicMock()
    profile.has_role.side_effect = (
        lambda role, scope=None: role == "regular_user" and scope == str(org)
    )
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    payload = {
        "active_organizations": 1,
        "total_calls_week": 0,
        "total_calls_month": 0,
        "avg_duration_seconds": 0,
        "selected_period_days": 1,
        "selected_status": None,
        "selected_total_calls": 0,
        "selected_active_organizations": 0,
        "selected_average_duration_seconds": None,
        "available_statuses": [],
        "calls_by_day": [],
        "calls_by_agent": [],
        "calls_by_hour": [],
        "calls_by_status": [],
    }
    with patch(
        "src.call_logs.routes.call_log_service.get_analytics", new_callable=AsyncMock
    ) as service:
        service.return_value = (payload, None)
        response = client.get(
            f"/api/v1/calls/organization/{org}/analytics"
            "?period=yesterday&timezone_name=America%2FNew_York"
        )
        assert response.status_code == 200, response.text
        service.assert_awaited_once_with(
            organization_id=org,
            period_days=30,
            calendar_period="yesterday",
            call_status=None,
            timezone_name="America/New_York",
        )

        conflicting_ranges = client.get(
            f"/api/v1/calls/organization/{org}/analytics?period=today&period_days=7"
        )
        assert conflicting_ranges.status_code == 422
        service.assert_awaited_once()


def test_platform_provider_failure_is_not_a_zero_response(client):
    profile = MagicMock()
    profile.has_role.return_value = True
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    with patch(
        "src.call_logs.routes.call_log_service.get_analytics", new_callable=AsyncMock
    ) as service:
        service.return_value = (None, "Call analytics unavailable")
        response = client.get("/api/v1/calls/platform/analytics")
    assert response.status_code == 503
    assert response.json()["detail"] == "Call analytics unavailable"


@pytest.mark.asyncio
async def test_agent_names_and_utc_hours_are_scoped():
    """An org report resolves only its agent names and normalizes offset hours."""
    org, agent = uuid4(), uuid4()
    clock = MagicMock(wraps=datetime)
    clock.now.return_value = datetime(2026, 9, 16, tzinfo=timezone.utc)
    row = {
        "organization_id": str(org),
        "agent_id": str(agent),
        "created_at": "2026-09-15T01:00:00+02:00",
        "duration": None,
        "status": "failed",
    }
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq", "in_"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [
        MagicMock(data=[row]),
        MagicMock(data=[{"id": str(agent), "name": "Test agent"}]),
    ]
    with (
        patch("src.call_logs.service.supabase_config") as config,
        patch("src.call_logs.service.datetime", clock),
    ):
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(org)
    assert error is None
    assert result.calls_by_hour[23]["calls"] == 1
    assert result.calls_by_agent[0]["agent_name"] == "Test agent"
    assert result.avg_duration_seconds == 0
    assert query.eq.call_count == 2
    query.eq.assert_called_with("organization_id", str(org))


@pytest.mark.asyncio
async def test_selected_period_status_and_timezone_drive_dashboard_breakdowns():
    """Dashboard charts share the selected call window and workspace timezone."""
    org, agent = uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    rows = [
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": (now - timedelta(days=1)).isoformat(),
            "duration": None,
            "status": "failed",
            "source_type": "phone",
        },
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "duration": 60,
            "status": "completed",
            "source_type": "phone",
        },
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": (now - timedelta(days=3)).isoformat(),
            "duration": 20,
            "status": "no-answer",
            "source_type": "web_demo",
        },
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": (now - timedelta(days=10)).isoformat(),
            "duration": 90,
            "status": "completed",
            "source_type": "phone",
        },
    ]
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq", "in_"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [
        MagicMock(data=rows),
        MagicMock(data=[{"id": str(agent), "name": "Test agent"}]),
    ]

    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(
            org,
            period_days=7,
            call_status="failed",
            timezone_name="America/Phoenix",
        )

    assert error is None
    assert result.selected_period_days == 7
    assert result.selected_status == "failed"
    assert result.selected_total_calls == 1
    assert result.selected_active_organizations == 1
    assert result.selected_average_duration_seconds is None
    assert result.calls_by_status == [{"status": "failed", "count": 1}]
    assert result.available_statuses == ["completed", "failed", "no-answer"]
    assert result.calls_by_agent[0]["count"] == 1
    assert result.calls_by_agent[0]["avg_duration_seconds"] is None
    local_call = now - timedelta(days=1)
    local_call = local_call.astimezone(ZoneInfo("America/Phoenix"))
    assert result.calls_by_hour[local_call.hour]["calls"] == 1
    assert {item["date"] for item in result.calls_by_day if item["calls"]} == {
        local_call.date().isoformat()
    }
    query.eq.assert_called_with("organization_id", str(org))


@pytest.mark.asyncio
async def test_completed_call_averages_skip_missing_and_unsuccessful_durations():
    """Duration cards summarize completed calls with an actual duration only."""
    org, agent = uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    rows = [
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": now.isoformat(),
            "duration": 60,
            "status": "completed",
        },
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": now.isoformat(),
            "duration": None,
            "status": "completed",
        },
        {
            "organization_id": str(org),
            "agent_id": str(agent),
            "created_at": now.isoformat(),
            "duration": 200,
            "status": "failed",
        },
    ]
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq", "in_"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [
        MagicMock(data=rows),
        MagicMock(data=[{"id": str(agent), "name": "Test agent"}]),
    ]

    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(org)

    assert error is None
    assert result.selected_average_duration_seconds == 60
    assert result.selected_active_organizations == 1
    assert result.calls_by_agent[0]["avg_duration_seconds"] == 60


@pytest.mark.asyncio
async def test_unassigned_calls_are_labeled_without_a_fake_agent_id():
    """Unassigned activity remains visible as its own dashboard bucket."""
    org = uuid4()
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(
        data=[
            {
                "organization_id": str(org),
                "agent_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "duration": None,
                "status": "failed",
            }
        ]
    )
    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(org)

    assert error is None
    assert result.calls_by_agent[0]["agent_id"] is None
    assert result.calls_by_agent[0]["agent_name"] == "Unassigned calls"


@pytest.mark.asyncio
async def test_reporting_limit_fails_instead_of_returning_partial_totals():
    """Bounded reads must fail explicitly at the reporting-volume limit."""
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[{}] * 1000)
    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(None)
    assert result is None
    assert "reporting limit" in error
    assert query.execute.call_count == 100


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("calendar_period", "period_start", "period_end", "report_date"),
    [
        (
            "today",
            "2025-03-10T04:00:00+00:00",
            "2025-03-10T12:00:00+00:00",
            "2025-03-10",
        ),
        (
            "yesterday",
            "2025-03-09T05:00:00+00:00",
            "2025-03-10T04:00:00+00:00",
            "2025-03-09",
        ),
    ],
)
async def test_calendar_reporting_periods_use_timezone_midnights_and_exclusive_end(
    calendar_period, period_start, period_end, report_date
):
    """Calendar periods use local midnight and exclude the following boundary."""
    org = uuid4()
    frozen_now = datetime(2025, 3, 10, 12, tzinfo=timezone.utc)
    start = datetime.fromisoformat(period_start)
    end = datetime.fromisoformat(period_end)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now.astimezone(tz) if tz else frozen_now.replace(tzinfo=None)

    def call_row(created_at, duration):
        return {
            "organization_id": str(org),
            "agent_id": None,
            "created_at": created_at.isoformat(),
            "duration": duration,
            "status": "completed",
        }

    rows = [
        call_row(start - timedelta(seconds=1), 999),
        call_row(start, 30),
        call_row(end - timedelta(seconds=1), 60),
        call_row(end, 999),
    ]
    query = MagicMock()
    for method in ("select", "gte", "lt", "order", "range", "eq"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=rows)

    with (
        patch("src.call_logs.service.datetime", FrozenDateTime),
        patch("src.call_logs.service.supabase_config") as config,
    ):
        config.client.table.return_value = query
        result, error = await CallLogService().get_analytics(
            org,
            calendar_period=calendar_period,
            timezone_name="America/New_York",
        )

    assert error is None
    assert result.selected_period_days == 1
    assert result.selected_total_calls == 2
    assert result.selected_average_duration_seconds == 45
    assert result.calls_by_day == [{"date": report_date, "calls": 2}]


@pytest.mark.asyncio
async def test_call_list_supports_an_exclusive_end_for_calendar_periods():
    """An exclusive end keeps midnight records out of the prior calendar day."""
    query = MagicMock()
    for method in ("select", "eq", "order", "gte", "lt", "lte", "range"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=[], count=0)
    end = datetime(2025, 3, 10, 4, tzinfo=timezone.utc)

    with patch("src.call_logs.service.supabase_config") as config:
        config.client.table.return_value = query
        result, error = await CallLogService().list_call_logs(
            uuid4(), date_to_exclusive=end
        )

    assert error is None
    assert result.total == 0
    query.lt.assert_called_once_with("created_at", end.isoformat())
    query.lte.assert_not_called()


def test_call_list_route_passes_exclusive_end_and_rejects_two_end_filters(client):
    """The recent-call route preserves half-open windows at its API boundary."""
    org = uuid4()
    profile = MagicMock()
    profile.has_role.side_effect = (
        lambda role, scope=None: role == "regular_user" and scope == str(org)
    )
    client.app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    boundary = datetime(2025, 3, 10, 4, tzinfo=timezone.utc)
    with patch(
        "src.call_logs.routes.call_log_service.list_call_logs", new_callable=AsyncMock
    ) as service:
        service.return_value = (
            {"items": [], "total": 0, "page": 1, "page_size": 25, "total_pages": 1},
            None,
        )
        response = client.get(
            f"/api/v1/calls/organization/{org}"
            "?date_to_exclusive=2025-03-10T04%3A00%3A00Z"
        )
        assert response.status_code == 200, response.text
        service.assert_awaited_once_with(
            organization_id=org,
            agent_id=None,
            status=None,
            source_type=None,
            date_from=None,
            date_to=None,
            date_to_exclusive=boundary,
            recording_only=False,
            page=1,
            page_size=25,
        )

        conflicting_filters = client.get(
            f"/api/v1/calls/organization/{org}"
            "?date_to=2025-03-10T04%3A00%3A00Z"
            "&date_to_exclusive=2025-03-10T04%3A00%3A00Z"
        )
        assert conflicting_filters.status_code == 422
        service.assert_awaited_once()
