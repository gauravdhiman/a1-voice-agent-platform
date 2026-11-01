"""Browser coverage for website URL gating on business-context generation."""

import json
import re

from helpers import signin_user
from playwright.sync_api import Page, expect

ORG_ID = "00000000-0000-0000-0000-000000000001"


def test_generator_button_requires_a_complete_public_website_url(
    page: Page, base_url: str
) -> None:
    """Malformed website input keeps the user-initiated action hidden."""
    organization = {
        "id": ORG_ID,
        "name": "Test Organization",
        "slug": "test-organization",
        "is_active": True,
        "onboarding_completed": True,
        "created_at": "2026-01-21T00:00:00Z",
        "updated_at": "2026-01-21T00:00:00Z",
        "description": "",
        "industry": "Other",
        "location": "",
        "timezone": "America/Phoenix",
        "website": "",
        "business_details": "",
    }
    page.route(
        re.compile(rf".*/api/v1/organizations/{ORG_ID}(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(organization),
        ),
    )

    signin_user(page, base_url)
    page.goto(f"{base_url}/organization")
    page.wait_for_load_state("networkidle")

    page.get_by_role("button", name="Edit", exact=True).click()
    website = page.get_by_role("textbox", name="Website")
    generate_button = page.get_by_test_id("generate-business-context")

    website.fill("https:cognients.com")
    expect(generate_button).to_have_count(0)

    website.fill("https://cognients.com")
    expect(generate_button).to_be_visible()

    # Keep this test isolated: do not save the temporary form value.
    page.get_by_role("button", name="Cancel", exact=True).click()
    expect(page.get_by_text("No website", exact=True)).to_be_visible()
