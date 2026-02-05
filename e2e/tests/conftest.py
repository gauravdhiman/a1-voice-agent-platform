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
    """Intercepts EXTERNAL boundaries only (Supabase Auth)."""
    
    # Fixed test user ID matching init-test-db.sql
    test_user_id = "00000000-0000-0000-0000-000000000000"

    # 1. Mock Supabase Auth (External Service)
    page.route("**/auth/v1/signup**", lambda route: route.fulfill(
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
    page.route("**/auth/v1/token**", handle_token)

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

    page.route("**/auth/v1/user**", handle_user_request)

    # 2. Mock /api/v1/auth/me (Bridges external user to backend)
    # We mock this because it's the very first call and ensures the user exists for the FE
    page.route("**/api/v1/auth/me", lambda route: route.fulfill(
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
            ]
        }}'''
    ))

    # 3. Mock /api/v1/organizations (Required for OrganizationCheck component)
    # This is needed for the dashboard to load properly after sign-in
    test_org_id = "00000000-0000-0000-0000-000000000001"
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''[{{
            "id": "{test_org_id}",
            "name": "Test Organization",
            "slug": "test-org",
            "is_active": true
        }}]'''
    ))

    # 4. Mock /api/v1/agents/my-agents (Required for dashboard agents list)
    page.route("**/api/v1/agents/my-agents", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[]'''
    ))

@pytest.fixture(autouse=True)
def apply_mocks(page: Page):
    """Automatically apply boundary mocks to every page."""
    setup_boundary_mocks(page)
    yield
