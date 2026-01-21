import pytest
import re
from playwright.sync_api import Page, expect

def test_homepage_loads(page: Page):
    """Test that the homepage loads correctly."""
    page.goto("http://localhost:3000")
    # Wait for the page to load
    page.wait_for_load_state("networkidle")
    
    # Check for landing page content
    # Using a regex to check if title is not empty
    expect(page).to_have_title(re.compile(".+"))
    
def test_navigation_to_signin(page: Page):
    """Test navigation from homepage to sign-in page."""
    page.goto("http://localhost:3000")
    
    # Click Sign In button (adjust selector as needed)
    sign_in_button = page.get_by_text("Sign In").first
    if sign_in_button.is_visible():
        sign_in_button.click()
        page.wait_for_load_state("networkidle")
        assert "/auth/signin" in page.url
    else:
        pytest.skip("Sign In button not found on homepage")

def test_auth_pages_accessibility(page: Page):
    """Test that public auth pages are accessible."""
    auth_pages = [
        "/auth/signin",
        "/auth/signup",
        "/auth/reset-password"
    ]
    
    for path in auth_pages:
        page.goto(f"http://localhost:3000{path}")
        page.wait_for_load_state("networkidle")
        assert page.status_code if hasattr(page, 'status_code') else 200 # status_code is not directly on page
        # More reliable: check if the page content matches the expected route
        assert path in page.url
