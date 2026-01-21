import pytest
import re
from playwright.sync_api import Page, expect


def test_homepage_loads(page: Page, base_url: str, step):
    """
    Test that the application homepage loads successfully.

    Purpose:
        Verify basic application accessibility by ensuring the landing page
        loads correctly without errors.

    Test Specification:
        1. Navigate to application base URL
        2. Wait for page to reach DOMContentLoaded state
        3. Verify page has a title element (non-empty)

    Mocks Required:
        - None (tests actual frontend rendering)

    Expected Behavior:
        - Homepage loads without errors
        - Page has a non-empty title

    Dependencies:
        - None (no authentication required)
    """

    step("Navigate to landing page")
    page.goto(base_url)

    step("Wait for page to load")
    page.wait_for_load_state("domcontentloaded")

    step("Verify page title is present")
    expect(page).to_have_title(re.compile(".+"))


def test_navigation_to_signin(page: Page, base_url: str, step):
    """
    Test navigation from homepage to sign-in page.

    Purpose:
        Verify that users can navigate from homepage to
        sign-in page using the "Sign In" button.

    Test Specification:
        1. Navigate to application homepage
        2. Wait for page to fully load
        3. Verify "Sign In" button is visible
        4. Click "Sign In" button
        5. Verify automatic redirection to /auth/signin

    Mocks Required:
        - None (tests actual navigation flow)

    Expected Behavior:
        - Homepage displays "Sign In" button
        - Clicking button redirects to /auth/signin
        - Sign-in page URL pattern matches expected

    Dependencies:
        - None (no authentication required)
    """

    step(f"Navigate to homepage at {base_url}")
    page.goto(base_url)
    page.wait_for_load_state("domcontentloaded")

    step("Wait for Sign In button to be visible")
    sign_in_button = page.get_by_text("Sign In").first
    expect(sign_in_button).to_be_visible(timeout=5000)

    step("Click 'Sign In' button")
    sign_in_button.click()

    step("Verify redirection to signin page")
    expect(page).to_have_url(re.compile(r".*/auth/signin"), timeout=5000)


def test_auth_pages_accessibility(page: Page, base_url: str, step):
    """
    Test authentication protection behavior for auth pages.

    Purpose:
        Verify that authenticated users are properly redirected away from
        authentication pages (sign-in, sign-up) to dashboard,
        while reset-password page remains accessible.

    Test Specification:
        1. Sign in as authenticated user with valid credentials
        2. Navigate to /auth/signin (expect redirect to dashboard)
        3. Navigate to /auth/signup (expect redirect to dashboard)
        4. Navigate to /auth/reset-password (expect to stay on page)
        5. Verify password reset form is visible
        6. Fill and submit password reset form
        7. Verify success message appears

    Mocks Required:
        - None (uses global auth mocks from conftest.py)

    Expected Behavior:
        - Authenticated users accessing sign-in/sign-up are redirected to /dashboard
        - Authenticated users accessing /auth/reset-password remain on the page
        - Password reset form is accessible and functional
        - Successful reset displays confirmation message

    Dependencies:
        - User must be able to sign in with test credentials
    """

    # Sign-in user
    step("Navigate to Signin page")
    page.goto(f"{base_url}/auth/signin")

    step("Sign in with existing test credentials")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard")

    # Now go to auth pages and verify redirection
    auth_pages = [
        "/auth/signin",
        "/auth/signup",
        "/auth/reset-password",
    ]

    for path in auth_pages:
        step(f"Check authenticated user access to {path}")
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("domcontentloaded")

        if path in ["/auth/signin", "/auth/signup"]:
            # Sign-in and sign-up pages should redirect authenticated users to dashboard
            step("Verify user is redirected to dashboard (not auth page)")
            expect(page).to_have_url(re.compile(r".*/dashboard"), timeout=5000)
        elif path == "/auth/reset-password":
            # Reset password page should allow authenticated users to access it
            step("Verify user can access reset password page")
            expect(page).to_have_url(re.compile(r".*/auth/reset-password"), timeout=5000)
            # Check that the password reset form is visible
            expect(page.get_by_label("New Password")).to_be_visible(timeout=5000)

            # Try to reset password and check success message
            step("Fill and submit password reset form")
            page.fill('input#password', "NewPassword123!")
            page.fill('input#confirmPassword', "NewPassword123!")
            page.click('button[type="submit"]')

            step("Verify password reset success message")
            expect(page.get_by_text("Password Reset Successful")).to_be_visible(timeout=5000)

