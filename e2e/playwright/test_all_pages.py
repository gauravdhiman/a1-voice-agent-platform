"""Comprehensive Playwright test for all public pages."""

from playwright.sync_api import sync_playwright
import os

def test_page(page, url, name, description=""):
    """Test a single page and take screenshot."""
    print(f"\n=== Testing: {name} ===")
    print(f"URL: {url}")

    try:
        page.goto(url)
        page.wait_for_load_state('networkidle')

        title = page.title()
        print(f"Title: {title}")

        # Take screenshot
        screenshot_path = f'/tmp/{name.replace("/", "-").replace(" ", "-")}.png'
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot: {screenshot_path}")

        # Get page preview
        body_text = page.locator('body').inner_text()[:300]
        print(f"Preview: {body_text}...")

        # Check for forms
        forms = page.locator('form').all()
        if forms:
            print(f"Forms: {len(forms)} form(s) found")

        # Check for inputs
        inputs = page.locator('input').all()
        if inputs:
            print(f"Inputs: {len(inputs)} input(s) found")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        print("\n" + "="*60)
        print("COMPREHENSIVE PUBLIC PAGE TESTING")
        print("="*60)

        # Test 1: Backend Health
        print("\n" + "="*60)
        print("BACKEND API TESTS")
        print("="*60)
        try:
            response = page.request.get('http://localhost:8000/health')
            print(f"Backend Health: {response.status} - {response.json()['status']}")
        except Exception as e:
            print(f"Backend Error: {e}")

        # Test 2: Frontend Public Pages
        print("\n" + "="*60)
        print("FRONTEND PUBLIC PAGES")
        print("="*60)

        pages_to_test = [
            ('http://localhost:3000/', 'Homepage', 'Main landing page'),
            ('http://localhost:3000/auth/signin', 'Sign In Page', 'User authentication login'),
            ('http://localhost:3000/auth/signup', 'Sign Up Page', 'User registration'),
            ('http://localhost:3000/auth/reset-password', 'Reset Password', 'Password reset flow'),
        ]

        results = {}
        for url, name, description in pages_to_test:
            results[name] = test_page(page, url, name, description)

        # Test 3: Protected Pages (expect redirect or 401)
        print("\n" + "="*60)
        print("PROTECTED ROUTES (Expect redirect or auth required)")
        print("="*60)

        protected_pages = [
            ('http://localhost:3000/auth/create-organization', 'Create Organization'),
            ('http://localhost:3000/dashboard', 'Dashboard'),
            ('http://localhost:3000/organization', 'Organization Page'),
            ('http://localhost:3000/settings', 'Settings'),
            ('http://localhost:3000/billing', 'Billing'),
            ('http://localhost:3000/organizations', 'Organizations List'),
            ('http://localhost:3000/users', 'Users Management'),
        ]

        protected_results = {}
        for url, name in protected_pages:
            print(f"\n=== Testing: {name} ===")
            try:
                response = page.request.get(url)
                print(f"Status: {response.status}")

                if response.status == 200:
                    page.goto(url)
                    page.wait_for_load_state('networkidle')
                    final_url = page.url
                    print(f"Final URL: {final_url}")

                    # Check if redirected
                    if final_url != url:
                        print(f"Redirected from {url} to {final_url}")

                    # Take screenshot
                    screenshot_path = f'/tmp/{name.replace("/", "-")}.png'
                    page.screenshot(path=screenshot_path, full_page=True)
                    print(f"Screenshot: {screenshot_path}")

                protected_results[name] = response.status

            except Exception as e:
                print(f"Error: {e}")
                protected_results[name] = "ERROR"

        # Test 4: Navigation Flow
        print("\n" + "="*60)
        print("NAVIGATION FLOW TESTS")
        print("="*60)

        try:
            # Test home -> signin flow
            print("\nTest: Homepage -> Sign In")
            page.goto('http://localhost:3000/')
            page.wait_for_load_state('networkidle')

            sign_in_btn = page.get_by_text('Sign In').first
            if sign_in_btn.is_visible():
                sign_in_btn.click()
                page.wait_for_load_state('networkidle')
                print(f"Navigated to: {page.url}")
            else:
                print("'Sign In' button not found")

            # Test signin -> signup flow
            print("\nTest: Sign In -> Sign Up")
            signup_link = page.get_by_text('Sign up for free').first
            if signup_link.is_visible():
                signup_link.click()
                page.wait_for_load_state('networkidle')
                print(f"Navigated to: {page.url}")
            else:
                print("'Sign up for free' link not found")

        except Exception as e:
            print(f"Navigation test error: {e}")

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        print("\nPublic Pages:")
        for name, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status}: {name}")

        print("\nProtected Routes:")
        for name, status in protected_results.items():
            print(f"  {status}: {name}")

        print("\nScreenshots saved to /tmp/")
        browser.close()

if __name__ == '__main__':
    main()
