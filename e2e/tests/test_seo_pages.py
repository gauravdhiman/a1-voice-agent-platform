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
    expect(page.get_by_role("heading", name=heading)).to_be_visible(timeout=15000)

    step("Verify demo and interest CTAs are present")
    expect(page.get_by_role("link", name="Request a Demo").first).to_be_visible()
    expect(page).to_have_url(re.compile(re.escape(path)))


def test_unknown_route_shows_branded_404(page: Page, base_url: str, step):
    """Dead ends offer home and demo paths, never a blank default."""
    step("Open a nonexistent route")
    page.goto(f"{base_url}/no-such-page-anywhere")

    step("Verify branded 404 with navigation")
    expect(page.get_by_role("heading", name="didn't pick up")).to_be_visible(
        timeout=15000
    )
    expect(page.get_by_role("link", name="Back to home")).to_be_visible()
    expect(page.get_by_role("link", name="Request a demo")).to_be_visible()


def test_industry_supporting_copy_has_theme_contrast(page: Page, base_url: str):
    """Shared vertical pages keep pain, outcome, and FAQ copy legible."""
    page.goto(f"{base_url}/dental")
    expect(page.get_by_role("heading", name="Sound familiar?")).to_be_visible(
        timeout=15000
    )
    pain = page.locator("main ul li").first
    pain_text = pain.locator("span")
    pain_icon = pain.locator("svg")
    outcome_copy = page.locator("main section").nth(2).locator("p").first
    faq_copy = page.locator("main section").last.locator("p").first

    for theme in ("day", "night"):
        switch = page.get_by_role("switch")
        should_be_dark = theme == "night"
        if (switch.get_attribute("aria-checked") == "true") != should_be_dark:
            switch.click()
        expect(switch).to_have_attribute("aria-checked", str(should_be_dark).lower())
        expect(page.locator(f'[data-theme="{theme}"]')).to_be_visible()
        page.wait_for_timeout(600)
        for text in (pain_text, outcome_copy, faq_copy):
            contrast = text.evaluate(
                """element => {
                    const rgb = value => {
                        const match = value.match(/rgba?\\(([^)]+)\\)/);
                        if (!match) return null;
                        const parts = match[1].split(/[,/ ]+/).filter(Boolean).map(Number);
                        return [parts[0], parts[1], parts[2], parts[3] ?? 1];
                    };
                    const luminance = color => color.slice(0, 3).map(channel => {
                        const value = channel / 255;
                        return value <= 0.04045
                            ? value / 12.92
                            : ((value + 0.055) / 1.055) ** 2.4;
                    }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
                    const foreground = rgb(getComputedStyle(element).color);
                    let node = element;
                    let background = null;
                    while (node) {
                        const color = rgb(getComputedStyle(node).backgroundColor);
                        if (color && color[3] >= 0.95) { background = color; break; }
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
                    const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
                    return {
                        ratio: (values[0] + 0.05) / (values[1] + 0.05),
                        foreground: getComputedStyle(element).color,
                        background: getComputedStyle(node).backgroundColor,
                        text: element.textContent.trim(),
                    };
                }"""
            )
            assert contrast["ratio"] >= 4.5, (
                f"{theme} mode text contrast is {contrast['ratio']:.2f}:1 "
                f"for {contrast['text']!r} ({contrast['foreground']} on "
                f"{contrast['background']})"
            )
        # Industry pain icons use the brand accent as a foreground color.
        icon_colors = pain_icon.evaluate(
            """element => {
                const root = element.closest('[data-theme]');
                const probe = document.createElement('span');
                probe.style.color = 'var(--public-accent)';
                root.append(probe);
                const expected = getComputedStyle(probe).color;
                probe.remove();
                return { actual: getComputedStyle(element).color, expected };
            }"""
        )
        assert icon_colors["actual"] == icon_colors["expected"]
