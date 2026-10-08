"""Real-auth dashboard smoke tests for the isolated worktree fixture.

Run with E2E_REAL_AUTH=1 and E2E_BASE_URL pointing at worktree-stack.sh config.
No provider calls or customer data are created by these tests.
"""

import os
import re
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import Locator, Page, expect

pytestmark = pytest.mark.skipif(
    os.getenv("E2E_REAL_AUTH") != "1",
    reason="Requires the isolated worktree's real-auth fixture accounts",
)


@pytest.fixture(autouse=True)
def dismiss_optional_tour_overlay(page: Page):
    """Dismiss the optional tour when it appears during page interactions."""
    page.add_locator_handler(
        page.get_by_role("button", name="Skip tour"), lambda locator: locator.click()
    )
    yield


@pytest.fixture(autouse=True)
def apply_mocks():
    """Leave the isolated stack's real auth and data boundaries untouched.

    ``e2e/tests/conftest.py`` supplies boundary mocks for the broader mocked
    suite under this same fixture name. This module is explicitly opted into
    the worktree's seeded accounts with ``E2E_REAL_AUTH=1`` and therefore
    shadows that fixture so role and tenant behavior are exercised end to end.
    """
    yield


def dismiss_optional_tour(page: Page) -> None:
    """Dismiss the optional tour before dashboard pointer interactions."""
    skip = page.get_by_role("button", name="Skip tour")
    if skip.is_visible():
        skip.click()
        expect(skip).to_be_hidden(timeout=5000)


def sign_in(page: Page, base_url: str, role: str) -> None:
    page.goto(f"{base_url}/auth/signin")
    page.get_by_label("Email Address").fill(f"{role}@247ai.local")
    page.locator("input#password").fill("Password123!")
    page.get_by_role("button", name="Sign In", exact=True).click()
    # The heading is the selected organization name, so use the stable page
    # eyebrow to wait for the dashboard shell after authentication.
    expect(page.get_by_text("Workspace overview", exact=True)).to_be_visible(
        timeout=30000
    )
    dismiss_optional_tour(page)


