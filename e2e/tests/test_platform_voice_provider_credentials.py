"""Browser coverage for platform API credentials."""

import json
import os
import re
from pathlib import Path

from helpers import signin_user
from playwright.sync_api import Page, expect


def test_platform_admin_can_save_and_remove_voice_provider_key(
    page: Page, base_url: str, step
):
    """Platform admins can rotate a key and return to its env fallback."""
    providers = {
        provider: {
            "configured": False,
            "environment_fallback_configured": provider == "google",
            "updated_at": None,
        }
        for provider in (
            "google",
            "deepgram",
            "openai",
            "cartesia",
            "cerebras",
            "openrouter",
            "fish",
        )
    }
    saved_payloads = []
    screenshot_dir = os.getenv("PLATFORM_API_CREDENTIALS_SCREENSHOT_DIR")
    if screenshot_dir:
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    def capture_review_screenshot(name: str) -> None:
        """Save a review screenshot while masking the signed-in user's email."""
        if screenshot_dir:
            page.screenshot(
                path=str(Path(screenshot_dir) / name),
                full_page=True,
                mask=[page.get_by_text("test@gmail.com", exact=True)],
                mask_color="#f8fafc",
            )

    def handle_credentials(route):
        provider = route.request.url.rstrip("/").split("/")[-1]
        method = route.request.method
        if method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"providers": providers}),
            )
            return
        if method == "PUT":
            payload = route.request.post_data_json
            saved_payloads.append(payload)
            providers[provider]["configured"] = True
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(providers[provider]),
            )
            return
        if method == "DELETE":
            providers[provider]["configured"] = False
            route.fulfill(status=204, body="")
            return
        route.continue_()

    page.route(
        re.compile(r".*/api/v1/platform/api-credentials(?:/.*)?$"),
        handle_credentials,
    )

    step("Sign in as a platform admin and open API Credentials")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/settings?section=api-credentials")
    expect(page.get_by_text("Platform API Credentials", exact=True)).to_be_visible()
    expect(page.get_by_text("Environment fallback")).to_be_visible()

    capture_review_screenshot("before.png")

    step("Save a platform Google key without displaying it again")
    page.get_by_role("button", name="Add API key").first.click()
    page.get_by_label("API key", exact=True).fill("e2e-platform-google-key")
    page.get_by_role("button", name="Save API key").click()
    expect(page.get_by_role("button", name="Update key").first).to_be_visible()
    expect(page.get_by_text("e2e-platform-google-key")).to_have_count(0)
    assert saved_payloads == [{"api_key": "e2e-platform-google-key"}]
    capture_review_screenshot("after.png")

    step("Remove the saved key and return to the environment fallback")
    page.get_by_role("button", name="Remove key").first.click()
    expect(page.get_by_role("dialog")).to_contain_text(
        "The matching environment value will then be used as a fallback"
    )
    page.get_by_role("dialog").get_by_role("button", name="Remove key").click()
    expect(
        page.get_by_text(
            "No platform API credential is stored. The matching environment "
            "value will be used as a fallback."
        )
    ).to_be_visible()
