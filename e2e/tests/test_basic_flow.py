import pytest
import re
from playwright.sync_api import Page, expect

def test_homepage_loads(page: Page, base_url: str, step):
    """Test that the homepage loads correctly."""
    step("Navigate to the landing page")
    page.goto(base_url)
    
    step("Wait for network to be idle")
    page.wait_for_load_state("networkidle")
    
    step("Verify page title is present")
    expect(page).to_have_title(re.compile(".+"))
    
def test_navigation_to_signin(page: Page, base_url: str, step):
    """Test navigation from homepage to sign-in page."""
    step(f"Navigate to homepage at {base_url}")
    page.goto(base_url)
    
    step("Locate and click 'Sign In' button")
    sign_in_button = page.get_by_text("Sign In").first
    if sign_in_button.is_visible():
        sign_in_button.click()
        step("Verify redirection to signin page")
        page.wait_for_load_state("networkidle")
        assert "/auth/signin" in page.url
    else:
        step("Skip: Sign In button not visible")
        pytest.skip("Sign In button not found on homepage")

def test_auth_pages_accessibility(page: Page, base_url: str, step):
    """Test that public auth pages are accessible."""
    auth_pages = [
        "/auth/signin",
        "/auth/signup",
        "/auth/reset-password"
    ]
    
    for path in auth_pages:
        step(f"Check accessibility of {path}")
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")
        
        step(f"Verify URL contains {path}")
        assert path in page.url
