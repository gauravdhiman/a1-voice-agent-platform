import pytest
import os
import re
from playwright.sync_api import BrowserContext, Page

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("E2E_BASE_URL", "http://localhost:3001")

@pytest.fixture
def step(page: Page, request):
    """Fixture to log steps to the report and console."""
    if not hasattr(request.node, "steps"):
        request.node.steps = []
        
    def _step(description: str):
        # Store step for report injection
        request.node.steps.append(description)
        # Print for console output
        print(f"\n[STEP] {description}")
        # Add to browser console
        try:
            page.evaluate(f"console.log('E2E_STEP: {description}')")
        except:
            pass
    return _step

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hooks into report generation to inject custom steps."""
    outcome = yield
    report = outcome.get_result()
    
    # Check if this is the "call" phase (when the test actually runs)
    if report.when == "call":
        # Get the steps from the test item
        steps = getattr(item, "steps", [])
        if steps:
            # Format steps as a bulleted list for the HTML report
            html_steps = "<div style='margin-top: 10px; font-family: sans-serif;'>"
            html_steps += "<strong>User Journey Path:</strong>"
            html_steps += "<ul style='list-style: none; padding-left: 5px;'>"
            
            for i, s in enumerate(steps):
                is_last = (i == len(steps) - 1)
                if report.failed and is_last:
                    symbol = "<span style='color: #ef4444; font-weight: bold;'>✕</span>"
                    style = "color: #ef4444; font-weight: bold; background: #fee2e2; padding: 2px 5px; border-radius: 3px;"
                else:
                    symbol = "<span style='color: #22c55e;'>✓</span>"
                    style = "color: #374151;"
                
                html_steps += f"<li style='margin-bottom: 5px; {style}'>{symbol} {s}</li>"
            
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

    page.route("**/auth/v1/user**", lambda route: route.fulfill(
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
    ))

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

@pytest.fixture(autouse=True)
def apply_mocks(page: Page):
    """Automatically apply boundary mocks to every page."""
    setup_boundary_mocks(page)
    yield
