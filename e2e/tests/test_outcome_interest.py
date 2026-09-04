"""Outcome-page interest capture (closes the demo-to-funnel loop)."""

import re

from playwright.sync_api import Page, expect


def test_outcome_interest_form_posts_to_leads(
    page: Page, base_url: str, step
):
    """A visitor converts on the outcome page without retyping elsewhere."""
    demo_slug = "copper-ridge-service-request"
    step("Mock the outcome receipt and the leads endpoint")
    page.route(
        re.compile(rf".*/api/v1/public/demo/{demo_slug}/outcome\?token=.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "demo_slug": "copper-ridge-service-request",
                "agent_name": "Jordan",
                "organization_name": "Copper Ridge Heating & Air",
                "status": "completed",
                "actions": [],
                "expires_at": "2026-09-06T10:00:00Z"
            }""",
        ),
    )
    posted = []
    page.route(
        re.compile(r".*/api/v1/public/leads"),
        lambda route: (
            posted.append(route.request.post_data_json or {}),
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"received": true}',
            ),
        ),
    )

    step("Open the outcome page and submit interest")
    page.goto(f"{base_url}/demo/{demo_slug}/outcome?token=receipt-123")
    page.get_by_label("Your name").fill("Sam Owner")
    page.get_by_label("Work email").fill("sam@example.com")
    page.get_by_role("button", name="Get this for my business").click()

    step("Verify the attributed lead payload and the confirmation")
    expect(page.get_by_text("Request received")).to_be_visible(timeout=10000)
    assert posted, "expected one leads POST"
    assert posted[0]["source"] == "outcome-form"
    assert posted[0]["demo_slug"] == demo_slug
    assert posted[0]["vertical"] == "hvac"
    assert posted[0]["email"] == "sam@example.com"
