import pytest
import re
import uuid
from playwright.sync_api import Page, expect

import pytest
import re
import uuid
from playwright.sync_api import Page, expect

def test_full_onboarding_flow(page: Page, base_url: str):
    # 1. Sign Up
    page.goto(f"{base_url}/auth/signup")
    
    test_id = str(uuid.uuid4())[:8]
    email = f"testuser_{test_id}@gmail.com"
    password = "Password123!"
    
    page.fill('input#firstName', "Test")
    page.fill('input#lastName', "User")
    page.fill('input#email', email)
    page.fill('input#password', password)
    page.click('button[type="submit"]')

    # Check for success message
    expect(page.get_by_text(re.compile(r"Account created|check your email", re.I))).to_be_visible(timeout=5000)
    
    # 2. Sign In
    print(f"DEBUG: Proceeding to sign in with {email}")
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', email)
    page.fill('input#password', password)
    page.click('button[type="submit"]')
    
    # Wait for navigation
    page.wait_for_timeout(3000)
    
    print(f"DEBUG: URL after sign in: {page.url}")
    
    # 3. Organization Creation (if prompted)
    if "/auth/create-organization" in page.url:
        print("DEBUG: Creating organization")
        page.fill('input#name', f"Test Org {test_id}")
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)

    # 4. Verify Dashboard
    print(f"DEBUG: Final URL: {page.url}")
    expect(page).to_have_url(re.compile(r".*(dashboard|organization)"), timeout=15000)
    expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)

def test_signin_validation(page: Page, base_url: str):
    """Test signin form validation and error handling."""
    
    # Override signin mock to fail for this test
    page.route("**/auth/v1/token**", lambda route: route.fulfill(
        status=401,
        content_type="application/json",
        body='{"error": "invalid_grant", "error_description": "Invalid login credentials"}'
    ))

    page.goto(f"{base_url}/auth/signin")
    
    # Fill with dummy data
    page.fill('input#email', "wrong@example.com")
    page.fill('input#password', "wrongpassword")
    page.click('button[type="submit"]')
    
    # Verify error message using a more specific locator to avoid strict mode violations
    expect(page.locator('div[role="alert"]').get_by_text(re.compile(r"invalid|failed|error|credentials", re.I))).to_be_visible()

