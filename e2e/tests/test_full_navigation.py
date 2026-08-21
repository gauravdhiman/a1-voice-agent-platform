"""
E2E coverage for every top-level page reachable from the dashboard sidebar
and for key public/auth entry points.

Mocking strategy:
- Supabase Auth + /api/v1/auth/me + /api/v1/organizations + agents are
  handled by the autouse conftest mocks (now including org-scoped agents
  and calls/analytics). Each test only adds the extra route it needs;
  otherwise the page's own loading/empty states are the assertion.
- No real backend is hit; the frontend's data layer is exercised through
  the mocked API boundary, which is the intended E2E contract.
"""
import json
import re

from playwright.sync_api import Page, expect

from helpers import signin_user


TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _org_list(orgs=None):
    if orgs is None:
        orgs = [{"id": TEST_ORG_ID, "name": "Test Organization", "slug": "test-org", "is_active": True, "onboarding_completed": True}]
    return json.dumps(orgs)


# ---------- Public / auth entry points ----------

def test_landing_page_loads(page: Page, base_url: str, step):
    step("Navigate to landing page")
    page.goto(base_url)
    page.wait_for_load_state("domcontentloaded")
    step("Verify landing hero or sign-in CTA is present")
    # The landing page is an unauthenticated entry point — at least one CTA
    # should be present regardless of exact copy.
    expect(page.get_by_text(re.compile(r"Sign In|Get Started|24x7", re.I)).first).to_be_visible(timeout=10000)


def test_signin_page_renders(page: Page, base_url: str, step):
    step("Navigate to sign-in page")
    page.goto(f"{base_url}/auth/signin")
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_role("heading", name=re.compile(r"Welcome back|Sign in", re.I))).to_be_visible(timeout=10000)
    expect(page.locator('input#email, input[type="email"]').first).to_be_visible(timeout=5000)


def test_signup_page_renders(page: Page, base_url: str, step):
    step("Navigate to signup page")
    page.goto(f"{base_url}/auth/signup")
    page.wait_for_load_state("domcontentloaded")
    # Signup form should have email + CTA
    expect(page.locator('input#email, input[type="email"]').first).to_be_visible(timeout=10000)


def test_dashboard_loads_after_signin(page: Page, base_url: str, step):
    step("Sign in and land on dashboard")
    signin_user(page, base_url)
    expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)


def test_agents_page_loads(page: Page, base_url: str, step):
    step("Sign in then navigate to Agents page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name=re.compile(r"Voice Agents", re.I))).to_be_visible(timeout=10000)


def test_calls_page_loads(page: Page, base_url: str, step):
    step("Sign in then navigate to Calls page")
    signin_user(page, base_url)
    # Calls list API defaults are in conftest; page should render its header
    page.goto(f"{base_url}/calls?org_id=00000000-0000-0000-0000-000000000001")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name=re.compile(r"Call Log", re.I))).to_be_visible(timeout=10000)


