"""Epic B: vertical SEO pages render with demo and funnel CTAs."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.parametrize(
    "path,heading",
    [
        ("/dental", "Your dental practice, always answering"),
        ("/hvac", "Every service call answered, every job captured"),
    ],
)
def test_vertical_page_renders_funnel_ctas(
    page: Page, base_url: str, step, path: str, heading: str
):
    """Each vertical page shows its H1 plus demo and request-demo paths."""
    step(f"Open {path}")
    page.goto(f"{base_url}{path}")
    expect(page.get_by_role("heading", name=heading)).to_be_visible(
        timeout=15000
    )

    step("Verify demo and interest CTAs are present")
    expect(page.get_by_role("link", name="Request a Demo").first).to_be_visible()
    expect(page).to_have_url(re.compile(re.escape(path)))


def test_unknown_route_shows_branded_404(
    page: Page, base_url: str, step
):
    """Dead ends offer home and demo paths, never a blank default."""
    step("Open a nonexistent route")
    page.goto(f"{base_url}/no-such-page-anywhere")

    step("Verify branded 404 with navigation")
    expect(page.get_by_role("heading", name="didn't pick up")).to_be_visible(
        timeout=15000
    )
    expect(page.get_by_role("link", name="Back to home")).to_be_visible()
    expect(page.get_by_role("link", name="Request a demo")).to_be_visible()
