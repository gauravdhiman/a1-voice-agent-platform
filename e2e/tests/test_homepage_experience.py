"""Homepage storytelling remains navigable in both themes and on mobile."""

import re

from playwright.sync_api import Page, expect


def test_homepage_theme_motion_and_demo_entry(page: Page, base_url: str):
    """Theme persists; motion can stop; the primary funnel remains reachable."""
    page.goto(base_url)
    expect(page.get_by_role("heading", level=1)).to_have_text(
        "Never miss a call.Never miss a customer."
    )
    page.get_by_role("switch", name="Switch to day mode").click()
    expect(page.locator('[data-theme="day"]')).to_be_visible()
    page.reload()
    expect(page.get_by_role("switch", name="Switch to night mode")).to_be_visible()
    page.get_by_role("button", name="Pause ambient animation").click()
    expect(
        page.get_by_role("button", name="Resume ambient animation")
    ).to_have_attribute("aria-pressed", "true")
    page.get_by_role("link", name="Hear it handle a real call").click()
    expect(
        page.get_by_role("heading", name="Don’t take our word. Have a word.")
    ).to_be_visible()
    expect(
        page.get_by_role("link", name=re.compile("Talk to Robin"))
    ).to_have_attribute("href", "/demo/pleasant-pediatric-appointments")
    expect(
        page.get_by_role("heading", name=re.compile("Plugs into the tools"))
    ).to_be_visible()
    page.get_by_role("link", name="Request a demo", exact=True).last.click()
    expect(page).to_have_url(re.compile(r"/request-demo$"))
    expect(page.get_by_role("heading", name="Request a demo")).to_be_visible()


def test_homepage_mobile_and_reduced_motion(page: Page, base_url: str):
    """Reduced-motion visitors can navigate the full page without horizontal overflow."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.emulate_media(reduced_motion="reduce")
    page.goto(base_url)
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    page.get_by_role("button", name="Open navigation").click()
    nav = page.get_by_role("navigation", name="Mobile navigation")
    expect(nav).to_be_visible()
    nav.get_by_role("link", name="For your business").click()
    expect(nav).to_have_count(0)
    expect(
        page.get_by_role(
            "heading", name="You do what you do best. We’ll take the call."
        )
    ).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="Try the day shift").click()
    expect(page.locator('[data-theme="day"]')).to_be_visible()
