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
    page.wait_for_load_state("domcontentloaded")

    page.get_by_role("button", name="Edit", exact=True).click()
    website = page.get_by_role("textbox", name="Website")
    generate_button = page.get_by_test_id("generate-business-context")

    website.fill("https:cognients.com")
    expect(generate_button).to_have_count(0)

    website.fill("https://cognients.com")
    expect(generate_button).to_be_visible()

    context_field = page.locator("#business_details")
    context_label = page.locator('label[for="business_details"]')
    expect(context_field).to_be_visible()
    assert generate_button.evaluate(
        "(button) => Boolean(button.compareDocumentPosition("
        "document.querySelector('#business_details')) & Node.DOCUMENT_POSITION_FOLLOWING)"
    )
    button_box = generate_button.bounding_box()
    label_box = context_label.bounding_box()
    field_box = context_field.bounding_box()
    assert button_box and label_box and field_box
    assert abs(button_box["y"] - label_box["y"]) < 16
    assert button_box["x"] > label_box["x"]
    assert button_box["y"] < field_box["y"]

    page.set_viewport_size({"width": 390, "height": 844})
    context_field.scroll_into_view_if_needed()
    mobile_button_box = generate_button.bounding_box()
    mobile_label_box = context_label.bounding_box()
    mobile_field_box = context_field.bounding_box()
    assert mobile_button_box and mobile_label_box and mobile_field_box
    assert (
        mobile_button_box["y"]
        >= mobile_label_box["y"] + mobile_label_box["height"]
    )
    assert mobile_button_box["y"] < mobile_field_box["y"]

    # Keep this test isolated: do not save the temporary form value.
    page.get_by_role("button", name="Cancel", exact=True).click()
    expect(page.get_by_text("No website", exact=True)).to_be_visible()
