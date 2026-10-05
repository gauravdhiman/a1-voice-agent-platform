"""Platform interest queue browser coverage (owner follow-up workflow)."""

import re

from playwright.sync_api import Page, expect

from helpers import signin_user

LEAD_ROW = """{{
    "id": "11111111-1111-1111-1111-111111111111",
    "name": "Sam Owner",
    "business_name": "Bright Smiles",
    "email": "sam@example.com",
    "phone": null,
    "vertical": "dental",
    "message": "Miss after-hours calls.",
    "source": "outcome-form",
    "demo_slug": "copper-ridge-service-request",
    "status": "{status}",
    "created_at": "2026-09-04T00:00:00+00:00",
    "contacted_at": null
}}"""


def test_platform_interest_lists_and_advances_leads(
    page: Page, base_url: str, step
):
    """Platform admin sees attributed leads and moves them forward."""
    step("Mock interest list with one outcome-form lead")
    state = {"status": "new"}

    def handle_list(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=f"[{LEAD_ROW.format(status=state['status'])}]",
        )

    def handle_patch(route):
        if route.request.method != "PATCH":
            route.fallback()
            return
        state["status"] = "contacted"
        route.fulfill(
            status=200,
            content_type="application/json",
            body=LEAD_ROW.format(status="contacted"),
        )

    page.route(re.compile(r".*/api/v1/leads/?(?:\?.*)?$"), handle_list)
    page.route(re.compile(r".*/api/v1/leads/[^/?]+(?:\?.*)?$"), handle_patch)

    step("Sign in as the mocked platform admin")
    signin_user(page, base_url)

    step("Open the interest queue")
    page.goto(f"{base_url}/platform/interest")
    expect(page.get_by_text("Sam Owner")).to_be_visible(timeout=15000)
    expect(page.get_by_text("outcome-form")).to_be_visible()
    expect(page.get_by_text("Miss after-hours calls.")).to_be_visible()

    step("Advance the lead and verify the queue reflects it")
    page.get_by_role("button", name="Mark contacted").click()
    expect(page.get_by_text("contacted").first).to_be_visible(timeout=10000)
