"""Epic D: soft escalation browser coverage (owner callback queue)."""

import re

from playwright.sync_api import Page, expect

from helpers import signin_user

TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"

ESCALATION_ROW = """{{
    "id": "11111111-1111-1111-1111-111111111111",
    "organization_id": "{org}",
    "agent_id": null,
    "session_id": "session-1",
    "caller_phone": "+14805550100",
    "caller_name": "Sam",
    "reason": "Water heater is leaking.",
    "urgency": "urgent",
    "status": "{status}",
    "notified": true,
    "created_at": "2026-09-04T00:00:00+00:00",
    "acknowledged_at": null
}}"""


def test_callbacks_page_lists_queue_with_actions(
    page: Page, base_url: str, step
):
    """Owner sees callback rows and can acknowledge them (API mocked)."""
    step("Mock escalations list with one urgent callback")
    state = {"status": "new"}

    def handle_list(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=f"[{ESCALATION_ROW.format(org=TEST_ORG_ID, status=state['status'])}]",
        )

    def handle_patch(route):
        state["status"] = "acknowledged"
        route.fulfill(
            status=200,
            content_type="application/json",
            body=ESCALATION_ROW.format(org=TEST_ORG_ID, status="acknowledged"),
        )

    page.route(
        re.compile(rf".*/api/v1/organizations/{TEST_ORG_ID}/escalations.*"),
        handle_list,
    )
    page.route(
        re.compile(rf".*/api/v1/organizations/{TEST_ORG_ID}/escalations/.*"),
        handle_patch,
    )

    step("Sign in as the mocked platform admin")
    signin_user(page, base_url)

    step("Open the callbacks page")
    page.goto(f"{base_url}/callbacks")
    expect(page.get_by_text("+14805550100")).to_be_visible(timeout=15000)
    expect(page.get_by_text("Water heater is leaking.")).to_be_visible()

    step("Acknowledge the callback and verify the queue reflects it")
    page.get_by_role("button", name="Acknowledge").click()
    expect(page.get_by_text("Acknowledged").first).to_be_visible(timeout=10000)
