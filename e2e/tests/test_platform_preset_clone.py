"""Browser coverage for copying a platform-admin voice preset."""

import json
import re

from playwright.sync_api import Page, expect

from helpers import signin_user


SOURCE_PRESET = {
    "id": "preset-source",
    "name": "Support Voice",
    "description": "A calm voice for support calls.",
    "config": {
        "engine_mode": "realtime",
        "provider": "google",
        "model": "gemini-2.5-flash-native-audio-preview-12-2025",
        "voice": "Puck",
        "temperature": 0.7,
        "silence_duration_ms": 500,
        "prefix_padding_ms": 200,
        "params": {},
    },
    "is_published": True,
    "credential_source": "organization",
    "preset_type": "realtime",
    "is_default": False,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_platform_admin_can_copy_preset_into_draft(page: Page, base_url: str, step):
    """Copying opens the author drawer and submits a new, unpublished preset."""
    created_payloads = []

    def handle_presets(route):
        if route.request.method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps([SOURCE_PRESET]),
            )
            return

        if route.request.method == "POST":
            created_payloads.append(route.request.post_data_json)
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        **SOURCE_PRESET,
                        "id": "preset-copy",
                        "name": "Support Voice - Premium",
                        "description": "A premium support voice.",
                        "is_published": False,
                    }
                ),
            )
            return

        route.continue_()

    page.route(
        re.compile(r".*/api/v1/presets(?:/.*)?(?:\?.*)?$"),
        handle_presets,
    )

    step("Sign in and open the platform voice preset catalog")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/presets")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Support Voice", exact=True)).to_be_visible()

    step("Copy the existing preset")
    page.get_by_role("button", name="Copy Support Voice").click()
    expect(
        page.get_by_role("heading", name="Create voice preset")
    ).to_be_visible()
    expect(page.locator("#preset-name")).to_have_value("Copy of Support Voice")
    expect(page.locator("#preset-description")).to_have_value(
        "A calm voice for support calls."
    )

    step("Edit the copied fields and save the new preset as a draft")
    page.locator("#preset-name").fill("Support Voice - Premium")
    page.locator("#preset-description").fill("A premium support voice.")
    save_draft = page.get_by_role("button", name="Save draft")
    expect(save_draft).to_be_enabled()
    with page.expect_response(
        re.compile(r".*/api/v1/presets/?(?:\?.*)?$")
    ) as response_info:
        save_draft.click()

    assert response_info.value.ok
    expect(page.get_by_text("Voice preset catalog", exact=True)).to_be_visible()
    assert created_payloads == [
        {
            "name": "Support Voice - Premium",
            "description": "A premium support voice.",
            "config": SOURCE_PRESET["config"],
            "is_published": False,
            "credential_source": "organization",
        }
    ]


def test_platform_admin_can_publish_and_select_platform_default(
    page: Page, base_url: str, step
):
    """A platform profile can become default; org-key profiles cannot."""
    current_default = {
        **SOURCE_PRESET,
        "id": "preset-default",
        "name": "Current Default",
        "description": "Current platform default.",
        "credential_source": "platform",
        "is_default": True,
    }
    organization_preset = {**SOURCE_PRESET, "id": "org-keys-preset"}
    presets = [current_default, organization_preset]
    created_payloads = []
    default_selections = []

    def handle_presets(route):
        path = route.request.url.split("/api/v1/presets", 1)[-1].split("?", 1)[0]
        method = route.request.method
        if method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(presets),
            )
            return
        if method == "POST" and path in ("", "/"):
            payload = route.request.post_data_json
            created_payloads.append(payload)
            created = {
                **SOURCE_PRESET,
                **payload,
                "id": "platform-preset",
                "is_published": True,
                "is_default": False,
            }
            presets.append(created)
            route.fulfill(status=201, content_type="application/json", body=json.dumps(created))
            return
        if method == "POST" and path == "/platform-preset/default":
            default_selections.append(path)
            for preset in presets:
                preset["is_default"] = preset["id"] == "platform-preset"
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(next(preset for preset in presets if preset["id"] == "platform-preset")),
            )
            return
        route.continue_()

    page.route(re.compile(r".*/api/v1/presets(?:/.*)?(?:\?.*)?$"), handle_presets)

    step("Sign in and verify organization-key profiles cannot become the default")
    signin_user(page, base_url)
    page.goto(f"{base_url}/platform/presets")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Make default")).to_have_count(0)

    step("Create and publish a platform-managed voice profile")
    page.get_by_role("button", name="Create new preset").click()
    page.locator("#preset-name").fill("Platform Realtime")
    page.locator("#preset-description").fill("Managed by 24x7 AI.")
    page.locator("#preset-credential-source").select_option("platform")
    page.get_by_role("button", name="Publish", exact=True).click()

    expect(page.get_by_text("Platform Realtime", exact=True)).to_be_visible()
    assert created_payloads[0]["credential_source"] == "platform"
    assert created_payloads[0]["is_published"] is True

    step("Select the new profile as the platform default")
    page.get_by_role("button", name="Make default").click()
    expect(page.get_by_text("Default", exact=True)).to_be_visible()
    assert default_selections == ["/platform-preset/default"]
