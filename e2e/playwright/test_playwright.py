"""Playwright test for AI Voice Agent Platform."""

from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        # Test 1: Backend health check
        print("\n=== Testing Backend Health ===")
        try:
            response = page.request.get('http://localhost:8000/health')
            health_data = response.json()
            print(f"Backend health status: {health_data.get('status')}")
            print(f"Checks: {health_data.get('checks')}")
        except Exception as e:
            print(f"Backend health check failed: {e}")

        # Test 2: Backend root endpoint
        print("\n=== Testing Backend Root Endpoint ===")
        try:
            response = page.request.get('http://localhost:8000/')
            root_data = response.json()
            print(f"Backend message: {root_data.get('message')}")
            print(f"Version: {root_data.get('version')}")
        except Exception as e:
            print(f"Backend root endpoint failed: {e}")

        # Test 3: Frontend homepage
        print("\n=== Testing Frontend Homepage ===")
        try:
            page.goto('http://localhost:3000')
            page.wait_for_load_state('networkidle')
            title = page.title()
            print(f"Page title: {title}")

            # Take screenshot for visual inspection
            screenshot_path = '/tmp/ai-voice-agent-homepage.png'
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")

            # Check for common elements
            body_text = page.locator('body').inner_text()[:500]
            print(f"Page preview: {body_text}...")

            # Find all buttons and links
            buttons = page.locator('button').all()
            print(f"Found {len(buttons)} buttons on the page")

            links = page.locator('a').all()
            print(f"Found {len(links)} links on the page")

            # Look for navigation elements
            nav = page.locator('nav').first
            if nav.is_visible():
                print("Navigation bar found")
            else:
                print("No navigation bar visible")

        except Exception as e:
            print(f"Frontend homepage test failed: {e}")
            import traceback
            traceback.print_exc()

        # Test 4: Check for auth/landing pages
        print("\n=== Checking Auth Pages ===")
        auth_paths = [
            '/auth/signin',
            '/auth/signup',
            '/auth/reset-password',
        ]
        for path in auth_paths:
            try:
                response = page.request.get(f'http://localhost:3000{path}')
                print(f"Path {path} - Status: {response.status}")
                if response.status == 200:
                    page.goto(f'http://localhost:3000{path}')
                    page.wait_for_load_state('networkidle', timeout=3000)
                    print(f"  Title: {page.title()}")
            except Exception as e:
                print(f"Path {path} - Error: {e}")

        # Test 5: Check dashboard routes (should redirect to auth if not logged in)
        print("\n=== Checking Dashboard Routes ===")
        dashboard_paths = [
            '/dashboard',
            '/organization',
            '/billing',
            '/settings',
        ]
        for path in dashboard_paths:
            try:
                response = page.request.get(f'http://localhost:3000{path}')
                print(f"Path {path} - Status: {response.status}")
                if response.status == 200:
                    page.goto(f'http://localhost:3000{path}')
                    page.wait_for_load_state('networkidle', timeout=3000)
                    print(f"  Title: {page.title()}")
            except Exception as e:
                print(f"Path {path} - Error: {e}")

        # Test 6: Click navigation
        print("\n=== Testing Navigation ===")
        try:
            page.goto('http://localhost:3000')
            page.wait_for_load_state('networkidle')

            # Try to find and click "Get Started" or "Sign In" buttons
            get_started = page.get_by_text('Get Started').first
            if get_started.is_visible():
                print("Found 'Get Started' button")
            else:
                print("'Get Started' button not visible")

            sign_in = page.get_by_text('Sign In').first
            if sign_in.is_visible():
                print("Found 'Sign In' button")
                sign_in.click()
                page.wait_for_load_state('networkidle')
                print(f"Navigated to: {page.url}")
        except Exception as e:
            print(f"Navigation test failed: {e}")

        browser.close()
        print("\n=== Test Complete ===")

if __name__ == '__main__':
    main()
