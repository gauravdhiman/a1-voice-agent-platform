"""Guided platform tour keeps every chapter highlight visible."""

import re

from playwright.sync_api import Page, expect


def test_tour_highlights_stay_visible_and_funnel(page: Page, base_url: str):
    """Every chapter keeps all highlights visible and the demo funnel works."""
    page.goto(f"{base_url}/how-it-works")
    expect(page.get_by_role("heading", level=1)).to_have_text(
        "From hello to booked, on every call."
    )
    for heading, chapter, highlights in [
        (
            "Describe your business in plain words.",
            "Create",
            [
                "Write it like you'd say it",
                "Hear it back on a test call",
                "Approve it, then go live in about 48 hours",
            ],
        ),
        (
            "One AI assistant, your number and website.",
            "Answer everywhere",
            [
                "Keep your business number",
                "Add the website voice button",
                "Same AI assistant, every line",
            ],
        ),
        (
            "Works with the tools you already use.",
            "Connect tools",
            [
                "Pick your tools during setup",
                "Watch a booking land",
                "Confirmations handle the rest",
            ],
        ),
        (
            "Teach it your way of working.",
            "Set instructions",
            [
                "Write rules, not code",
                "Choose which assistant follows each rule",
                "Followed on every call",
            ],
        ),
        (
            "Review every call without listening to each one.",
            "Review calls",
            [
                "One log for every call",
                "Play the moments that matter",
                "Kept for 30 days",
            ],
        ),
    ]:
        expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
        highlight_list = page.get_by_role("list", name=f"{chapter} highlights")
        expect(highlight_list.get_by_role("listitem")).to_have_count(3)
        for highlight in highlights:
            expect(
                highlight_list.get_by_role("heading", name=highlight)
            ).to_be_visible()

    page.get_by_role("link", name=re.compile("Set instructions")).click()
    expect(page).to_have_url(re.compile(r"#tour-teach-skills$"))
    for name in [
        "Write rules, not code",
        "Choose which assistant follows each rule",
        "Followed on every call",
    ]:
        expect(page.get_by_role("heading", name=name)).to_be_visible()
    page.get_by_role("link", name=re.compile("Hear .* live demo call")).click()
    expect(page).to_have_url(re.compile(r"/demo/pleasant-pediatric-appointments$"))
    page.goto(f"{base_url}/how-it-works")
    page.get_by_role("link", name="Request a demo", exact=True).first.click()
    expect(page).to_have_url(re.compile(r"/request-demo$"))


def test_tour_mobile_no_overflow(page: Page, base_url: str):
    """Narrow viewports stack each chapter without horizontal overflow."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{base_url}/how-it-works")
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    expect(
        page.get_by_role(
            "heading", name=re.compile("without listening to each one")
        )
    ).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_tour_preview_replays_while_in_view(page: Page, base_url: str):
    """A visible preview restarts after its timeline and a short pause."""
    page.emulate_media(reduced_motion="no-preference")
    page.goto(f"{base_url}/how-it-works")
    preview = page.locator('[data-looping-preview="true"]').first
    preview.scroll_into_view_if_needed()
    expect(preview).to_have_attribute("data-playing", "true")

    initial_cycle = int(preview.get_attribute("data-loop-cycle") or "0")
    duration_ms = int(preview.get_attribute("data-animation-duration-ms") or "0")
    page.wait_for_timeout(duration_ms + 3500)
    expect(preview).to_have_attribute("data-loop-cycle", str(initial_cycle + 1))


def test_publish_scenes_type_and_reveal_the_website_button_after_save(
    page: Page, base_url: str
):
    """The phone number types one character at a time and the website button
    appears after the embed snippet has been saved.
    """
    page.emulate_media(reduced_motion="no-preference")
    page.goto(f"{base_url}/how-it-works#tour-answer-everywhere")

    phone_scene = page.locator('[data-tour-scene="phone-number"]')
    phone_scene.scroll_into_view_if_needed()
    phone_number = phone_scene.locator("[data-phone-number]")
    expect(phone_number).to_have_css("animation-duration", "3.5s")
    expect(phone_number).to_have_css("animation-timing-function", "steps(14)")

    website_scene = page.locator('[data-tour-scene="website-embed"]')
    website_scene.scroll_into_view_if_needed()
    talk_button = website_scene.locator("[data-talk-to-us]")
    saved_status = website_scene.locator("[data-embed-saved]")
    expect(talk_button).to_have_css("opacity", "0")
    expect(saved_status).to_have_css("opacity", "0")

    page.wait_for_timeout(3200)
    expect(talk_button).to_have_css("opacity", "0")
    expect(saved_status).to_have_css("opacity", "0")

    page.wait_for_timeout(1500)
    expect(saved_status).to_have_css("opacity", "1")
    expect(talk_button).to_have_css("opacity", "1")
