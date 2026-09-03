"""E2E coverage for public organization and demo-agent journeys."""

import json
import re

from helpers import signin_user
from playwright.sync_api import Page, expect


def _fulfill_json(route, payload, status=200):
    """Fulfill a Playwright route with a JSON response."""
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(payload),
    )


def test_public_org_page_lists_published_agents(page: Page, base_url: str, step):
    """Visitors can see the active agents explicitly published by an org."""
    org_slug = "acme-dental"
    agent_id = "00000000-0000-0000-0000-000000000101"

    page.route(
        re.compile(rf".*/api/v1/public/orgs/{org_slug}$"),
        lambda route: _fulfill_json(
            route,
            {
                "id": "00000000-0000-0000-0000-000000000201",
                "name": "Acme Dental",
                "description": "Friendly dental care from Acme.",
                "slug": org_slug,
                "passphrase_required": False,
            },
        ),
    )
    page.route(
        re.compile(rf".*/api/v1/public/orgs/{org_slug}/agents$"),
        lambda route: _fulfill_json(
            route,
            {
                "agents": [
                    {
                        "id": agent_id,
                        "name": "Front Desk Agent",
                        "persona": "Dental receptionist",
                        "mission": "Book appointments",
                    }
                ]
            },
        ),
    )

    step("Open the public organization page")
    page.goto(f"{base_url}/o/{org_slug}")

    step("Verify the published agent is visible to visitors")
    expect(page.get_by_role("heading", name="Acme Dental")).to_be_visible()
    expect(page.get_by_role("heading", name="Front Desk Agent")).to_be_visible()
    expect(page.get_by_role("link", name="Talk to this agent")).to_be_visible()


def test_protected_public_org_page_requires_passphrase(page: Page, base_url: str, step):
    """A protected public page unlocks its published-agent list after access."""
    org_slug = "protected-dental"
    token_seen = []

    page.route(
        re.compile(rf".*/api/v1/public/orgs/{org_slug}$"),
        lambda route: _fulfill_json(
            route,
            {
                "id": "00000000-0000-0000-0000-000000000202",
                "name": "Protected Dental",
                "description": None,
                "slug": org_slug,
                "passphrase_required": True,
            },
        ),
    )
    page.route(
        re.compile(rf".*/api/v1/public/orgs/{org_slug}/access$"),
        lambda route: _fulfill_json(route, {"access_token": "public-access-token"}),
    )

    def handle_agents(route):
        token_seen.append(route.request.headers.get("x-public-access-token"))
        _fulfill_json(
            route,
            {
                "agents": [
                    {
                        "id": "00000000-0000-0000-0000-000000000102",
                        "name": "Protected Agent",
                        "persona": "Private receptionist",
                        "mission": None,
                    }
                ]
            },
        )

    page.route(
        re.compile(rf".*/api/v1/public/orgs/{org_slug}/agents$"),
        handle_agents,
    )

    step("Open the protected public organization page")
    page.goto(f"{base_url}/o/{org_slug}")
    expect(page.get_by_text("Protected page")).to_be_visible()

    step("Submit the organization passphrase")
    page.get_by_label("Passphrase").fill("correct-horse-battery-staple")
    page.get_by_role("button", name="Continue").click()

    step("Verify the published list loads with the short-lived access token")
    expect(page.get_by_role("heading", name="Protected Agent")).to_be_visible()
    assert token_seen == ["public-access-token"]


