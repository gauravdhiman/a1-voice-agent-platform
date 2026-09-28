"""Guided platform tour shows every chapter with replayable run-throughs."""

import re

from playwright.sync_api import Page, expect


def test_tour_chapters_replay_and_funnel(page: Page, base_url: str):
    """All chapters render; a run-through can pause/replay; funnel works."""
    page.goto(f"{base_url}/how-it-works")
    expect(page.get_by_role("heading", level=1)).to_have_text(
        "From hello to booked, on every call."
    )
    for name in [
        "Describe your business in plain words.",
        "Teach it your way of working.",
    ]:
        expect(page.get_by_role("heading", name=name)).to_be_visible()
    page.get_by_role("link", name="Teach skills").click()
    expect(
        page.get_by_role("heading", name="Teach it your way of working.")
    ).to_be_visible()
    page.get_by_role("button", name="Pause the run-through").first.click()
    expect(
        page.get_by_role("button", name="Play the run-through").first
    ).to_have_attribute("aria-pressed", "true")
    page.get_by_role("button", name=re.compile("Replay .* from the start")).first.click()
    expect(
        page.get_by_role("button", name=re.compile("Pause the run-through")).first
    ).to_be_visible()
    page.get_by_role("link", name="Hear a live demo").click()
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
        page.get_by_role("heading", name=re.compile("without hearing all of them"))
    ).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
