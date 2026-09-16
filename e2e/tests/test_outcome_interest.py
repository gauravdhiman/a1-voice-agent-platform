"""Outcome-page interest capture (closes the demo-to-funnel loop)."""

import re
from urllib.parse import urlsplit

from playwright.sync_api import Locator, Page, expect


def _set_public_theme(page: Page, theme: str) -> None:
    """Set and verify the shared public day/night theme."""
    switch = page.get_by_role("switch")
    should_be_dark = theme == "night"
    if (switch.get_attribute("aria-checked") == "true") != should_be_dark:
        switch.click()
    expect(switch).to_have_attribute("aria-checked", str(should_be_dark).lower())
    expect(page.locator(f'[data-theme="{theme}"]')).to_be_visible()
    # Let the public shell's color transition finish before measuring contrast.
    page.wait_for_timeout(600)


def _assert_contrast(locator: Locator, minimum: float) -> None:
    """Check a visible foreground color against its nearest solid background."""
    colors = locator.evaluate(
        """element => {
            const parse = value => {
                const match = value.match(/rgba?\\(([^)]+)\\)/);
                if (!match) return null;
                const parts = match[1].split(/[,/ ]+/).filter(Boolean).map(Number);
                return [parts[0], parts[1], parts[2], parts[3] ?? 1];
            };
            const foreground = parse(getComputedStyle(element).color);
            let node = element;
            let background = null;
            while (node) {
                const color = parse(getComputedStyle(node).backgroundColor);
                if (color && color[3] >= 0.95) {
                    background = color;
                    break;
                }
                node = node.parentElement;
            }
            if (!foreground || !background) {
                return {
                    ratio: 0,
                    foreground,
                    background,
                    text: element.textContent.trim(),
                };
            }
            const luminance = color => color.slice(0, 3).map(channel => {
                const value = channel / 255;
                return value <= 0.04045
                    ? value / 12.92
                    : ((value + 0.055) / 1.055) ** 2.4;
            }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
            const values = [luminance(foreground), luminance(background)]
                .sort((a, b) => b - a);
            return {
                ratio: (values[0] + 0.05) / (values[1] + 0.05),
                foreground: getComputedStyle(element).color,
                background: getComputedStyle(node).backgroundColor,
                text: element.textContent.trim(),
            };
        }"""
    )
    assert colors["ratio"] >= minimum, (
        f"contrast {colors['ratio']:.2f}:1 is below {minimum}:1 "
        f"(foreground {colors['foreground']}, background {colors['background']}, "
        f"text {colors['text']!r})"
    )


def _assert_input_border_state(locator: Locator) -> None:
    """Valid fields stay neutral and invalid fields get the danger color."""
    colors = locator.evaluate(
        """element => {
            const original = element.getAttribute("aria-invalid");
            const originalBorder = element.style.borderColor;
            const normal = getComputedStyle(element).borderColor;
            element.style.borderColor = "var(--input-border)";
            const themed = getComputedStyle(element).borderColor;
            element.style.borderColor = originalBorder;
            element.setAttribute("aria-invalid", "true");
            const invalid = getComputedStyle(element).borderColor;
            if (original === null) element.removeAttribute("aria-invalid");
            else element.setAttribute("aria-invalid", original);
            return { normal, themed, invalid };
        }"""
    )
    assert colors["normal"] == colors["themed"]
    assert colors["themed"] != colors["invalid"]


def test_outcome_interest_form_posts_to_leads(page: Page, base_url: str, step):
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


def test_outcome_rating_posts_to_feedback(page: Page, base_url: str, step):
    """A visitor star rating is stored against their own demo session."""
    demo_slug = "copper-ridge-service-request"
    step("Mock the outcome receipt and the feedback endpoint")
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
        re.compile(rf".*/api/v1/public/demo/{demo_slug}/feedback\?token=.*"),
        lambda route: (
            posted.append(route.request.post_data_json or {}),
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"received": true}',
            ),
        ),
    )

    step("Open the outcome page and rate the call")
    page.goto(f"{base_url}/demo/{demo_slug}/outcome?token=receipt-123")
    page.get_by_role("button", name="Rate 4 out of 5").click()

    step("Verify the bound rating payload and the thanks state")
    expect(page.get_by_test_id("demo-feedback-thanks")).to_be_visible(timeout=10000)
    assert posted, "expected one feedback POST"
    assert posted[0] == {"rating": 4}