def test_public_demo_page_renders_description_and_visualizer_choice(
    page: Page, base_url: str, step
):
    """Visitors can open a demo slug without auth and select the bar visualizer."""
    demo_slug = "acme-demo"
    page.route(
        re.compile(rf".*/api/v1/public/demo/{demo_slug}$"),
        lambda route: _fulfill_json(
            route,
            {
                "id": "00000000-0000-0000-0000-000000000103",
                "name": "Acme Concierge",
                "demo_slug": demo_slug,
                "persona": "Helpful concierge",
                "mission": "Answer questions",
                "tone": "Warm",
                "public_description": "Book a dental visit and answer common questions.",
                "demo_calls_remaining": 3,
                "demo_max_call_duration_seconds": 600,
                "organization_id": "00000000-0000-0000-0000-000000000203",
                "organization_name": "Acme Dental",
            },
        ),
    )

    step("Open the public demo page with the lk-bars visualizer")
    page.goto(f"{base_url}/demo/{demo_slug}?visualizer=lk-bars")

    expect(page.locator('[data-demo-visualizer="lk-bars"]')).to_be_visible()
    expect(page.get_by_text("Acme Dental")).to_be_visible()
    expect(
        page.locator("main > section").get_by_text(
            "Book a dental visit and answer common questions."
        )
    ).to_be_visible()
    expect(page.get_by_text("3 trial calls remaining")).to_be_visible()
    expect(page.get_by_text("Maximum 10 minutes per call")).to_be_visible()
    start_button = page.get_by_role("button", name="Talk to Acme Concierge")
    expect(start_button).to_be_visible()
    expect(start_button).to_be_disabled()
    for viewport_width, viewport_height in ((1280, 720), (390, 844)):
        page.set_viewport_size({"width": viewport_width, "height": viewport_height})
        button_box = start_button.bounding_box()
        assert button_box is not None
        assert button_box["y"] + button_box["height"] <= viewport_height
    expect(
        page.get_by_text(
            "This agent writes the information you share to a public demo data store that other visitors may see."
        )
    ).to_be_visible()
    expect(
        page.get_by_role("link", name="Learn how Gmail aliases work")
    ).to_have_attribute("href", "https://support.google.com/mail/answer/22370?hl=en")
    page.get_by_role(
        "checkbox",
        name="I understand this is a public demo and will use dummy information.",
    ).check()
    expect(start_button).to_be_enabled()

    step("Verify the default visualizer remains radial")
    page.goto(f"{base_url}/demo/{demo_slug}")
    expect(page.locator('[data-demo-visualizer="radial"]')).to_be_visible()


def test_exhausted_public_demo_page_disables_trial_call(
    page: Page, base_url: str, step
):
    """An exhausted demo is visible but cannot start another call."""
    demo_slug = "exhausted-demo"
    page.route(
        re.compile(rf".*/api/v1/public/demo/{demo_slug}$"),
        lambda route: _fulfill_json(
            route,
            {
                "id": "00000000-0000-0000-0000-000000000105",
                "name": "Exhausted Concierge",
                "demo_slug": demo_slug,
                "persona": "Helpful concierge",
                "mission": "Answer questions",
                "tone": "Warm",
                "public_description": "A limited trial demo.",
                "organization_id": "00000000-0000-0000-0000-000000000203",
                "organization_name": "Acme Dental",
                "demo_calls_remaining": 0,
                "demo_max_call_duration_seconds": 600,
            },
        ),
    )

    page.goto(f"{base_url}/demo/{demo_slug}")

    expect(page.get_by_text("This demo is currently unavailable")).to_be_visible()
    expect(
        page.get_by_text(
            "This demo agent has used all available trial calls. Please contact the platform administrator for further details or to have the demo re-enabled."
        )
    ).to_be_visible()
    expect(page.get_by_text("Calls: No trial calls remaining")).to_have_count(0)
    expect(page.get_by_text("Duration: Maximum 10 minutes per call")).to_have_count(0)
    assert page.get_by_role("button", name="Demo unavailable").is_disabled()


