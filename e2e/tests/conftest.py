import pytest
import os
import re
from playwright.sync_api import BrowserContext, Page

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("E2E_BASE_URL", "http://localhost:3001")

@pytest.fixture
def step(page: Page, request):
    """Fixture to log steps to the report and console with enhanced formatting."""
    if not hasattr(request.node, "steps"):
        request.node.steps = []
        
    def _step(description: str):
        import time
        
        step_time = time.strftime("%H:%M:%S")
        # Store step for report injection with timestamp
        request.node.steps.append({"description": description, "time": step_time})
        # Print for console output with timestamp
        print(f"\n[STEP {step_time}] {description}")
        # Add to browser console with timestamp
        try:
            page.evaluate(f"console.log('[E2E {step_time}] {description}')")
        except:
            pass
    return _step

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hooks into report generation to inject custom steps with enhanced formatting."""
    outcome = yield
    report = outcome.get_result()
    
    # Check if this is the "call" phase (when the test actually runs)
    if report.when == "call":
        # Get the steps from the test item
        steps = getattr(item, "steps", [])
        if steps:
            # Format steps as a bulleted list for the HTML report with timestamps
            html_steps = "<div style='margin-top: 10px; font-family: sans-serif;'>"
            html_steps += "<strong>User Journey Path:</strong>"
            html_steps += "<ul style='list-style: none; padding-left: 5px; background: #f9fafb; border-radius: 6px; padding: 10px;'>"
            
            for i, step_data in enumerate(steps):
                # Handle both old format (string) and new format (dict)
                if isinstance(step_data, str):
                    step_desc = step_data
                    step_time = ""
                else:
                    step_desc = step_data.get("description", "")
                    step_time = step_data.get("time", "")
                
                is_last = (i == len(steps) - 1)
                if report.failed and is_last:
                    symbol = "<span style='color: #ef4444; font-weight: bold;'>✕</span>"
                    style = "color: #ef4444; font-weight: bold; background: #fee2e2; padding: 4px 8px; border-radius: 4px; margin-bottom: 4px;"
                else:
                    symbol = "<span style='color: #22c55e;'>✓</span>"
                    style = "color: #374151; margin-bottom: 4px;"
                
                time_badge = f"<span style='color: #6b7280; font-size: 11px; margin-left: 8px;'>[{step_time}]</span>" if step_time else ""
                html_steps += f"<li style='{style}'><span style='display: inline-block; min-width: 20px;'>{i + 1}.</span> {symbol} {step_desc}{time_badge}</li>"
            
            html_steps += "</ul></div>"
            
            # Inject into the report's extra section
            pytest_html = item.config.pluginmanager.getplugin("html")
            if pytest_html:
                extra = getattr(report, "extra", [])
                extra.append(pytest_html.extras.html(html_steps))
                report.extra = extra

def setup_boundary_mocks(page: Page):
    """Intercepts EXTERNAL boundaries only (Supabase Auth) and suppresses the product tour.

    The dashboard product tour (react-joyride) auto-starts on first login and
    overlays the page with a spotlight that intercepts pointer events. Without
    suppression every E2E click inside signin_user or the test itself would be
    swallowed. We seed localStorage so readProductTourStatus returns a terminal
    value before the provider mounts.
    """

    # Suppress the product tour for every role the E2E user might have
    test_user_id = "00000000-0000-0000-0000-000000000000"
    page.add_init_script(
        """(function () {
            const userId = '00000000-0000-0000-0000-000000000000';
            const version = 'v1';
            const roles = ['member', 'org_admin', 'platform_admin'];
            const branches = ['main', 'agents', 'calls', 'skills', 'agent-details'];
            // The actual keys are 24x7-ai.product-tour.v1.<role>.<userId>[.<branch>]
            // We seed every role so the mocks in this file can't get out of sync
            // with the tour's role resolution.
            for (const role of roles) {
                const base = `24x7-ai.product-tour.${version}.${role}.${userId}`;
                for (const branch of branches) {
                    const key = branch === 'main' ? base : `${base}.${branch}`;
                    try { localStorage.setItem(key, 'completed'); } catch (_) {}
                }
            }
        })();"""
    )

    page.route(re.compile(r".*/auth/v1/signup.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'{{"user": {{"id": "{test_user_id}", "email": "test@gmail.com"}}, "session": null}}'
    ))

    def handle_token(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=f'''{{
                "access_token": "mock-jwt-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "mock-refresh-token",
                "user": {{
                    "id": "{test_user_id}",
                    "email": "test@gmail.com",
                    "app_metadata": {{"provider": "email"}},
                    "user_metadata": {{"first_name": "Test", "last_name": "User"}},
                    "aud": "authenticated",
                    "role": "authenticated"
                }}
            }}'''
        )
    page.route(re.compile(r".*/auth/v1/token.*"), handle_token)

    def handle_user_request(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=f'''{{
                "id": "{test_user_id}",
                "email": "test@gmail.com",
                "aud": "authenticated",
                "role": "authenticated",
                "app_metadata": {{"provider": "email"}},
                "user_metadata": {{"first_name": "Test", "last_name": "User"}}
            }}'''
        )

    page.route(re.compile(r".*/auth/v1/user.*"), handle_user_request)

    # 2. Mock /api/v1/auth/me (Bridges external user to backend)
    # We mock this because it's the very first call and ensures the user exists for the FE
    page.route(re.compile(r".*/api/v1/auth/me.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{test_user_id}",
            "email": "test@gmail.com",
            "first_name": "Test",
            "last_name": "User",
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z",
            "roles": [
                {{
                    "id": "role-1",
                    "user_id": "{test_user_id}",
                    "role_id": "platform-admin-id",
                    "organization_id": null,
                    "role": {{
                        "id": "platform-admin-id",
                        "name": "platform_admin",
                        "description": "Admin",
                        "is_system_role": true,
                        "permissions": [
                            {{"id": "p1", "name": "agents:write", "resource": "agents", "action": "write"}},
                            {{"id": "p2", "name": "agents:read", "resource": "agents", "action": "read"}}
                        ]
                    }}
                }}
            ],
            "current_organization_id": "00000000-0000-0000-0000-000000000001",
            "permissions": {{"*": ["*"]}},
            "has_organizations": true
        }}'''
    ))

    # 2b. Mock /api/v1/auth/signin — the actual sign-in endpoint the UI calls.
    #     auth-service.ts posts {email, password} and expects {access_token, refresh_token}.
    #     Without this mock the UI shows "An unexpected error occurred".
    def handle_signin(route):
        # Simulate credential check: only the E2E test credentials succeed
        try:
            body = route.request.post_data_json or {}
        except Exception:
            body = {}
        # Accept both the conftest test user and any test@gmail path the helpers use
        if body.get("email") in ("test@gmail.com", "test@cogninets.local", "test@247ai.local"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=f'''{{
                    "access_token": "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMC0wMDAwMDAwMDAwMDAwIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjo5OTk5OTk5OTk5fQ.c2lnbmF0dXJl",
                    "refresh_token": "mock-refresh-token-e2e",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "user": {{
                        "id": "{test_user_id}",
                        "email": "test@gmail.com",
                        "first_name": "Test",
                        "last_name": "User",
                        "created_at": "2026-01-21T00:00:00Z",
                        "updated_at": "2026-01-21T00:00:00Z",
                        "roles": []
                    }}
                }}'''
            )
        else:
            route.fulfill(
                status=400,
                content_type="application/json",
                body='{"detail": {"message": "Invalid credentials", "code": "invalid_credentials"}}'
            )

    page.route(re.compile(r".*/api/v1/auth/signin.*"), handle_signin)

    # 2b2. Mock check-email — called on blur of email field; without it the
    #     form shows inline validation errors and the CORS 404 confuses setSession
    page.route(re.compile(r".*/api/v1/auth/check-email.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"exists": true, "sign_in_methods": ["password"], "message": null}'
    ))

    # 2c. Mock Supabase setSession via /auth/v1/token?grant_type=refresh_token
    #     After backend signin, the frontend calls supabase.auth.setSession with the
    #     tokens. In E2E those tokens are mocked JWTs; we intercept the underlying
    #     Supabase REST call that setSession triggers.
    # 3. Mock /api/v1/organizations (Required for OrganizationCheck component)
    # This is needed for the dashboard to load properly after sign-in
    test_org_id = "00000000-0000-0000-0000-000000000001"
    page.route(re.compile(r".*/api/v1/organizations.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''[{{
            "id": "{test_org_id}",
            "name": "Test Organization",
            "slug": "test-org",
            "is_active": true,
            "onboarding_completed": true
        }}]'''
    ))

    # 4. Mock /api/v1/agents/my-agents (platform_admin cross-org view)
    page.route(re.compile(r".*/api/v1/agents/my-agents.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[]'''
    ))

    # 5. Mock /api/v1/agents/organization/.* (org-scoped agents — new in #61)
    #    The agents page now uses the active org for non-platform users.
    #    Keep this alongside my-agents so both roles resolve.
    page.route(re.compile(r".*/api/v1/agents/organization/.*"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[]'''
    ))

    # 6. Mock common dashboard hydration endpoints so page loads do not 404.
    #    Safe defaults; individual tests override with specific data.
    # Generic calls mock covering both list (/calls/organization/{id}) and analytics
    # so dashboard + calls page do not 404/CORS when conftest is the only mock.
    # Tests that need specific calls data override with their own page.route before signin.
    def _handle_calls(route):
        url = route.request.url
        if "analytics" in url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='''{"total_calls_week": 0, "total_calls_month": 0, "avg_duration_seconds": 0, "calls_by_status": [], "calls_by_hour": [], "calls_by_agent": []}'''
            )
        else:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='''{"items": [], "total": 0, "page": 1, "page_size": 25, "total_pages": 0}'''
            )
    page.route(re.compile(r".*/api/v1/calls.*"), _handle_calls)

@pytest.fixture(autouse=True)
def apply_mocks(page: Page):
    """Automatically apply boundary mocks to every page."""
    setup_boundary_mocks(page)
    yield
