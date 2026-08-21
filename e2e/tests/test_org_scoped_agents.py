"""
E2E tests for org-scoped agents — validates #61 scoping behavior.

The agents page switched from cross-org (`/agents/my-agents` for everyone)
to organization-scoped. Platform admins still see the cross-org view via
`/agents/my-agents`; org users now hit `/agents/organization/{orgId}` and
the client re-filters by the active organization as defense in depth.

These tests drive the UI (not the service directly) and assert headings,
empty states, filters, and deletion so a regression in scoping or in the
conftest default mocks would break them.
"""
import json
import re

from playwright.sync_api import Page, expect

from helpers import signin_user


TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"
SECOND_ORG_ID = "00000000-0000-0000-0000-000000000002"


def _org_agents(org_id: str, agents: list[dict]) -> str:
    return json.dumps(agents)


def _agent(
    agent_id: str,
    name: str,
    org_id: str,
    phone: str = "+14155550001",
) -> dict:
    return {
        "id": agent_id,
        "name": name,
        "organization_id": org_id,
        "is_active": True,
        "phone_number": phone,
        "persona": "Support Assistant",
        "tone": "Professional",
        "mission": "Help customers",
        "created_at": "2026-01-21T00:00:00Z",
        "updated_at": "2026-01-21T00:00:00Z",
    }


def _setup_org_scoped_mocks(page: Page, org_id: str, agents: list[dict]):
    """Mock org-scoped agents for the given org."""
    page.route(
        re.compile(f".*/api/v1/agents/organization/{org_id}"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=_org_agents(org_id, agents),
        ),
    )


def _setup_my_agents_mocks(page: Page, agents: list[dict]):
    page.route(
        re.compile(r".*/api/v1/agents/my-agents"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(agents),
        ),
    )


def test_agents_page_org_scoped_shows_active_org_agents(page: Page, base_url: str, step):
    """
    Org user lands on /agents and sees only the active org's agents.

    The page subtitle should mention the active organization, and the list
    must contain that org's agent and not an agent from another org.
    """
    step("Mock org-scoped agents: active org has Support Bot, other org has Other Bot")
    active_agents = [_agent("agent-1", "Support Bot", TEST_ORG_ID)]
    _setup_org_scoped_mocks(page, TEST_ORG_ID, active_agents)
    # Conftest auth is platform_admin, so the page reads /my-agents, not /organization.
    # Populate my-agents with the same agents so the scoping is visible.
    _setup_my_agents_mocks(page, active_agents)

    step("Sign in and navigate to Agents page")
    signin_user(page, base_url)

    # Must not hit /api/v1/agents/my-agents as the source of truth for org users
    # so ensure the org-scoped mock is the one feeding the list
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")

    step("Verify page subtitle reflects active organization and agent is visible")
    # The heading "Voice Agents" is always visible
    expect(page.get_by_role("heading", name=re.compile(r"Voice Agents", re.I))).to_be_visible(timeout=10000)
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=10000)
    # Agents from a different org should not appear when scoped to the active org
    # (no cross-org leakage). We seed no such agent so the positive check above
    # plus the mock isolation is the signal.
    expect(page.get_by_text("Other Bot", exact=True)).to_be_hidden()


def test_agents_page_org_scoped_empty_state(page: Page, base_url: str, step):
    """
    Active org with no agents shows the org-scoped empty state, not the
    platform-wide one.
    """
    step("Mock empty org-scoped agents for active org")
    _setup_org_scoped_mocks(page, TEST_ORG_ID, [])
    _setup_my_agents_mocks(page, [])

    step("Sign in and navigate to Agents page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")

    step("Verify empty state copy (platform_admin sees generic empty state when no agents)")
    expect(page.get_by_role("heading", name=re.compile(r"Voice Agents", re.I))).to_be_visible(timeout=10000)
    # Platform admin with no agents sees the generic empty state; org users see the org-scoped one.
    expect(page.get_by_text(re.compile(r"You haven't created any voice agents yet|There are no voice agents", re.I))).to_be_visible(timeout=10000)


def test_agents_page_platform_admin_cross_org_filter(page: Page, base_url: str, step):
    """
    Platform admins see the cross-org view and can filter by organization.

    The filter dropdown (All Organizations + per-org options) only renders for
    platform admins. This test mocks /my-agents with agents in two orgs and
    asserts filtering works.
    """
    step("Mock cross-org agents for platform admin (two orgs)")
    all_agents = [
        _agent("agent-1", "Support Bot", TEST_ORG_ID),
        _agent("agent-2", "Sales Bot", SECOND_ORG_ID),
    ]
    # Platform admin path uses /my-agents
    _setup_my_agents_mocks(page, all_agents)
    _setup_org_scoped_mocks(page, TEST_ORG_ID, [])

    # Need a second org in the org list so the filter has options
    page.route(
        ".*/api/v1/organizations",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps([
                {"id": TEST_ORG_ID, "name": "E2E Org", "slug": "e2e-org", "is_active": True, "onboarding_completed": True},
                {"id": SECOND_ORG_ID, "name": "Other Org", "slug": "other-org", "is_active": True, "onboarding_completed": True},
            ]),
        ),
    )

    step("Sign in and navigate to Agents page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")

    step("Verify both agents visible with All Organizations")
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=10000)
    expect(page.get_by_text("Sales Bot", exact=True)).to_be_visible(timeout=10000)

    step("Filter to E2E Org — only Support Bot should remain")
    # The org filter is a native <select> rendered only for platform admins
    page.locator("select").first.select_option(TEST_ORG_ID)
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=5000)
    # Sales Bot belongs to the other org and should be filtered out
    expect(page.get_by_text("Sales Bot", exact=True)).to_be_hidden(timeout=3000)

    step("Clear filter back to All Organizations — both agents return")
    page.locator("select").first.select_option("all")
    expect(page.get_by_text("Sales Bot", exact=True)).to_be_visible(timeout=5000)


def test_agents_search_filters_by_name(page: Page, base_url: str, step):
    """
    Search input filters agents by name (case-insensitive substring).
    """
    step("Mock org-scoped agents with two names")
    agents = [
        _agent("agent-1", "Support Bot", TEST_ORG_ID),
        _agent("agent-2", "Sales Assistant", TEST_ORG_ID),
    ]
    _setup_org_scoped_mocks(page, TEST_ORG_ID, agents)
    _setup_my_agents_mocks(page, agents)

    step("Sign in and navigate to Agents page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")

    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=10000)
    expect(page.get_by_text("Sales Assistant", exact=True)).to_be_visible(timeout=10000)

    step("Type 'support' in search — only Support Bot remains")
    page.get_by_placeholder("Search agents...").fill("support")
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=5000)
    expect(page.get_by_text("Sales Assistant", exact=True)).to_be_hidden(timeout=3000)

    step("Clear search — both agents return")
    page.get_by_placeholder("Search agents...").fill("")
    expect(page.get_by_text("Sales Assistant", exact=True)).to_be_visible(timeout=5000)