def test_public_demo_outcome_page_shows_provider_backed_receipt(
    page: Page, base_url: str, step
):
    """A visitor can inspect the fields and provider confirmed by a demo call."""
    demo_slug = "copper-ridge-service-request"
    page.route(
        re.compile(rf".*/api/v1/public/demo/{demo_slug}/outcome\?token=.*"),
        lambda route: _fulfill_json(
            route,
            {
                "demo_slug": demo_slug,
                "agent_name": "Jordan",
                "organization_name": "Copper Ridge Heating & Air",
                "status": "completed",
                "actions": [
                    {
                        "id": "00000000-0000-0000-0000-000000000501",
                        "action_type": "lead_capture",
                        "provider": "google_sheets",
                        "status": "succeeded",
                        "error_code": None,
                        "captured_fields": {
                            "caller_name": "Maria Garcia",
                            "service_needed": "AC repair",
                            "issue_summary": "Warm air upstairs",
                        },
                        "provider_result": {
                            "record_type": "lead_row",
                            "record_id": "submission-123",
                            "updated_range": "Lead submissions!A2",
                            "message": "Service inquiry captured in Google Sheets.",
                        },
                        "created_at": "2026-08-30T10:00:00Z",
                        "expires_at": "2026-09-06T10:00:00Z",
                    },
                    {
                        "id": "00000000-0000-0000-0000-000000000503",
                        "action_type": "email_delivery",
                        "provider": "gmail",
                        "status": "succeeded",
                        "error_code": None,
                        "captured_fields": {},
                        "provider_result": {
                            "record_type": "email",
                            "record_id": "gmail-message-123",
                            "message": "Gmail confirmed the email was sent.",
                        },
                        "created_at": "2026-08-30T10:00:01Z",
                        "expires_at": "2026-09-06T10:00:01Z",
                    },
                ],
                "expires_at": "2026-09-06T10:00:00Z",
            },
        ),
    )

    step("Open the private demo outcome receipt")
    page.goto(f"{base_url}/demo/{demo_slug}/outcome?token=visitor-receipt-token-123456")

    step("Verify the captured inquiry and provider confirmation")
    expect(page.get_by_text("The handoff is complete")).to_be_visible()
    expect(page.get_by_text("Maria Garcia")).to_be_visible()
    expect(page.get_by_text("AC repair")).to_be_visible()
    expect(page.get_by_text("Google Sheets", exact=True)).to_be_visible()
    expect(page.get_by_text("Email confirmation sent")).to_be_visible()
    expect(page.get_by_text("Gmail confirmed the email was sent.")).to_be_visible()


def test_public_demo_outcome_page_is_clear_when_provider_save_fails(
    page: Page, base_url: str, step
):
    """A failed provider mutation is not presented as a completed capture."""
    demo_slug = "copper-ridge-service-request"
    page.route(
        re.compile(rf".*/api/v1/public/demo/{demo_slug}/outcome\?token=.*"),
        lambda route: _fulfill_json(
            route,
            {
                "demo_slug": demo_slug,
                "agent_name": "Jordan",
                "organization_name": "Copper Ridge Heating & Air",
                "status": "needs_attention",
                "actions": [
                    {
                        "id": "00000000-0000-0000-0000-000000000502",
                        "action_type": "lead_capture",
                        "provider": "google_sheets",
                        "status": "failed",
                        "error_code": "invalid_configuration",
                        "captured_fields": {
                            "caller_name": "Maria Garcia",
                            "caller_email": "maria@example.com",
                            "service_needed": "AC repair",
                        },
                        "provider_result": {
                            "message": "The Google Sheets destination is not configured for this demo.",
                        },
                        "created_at": "2026-08-30T10:00:00Z",
                        "expires_at": "2026-09-06T10:00:00Z",
                    }
                ],
                "expires_at": "2026-09-06T10:00:00Z",
            },
        ),
    )

    step("Open the failed private demo outcome receipt")
    page.goto(f"{base_url}/demo/{demo_slug}/outcome?token=visitor-receipt-token-123456")

    step("Verify the receipt distinguishes captured details from a failed save")
    expect(page.get_by_text("Review what Jordan captured.")).to_be_visible()
    expect(page.get_by_text("Service inquiry details captured")).to_be_visible()
    expect(page.get_by_text("Not completed")).to_be_visible()
    expect(
        page.get_by_text(
            "The Google Sheets destination is not configured for this demo."
        )
    ).to_be_visible()
    expect(page.get_by_text("Service inquiry captured", exact=True)).to_have_count(0)