def wait_until(predicate, page: Page, description: str) -> None:
    """Poll a Python-side request assertion for Playwright versions without expect.poll."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if predicate():
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"Timed out waiting for {description}")


def assert_immediate_chart_readout(
    page: Page, chart: Locator, x_fraction: float, expected: str
) -> None:
    """Move across a chart and verify its shared, immediate value readout."""
    dismiss_optional_tour(page)
    expect(chart).to_be_visible()
    chart.scroll_into_view_if_needed()
    bounds = chart.bounding_box()
    assert bounds is not None
    pointer_x = bounds["x"] + bounds["width"] * x_fraction
    pointer_y = bounds["y"] + bounds["height"] / 2
    tooltip = chart.get_by_role("tooltip")
    for attempt in range(2):
        dismiss_optional_tour(page)
        page.mouse.move(pointer_x, pointer_y)
        try:
            expect(tooltip).to_be_visible(timeout=1000)
            expect(tooltip).to_have_attribute("aria-label", expected, timeout=1000)
            break
        except AssertionError:
            if attempt == 1:
                raise
    expect(chart.locator("[title]")).to_have_count(0)


@pytest.mark.parametrize("role", ["org-admin", "regular-user", "platform-admin"])
def test_dashboard_real_roles_follow_the_selected_workspace(
    page: Page, base_url: str, role: str
):
    """Every role sees workspace data when selected, with role-specific actions."""
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    sign_in(page, base_url, role)
    main = page.locator("main")
    choose_workspace = main.get_by_role("heading", name="Choose a workspace")
    workspace_selected = choose_workspace.count() == 0
    organization_reports = [
        url
        for url in requests
        if "/api/v1/calls/organization/" in url and "/analytics" in url
    ]
    if role == "platform-admin":
        expect(main.get_by_text("Platform pulse", exact=True)).to_be_visible()
        expect(main.get_by_role("link", name="View platform overview")).to_be_visible()
        if workspace_selected:
            expect(main.get_by_text("Workspace overview", exact=True)).to_be_visible()
            expect(main.get_by_text("Call performance", exact=True)).to_be_visible(
                timeout=30000
            )
            expect(main.get_by_text("Peak call hours", exact=True)).to_be_visible()
            expect(main.get_by_role("heading", name="Agent activity")).to_be_visible()
            expect(main.get_by_role("heading", name="Recent calls")).to_be_visible()
            assert (
                organization_reports
            ), "Selected workspace analytics were not requested"
            expect(
                main.get_by_role("heading", name="Platform administration")
            ).to_be_visible()
        else:
            expect(choose_workspace).to_be_visible()
    else:
        expect(main.get_by_text("Workspace overview", exact=True)).to_be_visible()
        expect(main.get_by_text("Call performance", exact=True)).to_be_visible(
            timeout=30000
        )
        expect(main.get_by_text("Peak call hours", exact=True)).to_be_visible()
        expect(main.get_by_role("heading", name="Agent activity")).to_be_visible()
        expect(main.get_by_role("heading", name="Recent calls")).to_be_visible()
        assert organization_reports, "Workspace analytics were not requested"

    expect(main.get_by_text("Total Revenue", exact=True)).to_have_count(0)
    expect(main.get_by_role("alert")).to_have_count(0)

    if role == "org-admin":
        expect(main.get_by_text("Available credits", exact=True)).to_be_visible(
            timeout=15000
        )
        expect(main.get_by_role("link", name="Manage callbacks")).to_be_visible()
        expect(main.get_by_role("link", name="Create agent")).to_be_visible()
    elif role == "regular-user":
        expect(main.get_by_role("link", name="View callback queue")).to_be_visible()
        expect(main.get_by_role("heading", name="Account capacity")).to_have_count(0)
        expect(main.get_by_role("link", name="Create agent")).to_have_count(0)

    page.set_viewport_size({"width": 390, "height": 844})
    if workspace_selected:
        expect(main.get_by_text("Workspace overview", exact=True)).to_be_visible()
    else:
        expect(choose_workspace).to_be_visible()
    expect(page.get_by_role("button", name="Expand navigation")).to_be_visible()
    assert main.bounding_box()["width"] >= 350
    page.get_by_role("button", name="Expand navigation").click()
    expect(page.get_by_role("button", name="Close navigation")).to_be_visible()
    page.get_by_role("button", name="Close navigation").click()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_platform_overview_filters_cross_organization_data(page: Page, base_url: str):
    """The separate admin page shows platform aggregates and forwards filters."""
    report = {
        "active_organizations": 2,
        "total_calls_week": 7,
        "total_calls_month": 12,
        "avg_duration_seconds": 45,
        "selected_period_days": 30,
        "selected_status": None,
        "selected_total_calls": 12,
        "selected_active_organizations": 2,
        "selected_average_duration_seconds": 45,
        "available_statuses": ["completed", "failed"],
        "calls_by_day": [
            {"date": "2026-09-14", "calls": 7},
            {"date": "2026-09-15", "calls": 5},
        ],
        "calls_by_hour": [
            {"hour": hour, "calls": 4 if hour == 16 else 0} for hour in range(24)
        ],
        "calls_by_agent": [],
        "calls_by_status": [
            {"status": "completed", "count": 10},
            {"status": "failed", "count": 2},
        ],
    }
    analytics_requests = []

    def respond(route):
        query = parse_qs(urlsplit(route.request.url).query)
        analytics_requests.append(query)
        status = query.get("status", [None])[0]
        filtered = dict(report)
        filtered["selected_period_days"] = (
            1 if query.get("period") else int(query.get("period_days", ["30"])[0])
        )
        if status:
            count = 2 if status == "failed" else 10
            filtered["selected_status"] = status
            filtered["selected_total_calls"] = count
            filtered["selected_average_duration_seconds"] = None
            filtered["calls_by_status"] = [{"status": status, "count": count}]
        route.fulfill(json=filtered)

    page.route("**/api/v1/calls/platform/analytics**", respond)
    sign_in(page, base_url, "platform-admin")
    main = page.locator("main")
    link = main.get_by_role("link", name="View platform overview")
    if link.is_visible():
        link.click()
    else:
        page.goto(f"{base_url}/platform/dashboard")

    expect(page.get_by_role("heading", name="Platform overview")).to_be_visible(
        timeout=30000
    )
    expect(page.get_by_text("Platform call volume", exact=True)).to_be_visible()
    expect(page.get_by_text("Organizations with calls", exact=True)).to_be_visible()
    assert analytics_requests

    assert_immediate_chart_readout(
        page,
        main.get_by_role(
            "group",
            name="Platform daily call volume. Move the pointer or use the arrow keys to inspect each UTC date.",
        ),
        0.9,
        "Sep 15, 2026, 5 calls",
    )
    assert_immediate_chart_readout(
        page,
        main.get_by_role(
            "group",
            name="Calls by hour in UTC. Move the pointer or use the arrow keys to inspect each hour.",
        ),
        0.69,
        "16:00–17:00, 4 calls",
    )
    assert_immediate_chart_readout(
        page,
        main.get_by_role(
            "group",
            name="Platform call outcomes by status. Move the pointer or use the arrow keys to inspect each status.",
        ),
        0.95,
        "Failed, 2 calls",
    )

    page.get_by_label("Platform reporting period").select_option("last_7_days")
    wait_until(
        lambda: any(item.get("period_days") == ["7"] for item in analytics_requests),
        page,
        "platform period request",
    )
    page.get_by_label("Platform call status filter").select_option("failed")
    wait_until(
        lambda: any(item.get("status") == ["failed"] for item in analytics_requests),
        page,
        "platform status request",
    )
    page.get_by_label("Platform reporting period").select_option("today")
    wait_until(
        lambda: any(item.get("period") == ["today"] for item in analytics_requests),
        page,
        "platform calendar-day request",
    )
    expect(page.get_by_text("Call outcomes", exact=True)).to_be_visible()


def test_workspace_dashboard_filters_recent_calls_and_surfaces_refresh_failure(
    page: Page, base_url: str
):
    """Workspace filters share the same window; failures remain visible, not zero."""
    import json

    from playwright.sync_api import Route

    workspace_report = {
        "active_organizations": 1,
        "total_calls_week": 7,
        "total_calls_month": 12,
        "avg_duration_seconds": 45,
        "selected_period_days": 30,
        "selected_status": None,
        "selected_total_calls": 12,
        "selected_active_organizations": 1,
        "selected_average_duration_seconds": 45,
        "available_statuses": ["completed", "failed"],
        "calls_by_day": [
            {"date": "2026-09-14", "calls": 5},
            {"date": "2026-09-15", "calls": 7},
        ],
        "calls_by_hour": [
            {"hour": hour, "calls": 4 if hour == 14 else 0} for hour in range(24)
        ],
        "calls_by_agent": [
            {
                "agent_id": "test-agent",
                "agent_name": "Fixture receptionist",
                "count": 12,
                "avg_duration_seconds": 45,
                "last_call_at": "2026-09-15T12:00:00Z",
                "last_call_status": "completed",
                "last_call_duration_seconds": 45,
                "last_call_source_type": "phone",
            }
        ],
        "calls_by_status": [
            {"status": "completed", "count": 10},
            {"status": "failed", "count": 2},
        ],
    }
    call_item = {
        "id": "call-log-1",
        "call_sid": "test-call-1",
        "organization_id": "test-org",
        "agent_id": "test-agent",
        "caller_number": None,
        "called_number": None,
        "source_type": "phone",
        "source_url": None,
        "source_domain": None,
        "status": "completed",
        "failure_code": None,
        "failure_message": None,
        "duration": 45,
        "credits_consumed": 1,
        "credit_transaction_id": None,
        "recording_available": False,
        "started_at": None,
        "ended_at": None,
        "created_at": "2026-09-15T12:00:00Z",
        "updated_at": "2026-09-15T12:00:00Z",
    }
    organization_requests = []

    def respond_organization(route: Route):
        parsed = urlsplit(route.request.url)
        query = parse_qs(parsed.query)
        organization_requests.append((parsed.path, query))
        if parsed.path.endswith("/analytics"):
            status = query.get("status", [None])[0]
            result = dict(workspace_report)
            result["selected_period_days"] = (
                1 if query.get("period") else int(query.get("period_days", ["30"])[0])
            )
            if status:
                result["selected_status"] = status
                result["selected_total_calls"] = 2
                result["selected_active_organizations"] = 1
                result["selected_average_duration_seconds"] = None
                result["calls_by_status"] = [{"status": status, "count": 2}]
                result["calls_by_agent"] = []
            route.fulfill(json=result)
        elif "date_from" in query:
            items = [] if query.get("status") == ["failed"] else [call_item]
            route.fulfill(
                json={
                    "items": items,
                    "total": len(items),
                    "page": 1,
                    "page_size": 6,
                    "total_pages": 1,
                }
            )
        else:
            route.continue_()

    def respond_agent_summary(route: Route):
        route.fulfill(json={"total_agents": 2, "active_agents": 2})

    org_pattern = "**/api/v1/calls/organization/**"
    page.route(org_pattern, respond_organization)
    page.route("**/api/v1/agents/organization/*/summary", respond_agent_summary)
    sign_in(page, base_url, "regular-user")
    main = page.locator("main")
    expect(main.get_by_text("Call performance", exact=True)).to_be_visible(
        timeout=30000
    )
    expect(main.get_by_text("Fixture receptionist", exact=True).first).to_be_visible()

    assert_immediate_chart_readout(
        page,
        main.get_by_role(
            "group",
            name="Daily call volume chart. Move the pointer or use the arrow keys to inspect each day.",
        ),
        0.9,
        "Sep 15, 2026, 7 calls",
    )
    assert_immediate_chart_readout(
        page,
        main.get_by_role(
            "group",
            name=re.compile(
                r"Calls by hour in .+\. Move the pointer or use the arrow keys to inspect each hour\."
            ),
        ),
        0.61,
        "14:00–15:00, 4 calls",
    )
    assert_immediate_chart_readout(
        page,
        main.get_by_role("group", name=re.compile(r"Call outcomes by status")),
        0.95,
        "Failed, 2 calls",
    )

    main.get_by_label("Call reporting period").select_option("last_7_days")
    wait_until(
        lambda: any(
            query.get("period_days") == ["7"]
            for path, query in organization_requests
            if path.endswith("/analytics")
        ),
        page,
        "workspace period request",
    )
    main.get_by_label("Call status filter").select_option("failed")
    wait_until(
        lambda: any(
            query.get("status") == ["failed"]
            for path, query in organization_requests
            if path.endswith("/analytics")
        ),
        page,
        "workspace status request",
    )
    wait_until(
        lambda: any(
            query.get("status") == ["failed"]
            and "date_to_exclusive" in query
            and "date_to" not in query
            for path, query in organization_requests
            if "date_from" in query
        ),
        page,
        "recent calls status request",
    )

    main.get_by_label("Call reporting period").select_option("yesterday")
    wait_until(
        lambda: any(
            query.get("period") == ["yesterday"]
            for path, query in organization_requests
            if path.endswith("/analytics")
        ),
        page,
        "workspace calendar-day request",
    )
    main.get_by_label("Call reporting period").select_option("last_30_days")
    main.get_by_label("Call status filter").select_option("")
    wait_until(
        lambda: any(
            query.get("status") is None
            for path, query in organization_requests
            if path.endswith("/analytics")
        ),
        page,
        "workspace all-status request",
    )
    page.unroute(org_pattern)

    def fail_analytics(route: Route):
        if urlsplit(route.request.url).path.endswith("/analytics"):
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": "Call analytics unavailable"}),
            )
        else:
            route.continue_()

    page.route(org_pattern, fail_analytics)
    main.get_by_role("button", name="Refresh call data").click()
    expect(main.get_by_role("alert")).to_be_visible(timeout=20000)
    expect(main.get_by_role("heading", name="Recent calls")).to_be_visible()
    expect(main.get_by_text("Avg. call duration", exact=True)).to_have_count(0)
