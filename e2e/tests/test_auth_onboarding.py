import pytest
import re
import uuid
from playwright.sync_api import Page, expect

def test_full_onboarding_journey(page: Page, base_url: str, step):
    """
    Test the full user journey from Signup to Dashboard.
    Ensures that for a new user, the Organization Creation flow is triggered.
    """
    
    test_id = str(uuid.uuid4())[:8]
    email = f"newuser_{test_id}@gmail.com"
    password = "Password123!"
    org_name = f"New Org {test_id}"

    # 1. Signup
    step("Setup: Override /me mock to return a new user with no roles")
    test_user_id = "00000000-0000-0000-0000-000000000000"
    page.route("**/api/v1/auth/me", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{test_user_id}",
            "email": "{email}",
            "first_name": "Test",
            "last_name": "User",
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z",
            "roles": []
        }}'''
    ))

    step("Navigate to Signup page")
    page.goto(f"{base_url}/auth/signup")
    
    step(f"Fill signup form for {email}")
    page.fill('input#firstName', "Test")
    page.fill('input#lastName', "User")
    page.fill('input#email', email)
    page.fill('input#password', password)
    page.click('button[type="submit"]')

    step("Verify signup success message")
    expect(page.get_by_text(re.compile(r"Account created|check your email", re.I))).to_be_visible(timeout=5000)
    
    # 2. Sign In
    step("Navigate to Signin page")
    page.goto(f"{base_url}/auth/signin")
    
    step(f"Sign in with {email}")
    page.fill('input#email', email)
    page.fill('input#password', password)
    page.click('button[type="submit"]')
    
    # 3. Organization Creation (This MUST happen for a new user in a fresh DB)
    step("Verify redirection to Organization Creation page")
    expect(page).to_have_url(re.compile(r".*/create-organization"), timeout=10000)
    
    step(f"Create organization: {org_name}")
    page.fill('input#name', org_name)
    page.click('button[type="submit"]')
    
    # 4. Verify Dashboard
    step("Verify final redirection to Dashboard")
    expect(page).to_have_url(re.compile(r".*/dashboard"), timeout=15000)
    expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)
    
    step("Verify organization name appears in the UI")
    expect(page.get_by_text(org_name)).to_be_visible()

def test_signin_validation_journey(page: Page, base_url: str, step):
    """Test signin form validation and error handling."""
    
    step("Setup: Override signin mock to fail")
    page.route("**/auth/v1/token**", lambda route: route.fulfill(
        status=401,
        content_type="application/json",
        body='{"error": "invalid_grant", "error_description": "Invalid login credentials"}'
    ))

    step("Navigate to Signin page")
    page.goto(f"{base_url}/auth/signin")
    
    step("Submit invalid credentials")
    page.fill('input#email', "wrong@example.com")
    page.fill('input#password', "wrongpassword")
    page.click('button[type="submit"]')
    
    step("Verify error alert is shown")
    expect(page.locator('div[role="alert"]').get_by_text(re.compile(r"invalid|failed|error|credentials", re.I))).to_be_visible()
