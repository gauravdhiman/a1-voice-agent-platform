"""Epic A: gated-entry funnel browser coverage.

Covers the two visitor-visible contracts of the controlled-SaaS launch:

1. ``/request-demo`` accepts interest and shows the fixed success copy
   (backend mocked at the network boundary).
2. ``/auth/signup`` without an invitation token redirects to
   ``/request-demo`` while open signup is disabled (status mocked).
"""

import re

from playwright.sync_api import Page, expect


def test_request_demo_submit_shows_success(page: Page, base_url: str, step):
    """Interest form posts to the public leads API and confirms receipt."""
    step("Mock public leads API to accept the submission")
    page.route(
        re.compile(r".*/api/v1/public/leads"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"received": true}',
        ),
    )

    step("Open the request-demo page")
    page.goto(f"{base_url}/request-demo")
    expect(page.get_by_role("heading", name="Request a demo")).to_be_visible(
        timeout=15000
    )

    step("Fill and submit the interest form")
    page.get_by_label("Your name").fill("Sam Owner")
    page.get_by_label("Business name").fill("Bright Smiles Dental")
    page.get_by_label("Work email").fill("sam@example.com")
    page.get_by_role("button", name="Request my demo").click()

    step("Verify the fixed success copy (no email-oracle leakage)")
    expect(page.get_by_test_id("request-demo-success")).to_be_visible(
        timeout=10000
    )
    expect(page.get_by_text("Request received")).to_be_visible()


def test_closed_signup_redirects_to_request_demo(
    page: Page, base_url: str, step
):
    """Gated signup sends visitors without a token to the interest form."""
    step("Mock signup-status as closed (invite-only)")
    page.route(
        re.compile(r".*/api/v1/auth/signup-status"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"public_signup_enabled": false}',
        ),
    )

    step("Visit signup without an invitation token")
    page.goto(f"{base_url}/auth/signup")

    step("Verify redirect to the interest form")
    expect(page).to_have_url(re.compile(r".*/request-demo"), timeout=15000)
    expect(page.get_by_role("heading", name="Request a demo")).to_be_visible(
        timeout=10000
    )


def test_invited_signup_stays_on_signup(page: Page, base_url: str, step):
    """An invitation token bypasses the closed-gate redirect."""
    step("Mock signup-status as closed (invite-only)")
    page.route(
        re.compile(r".*/api/v1/auth/signup-status"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"public_signup_enabled": false}',
        ),
    )

    step("Visit signup with an invitation token")
    page.goto(f"{base_url}/auth/signup?token=invite-123")

    step("Verify the signup form stays visible")
    expect(page).to_have_url(re.compile(r".*/auth/signup\?token=invite-123"))
    expect(
        page.get_by_role("heading", name="Create your free account")
    ).to_be_visible(timeout=15000)
