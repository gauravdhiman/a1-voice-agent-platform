import pytest
import os
import re
from playwright.sync_api import BrowserContext, Page

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("E2E_BASE_URL", "http://localhost:3000")

def setup_comprehensive_mocks(page: Page):
    """Intercepts Supabase and Backend API calls to simulate success."""
    print(f"DEBUG: Setting up comprehensive mocks for {page}")
    
    # Fixed test IDs
    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"

    # 1. Mock Supabase Auth
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

    # 2. Mock Backend API
    # Mock Auth Me
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
            "roles": []
        }}'''
    ))

    # Mock Organization Retrieval
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "Mock Org", "slug": "mock-org"}}]'
    ))

    # Mock Organization Creation
    page.route("**/api/v1/organizations/self", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'{{"id": "{test_org_id}", "name": "Mock Org", "slug": "mock-org"}}'
    ))

@pytest.fixture(autouse=True)
def apply_mocks(page: Page):
    """Automatically apply mocks to every page in every test."""
    setup_comprehensive_mocks(page)
    yield