def test_platform_admin_can_publish_and_mark_demo_agent(
    page: Page, base_url: str, step
):
    """Platform admins can save both public-page and demo-agent settings."""
    org_id = "00000000-0000-0000-0000-000000000001"
    agent_id = "00000000-0000-0000-0000-000000000104"
    state = {
        "id": agent_id,
        "name": "Configurable Agent",
        "organization_id": org_id,
        "phone_number": "+14155551234",
        "is_active": True,
        "is_published_on_public_page": False,
        "is_demo": False,
        "demo_slug": None,
        "public_description": None,
        "demo_public_result_url": None,
        "demo_calls_remaining": -1,
        "demo_max_call_duration_seconds": -1,
        "persona": "Receptionist",
        "tone": "Professional",
        "mission": "Help callers",
        "instructions_markdown": "# Instructions\n\nHelp callers.",
        "preset_id": None,
        "call_recording_enabled": False,
        "use_platform_credits": False,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    update_payloads = []

    page.route(
        re.compile(rf".*/api/v1/organizations/{org_id}$"),
        lambda route: _fulfill_json(
            route,
            {
                "id": org_id,
                "name": "Test Organization",
                "slug": "test-org",
                "is_active": True,
                "onboarding_completed": True,
            },
        ),
    )

    def handle_agent(route):
        if route.request.method == "GET":
            _fulfill_json(route, state)
            return
        if route.request.method == "PUT":
            payload = route.request.post_data_json or {}
            update_payloads.append(payload)
            state.update(payload)
            _fulfill_json(route, state)
            return
        route.continue_()

    page.route(re.compile(rf".*/api/v1/agents/{agent_id}$"), handle_agent)

    step("Sign in as the platform administrator")
    signin_user(page, base_url)

    step("Open agent settings")
    page.goto(f"{base_url}/agents/{agent_id}")
    expect(page.get_by_text("Agent Persona")).to_be_visible(timeout=10000)
    page.get_by_role("tab", name="Settings").click()
    expect(page.get_by_text("Agent Settings")).to_be_visible()

    step("Enable public publishing and demo settings")
    page.locator("#public-page-publish").click()
    page.locator("#is-demo").click()
    page.get_by_label("Demo slug *").fill("acme-demo")
    page.get_by_label("Public description").fill("A customer-facing demo description")
    page.get_by_label("Public result URL (optional)").fill(
        "https://docs.google.com/spreadsheets/d/demo-sheet/edit?gid=0#gid=0"
    )
    page.get_by_label("Demo calls remaining").fill("3")
    page.get_by_label("Maximum call duration (minutes)").fill("10")

    step("Save the agent and verify the API payload")
    with page.expect_response(
        lambda response: response.request.method == "PUT"
        and f"/api/v1/agents/{agent_id}" in response.url
    ):
        page.get_by_role("button", name="Save Changes").click()

    assert len(update_payloads) == 1
    assert update_payloads[0]["is_published_on_public_page"] is True
    assert update_payloads[0]["is_demo"] is True
    assert update_payloads[0]["demo_slug"] == "acme-demo"
    assert (
        update_payloads[0]["public_description"] == "A customer-facing demo description"
    )
    assert (
        update_payloads[0]["demo_public_result_url"]
        == "https://docs.google.com/spreadsheets/d/demo-sheet/edit?gid=0#gid=0"
    )
    assert update_payloads[0]["demo_calls_remaining"] == 3
    assert update_payloads[0]["demo_max_call_duration_seconds"] == 600