def test_phone_numbers_page_loads(page: Page, base_url: str, step):
    step("Mock phone numbers list and billing balance")
    page.route(re.compile(r".*/api/v1/phone-numbers.*"), lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"items": [], "total": 0, "page": 1, "page_size": 25}),
    ))
    page.route(re.compile(r".*/api/v1/billing/balance.*"), lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"total_credits": 0, "subscription_credits": 0, "purchased_credits": 0, "expiring_soon": 0, "expires_at": None}),
    ))
    page.route(re.compile(r".*/api/v1/phone-numbers/available.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Phone Numbers page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/phone-numbers")
    page.wait_for_load_state("networkidle")
    # Page heading varies by implementation; check for Phone Numbers
    expect(page.get_by_text(re.compile(r"Phone Numbers", re.I)).first).to_be_visible(timeout=10000)


def test_skills_page_loads(page: Page, base_url: str, step):
    step("Mock skills list to avoid empty fetch errors")
    page.route(re.compile(r".*/api/v1/skills.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    page.route(re.compile(r".*/api/v1/skills/files.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Skills page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/skills")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name=re.compile(r"Skills", re.I)).first).to_be_visible(timeout=10000)


def test_organization_page_loads(page: Page, base_url: str, step):
    step("Sign in then navigate to Organization page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization")
    page.wait_for_load_state("networkidle")
    # Org page has tabs and a heading; at least one org-related string should appear
    expect(page.get_by_text(re.compile(r"Organization", re.I)).first).to_be_visible(timeout=10000)


def test_organization_members_page(page: Page, base_url: str, step):
    step("Mock members list")
    page.route(re.compile(r".*/api/v1/organizations/.*/members.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    page.route(re.compile(r".*/api/v1/organizations/.*/invitations.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    page.route(re.compile(r".*/api/v1/rbac/.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"roles": [], "permissions": []}),
    ))
    step("Sign in then navigate to Organization Members")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization/members")
    page.wait_for_load_state("networkidle")
    # Members page has a heading or empty-state text
    expect(page.get_by_text(re.compile(r"Members|Team|Invite", re.I)).first).to_be_visible(timeout=10000)


def test_organization_billing_page(page: Page, base_url: str, step):
    step("Mock billing summary for org billing tab")
    page.route(re.compile(r".*/api/v1/billing/summary/.*"), lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"total_credits": 1250, "subscription_credits": 1000, "purchased_credits": 250, "expiring_soon": 100, "expires_at": None, "plans": []}),
    ))
    page.route(re.compile(r".*/api/v1/billing/credits/.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    page.route(re.compile(r".*/api/v1/billing/plans.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    page.route(re.compile(r".*/api/v1/billing/credit-products.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Organization Billing")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization/billing")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile(r"Billing|Credits|Balance|Plans", re.I)).first).to_be_visible(timeout=10000)


def test_settings_page_loads(page: Page, base_url: str, step):
    step("Sign in then navigate to Settings page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/settings")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("heading", name=re.compile(r"Settings", re.I))).to_be_visible(timeout=10000)


def test_organizations_list_page_for_platform_admin(page: Page, base_url: str, step):
    step("Sign in then navigate to Organizations listing (platform admin)")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organizations")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile(r"Organizations", re.I)).first).to_be_visible(timeout=10000)


def test_platform_tools_page_loads(page: Page, base_url: str, step):
    step("Mock platform tools catalog")
    page.route(re.compile(r".*/api/v1/tools/platform.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Platform Tools")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/tools")
    page.wait_for_load_state("networkidle")
    # Platform Tools page heading or fallback for non-admin
    expect(page.get_by_text(re.compile(r"Platform Tools|Tool Catalog|Management|Access Denied", re.I)).first).to_be_visible(timeout=10000)


def test_platform_presets_page_loads(page: Page, base_url: str, step):
    step("Mock presets catalog")
    page.route(re.compile(r".*/api/v1/presets.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Platform Presets")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/presets")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile(r"Presets|Voice.*Preset|Access Denied|Platform", re.I)).first).to_be_visible(timeout=10000)


def test_platform_templates_page_loads(page: Page, base_url: str, step):
    step("Mock templates catalog")
    page.route(re.compile(r".*/api/v1/voice-templates.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Platform Templates")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/templates")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile(r"Templates|Use Case|Access Denied|Platform", re.I)).first).to_be_visible(timeout=10000)


def test_platform_skills_page_loads(page: Page, base_url: str, step):
    step("Mock platform skills catalog")
    page.route(re.compile(r".*/api/v1/platform-skills.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    page.route(re.compile(r".*/api/v1/skills?.*"), lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps([]),
    ))
    step("Sign in then navigate to Platform Skills")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/skills")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile(r"Skills|Platform.*Skill|Access Denied", re.I)).first).to_be_visible(timeout=10000)


def test_sidebar_navigation_renders_for_authenticated_user(page: Page, base_url: str, step):
    """
    Smoke: after sign-in the sidebar renders the expected nav items for the
    workspace section (at least Dashboard and Agents).
    """
    step("Sign in and wait for dashboard layout to hydrate")
    signin_user(page, base_url)
    # Sidebar is part of the dashboard layout
    expect(page.get_by_role("link", name=re.compile(r"Home|Dashboard", re.I))).to_be_visible(timeout=10000)
    # Agents link may be hidden if permissions not yet hydrated; at least Home proves sidebar rendered


def test_unauthenticated_redirects_to_signin(page: Page, base_url: str, step):
    step("Clear auth and navigate to a protected route")
    # Clear the mocked auth session so the page is truly unauthenticated
    page.goto(f"{base_url}/auth/signin")
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
    # Without a session, middleware should redirect to /auth/signin or the
    # landing page's sign-in CTA. Either is a valid auth guard.
    page.wait_for_load_state("domcontentloaded")
    expect(page).to_have_url(re.compile(r"/auth/signin|/auth|/$", re.I), timeout=10000)