def test_outcome_secondary_content_is_legible_in_both_themes(
    page: Page, base_url: str, step
):
    """Empty and saved summaries keep supporting text and icons readable."""
    no_action_slug = "copper-ridge-service-request"
    saved_slug = "pleasant-pediatric-appointments"
    no_action = """{
        "demo_slug": "copper-ridge-service-request",
        "agent_name": "Jordan",
        "organization_name": "Copper Ridge Heating & Air",
        "status": "no_action",
        "actions": [],
        "expires_at": "2026-09-06T10:00:00Z"
    }"""
    saved = """{
        "demo_slug": "pleasant-pediatric-appointments",
        "agent_name": "Alex",
        "organization_name": "Pleasant Pediatric",
        "status": "completed",
        "actions": [{
            "id": "receipt-1",
            "action_type": "lead_capture",
            "provider": "google_sheets",
            "status": "succeeded",
            "error_code": null,
            "captured_fields": {
                "caller_name": "Maria Garcia",
                "service_needed": "Furnace repair"
            },
            "provider_result": {
                "record_type": "lead_row",
                "record_id": "demo-row",
                "message": "Appointment details saved to the demo sheet."
            },
            "public_result_url": null,
            "created_at": "2026-09-05T10:00:00Z",
            "expires_at": "2026-09-06T10:00:00Z"
        }],
        "expires_at": "2026-09-06T10:00:00Z"
    }"""

    def mock_outcome(route):
        path = urlsplit(route.request.url).path
        body = saved if saved_slug in path else no_action
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route(
        re.compile(r".*/api/v1/public/demo/[^/]+/outcome\?token=.*"),
        mock_outcome,
    )

    step("Check the empty-result summary in day and night mode")
    page.goto(f"{base_url}/demo/{no_action_slug}/outcome?token=receipt-123")
    empty_heading = page.get_by_role(
        "heading", name="Nothing got saved on this call", exact=True
    )
    expect(empty_heading).to_be_visible(timeout=15000)
    trust_label = page.locator("p").filter(has_text="PRIVATE CALL SUMMARY")
    empty_description = empty_heading.locator("xpath=following-sibling::p[1]")
    expect(empty_description).to_contain_text(
        "This page only shows results that tools confirmed."
    )
    feedback_region = page.get_by_role(
        "complementary", name="Feedback and setup request"
    )
    feedback_sticky = page.get_by_test_id("outcome-feedback-sticky")
    details_region = page.get_by_role("region", name="Call details and results")
    tool_icon = empty_heading.locator("xpath=../..").locator("svg").first
    benefits_heading = page.get_by_text("IF THIS RAN YOUR BUSINESS")
    benefit_icons = benefits_heading.locator("xpath=..").locator("svg")
    expiration = page.get_by_text("Summary expires after 24 hours")
    back_link = page.get_by_role("link", name="Back to demo")
    try_again = page.get_by_role("link", name="Try the call again", exact=True)
    name_input = page.get_by_label("Your name")

    expect(feedback_region).to_be_visible()
    expect(feedback_sticky).to_have_css("position", "sticky")
    detail_box = details_region.bounding_box()
    feedback_box = feedback_region.bounding_box()
    assert detail_box is not None and feedback_box is not None
    assert feedback_box["x"] > detail_box["x"]

    for theme in ("day", "night"):
        _set_public_theme(page, theme)
        _assert_contrast(trust_label, 4.5)
        _assert_contrast(trust_label.locator("svg"), 3.0)
        _assert_contrast(empty_description, 4.5)
        _assert_contrast(tool_icon, 3.0)
        _assert_contrast(expiration, 4.5)
        _assert_contrast(back_link, 4.5)
        _assert_contrast(try_again, 4.5)
        _assert_input_border_state(name_input)
        expect(benefit_icons).to_have_count(3)
        for index in range(3):
            _assert_contrast(benefit_icons.nth(index), 3.0)

    page.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
    page.evaluate("window.scrollTo(0, 500)")
    page.wait_for_function("window.scrollY >= 500")
    sticky_box = feedback_sticky.bounding_box()
    assert sticky_box is not None
    assert abs(sticky_box["y"] - 24) <= 2

    page.set_viewport_size({"width": 390, "height": 844})
    expect(feedback_sticky).to_have_css("position", "static")

    step("Check saved fields and provider confirmation in both themes")
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(f"{base_url}/demo/{saved_slug}/outcome?token=receipt-123")
    expect(
        page.get_by_role("heading", name="That call just did real work.")
    ).to_be_visible(timeout=15000)
    expect(
        page.get_by_role("complementary", name="Feedback and setup request")
    ).to_be_visible()
    saved_to = page.locator("p").filter(has_text="Saved to your spreadsheet")
    collected_label = page.get_by_text("WHAT WAS COLLECTED")
    field_label = page.locator("dt").filter(has_text="Name").first
    provider_message = page.get_by_text(
        "Appointment details saved to the demo sheet.", exact=True
    )
    for theme in ("day", "night"):
        _set_public_theme(page, theme)
        _assert_contrast(trust_label, 4.5)
        _assert_contrast(expiration, 4.5)
        _assert_contrast(back_link, 4.5)
        _assert_contrast(collected_label, 4.5)
        _assert_contrast(saved_to, 4.5)
        _assert_contrast(field_label, 4.5)
        _assert_contrast(provider_message, 4.5)


def test_public_auth_action_button_has_theme_contrast(page: Page, base_url: str):
    """Button links keep their foreground token inside the public theme shell."""
    page.goto(
        f"{base_url}/auth/session?error=Authentication%20could%20not%20be%20completed."
    )
    retry = page.get_by_role("link", name="Try signing in again")
    error_alert = page.get_by_role("main").get_by_role("alert")
    expect(retry).to_be_visible(timeout=15000)

    for theme in ("day", "night"):
        _set_public_theme(page, theme)
        _assert_contrast(error_alert, 4.5)
        _assert_contrast(retry, 4.5)


def test_embedded_missing_agent_error_has_theme_contrast(page: Page, base_url: str):
    """Standalone embed errors follow the selected workspace color scheme."""
    for theme in ("day", "night"):
        page.goto(
            f"{base_url}/auth/session?error=Authentication%20could%20not%20be%20completed."
        )
        retry = page.get_by_role("link", name="Try signing in again")
        expect(retry).to_be_visible(timeout=15000)
        _set_public_theme(page, theme)

        page.goto(f"{base_url}/embed/call")
        message = page.get_by_text("No agent ID provided", exact=True)
        expect(message).to_be_visible(timeout=15000)
        _assert_contrast(message, 4.5)
