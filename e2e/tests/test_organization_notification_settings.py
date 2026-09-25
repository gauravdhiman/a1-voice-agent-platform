"""Browser coverage for organization critical notification settings."""

import json
import re

from helpers import signin_user
from playwright.sync_api import Page, expect

ORG_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000000"


def test_org_admin_can_save_oauth_notification_destinations(
    page: Page, base_url: str, step
):
    """An org admin can configure and reload all supported recovery destinations."""
    settings = {
        "organization_id": ORG_ID,
        "alert_email": None,
        "sms_phone": None,
        "telegram_chat_id": None,
        "telegram_bot_configured": False,
        "updated_by": None,
        "created_at": "2026-01-21T00:00:00Z",
        "updated_at": "2026-01-21T00:00:00Z",
    }
    saved_payloads = []

    page.route(
        re.compile(r".*/api/v1/auth/me.*"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": USER_ID,
                    "email": "org-admin@example.com",
                    "first_name": "Org",
                    "last_name": "Admin",
                    "current_organization_id": ORG_ID,
                    "permissions": {"*": ["*"]},
                    "has_organizations": True,
                    "roles": [
                        {
                            "id": "org-admin-role",
                            "user_id": USER_ID,
                            "role_id": "org-admin",
                            "organization_id": ORG_ID,
                            "role": {
                                "id": "org-admin",
                                "name": "org_admin",
                                "description": "Organization administrator",
                                "is_system_role": True,
                                "permissions": [],
                            },
                        }
                    ],
                }
            ),
        ),
    )
    page.route(
        re.compile(rf".*/api/v1/organizations/{ORG_ID}(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": ORG_ID,
                    "name": "Test Organization",
                    "slug": "test-organization",
                    "is_active": True,
                    "onboarding_completed": True,
                    "created_at": "2026-01-21T00:00:00Z",
                    "updated_at": "2026-01-21T00:00:00Z",
                    "industry": "Other",
                    "timezone": "America/Phoenix",
                }
            ),
        ),
    )

    def handle_settings(route):
        if route.request.method == "PUT":
            payload = route.request.post_data_json
            saved_payloads.append(payload)
            settings.update(
                {
                    key: value
                    for key, value in payload.items()
                    if key != "telegram_bot_token"
                }
            )
            if "telegram_bot_token" in payload:
                settings["telegram_bot_configured"] = bool(
                    payload["telegram_bot_token"]
                )
            settings["updated_by"] = USER_ID
            settings["updated_at"] = "2026-01-22T00:00:00Z"

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(settings),
        )

    page.route(
        re.compile(
            rf".*/api/v1/notifications/organizations/{ORG_ID}/settings(?:\?.*)?$"
        ),
        handle_settings,
    )

    step("Sign in as an organization administrator")
    signin_user(page, base_url, wait_for_dashboard=False)
    expect(page).to_have_url(re.compile(r"/dashboard$"), timeout=10000)
    step("Open the saved notification deep link")
    page.goto(f"{base_url}/organization?org_id={ORG_ID}&tab=notifications")
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/organization\?.*tab=notifications"))
    expect(page.get_by_role("tab", name="Notifications")).to_have_attribute(
        "aria-selected", "true"
    )
    expect(page.get_by_text("Critical notifications")).to_be_visible()
    expect(
        page.get_by_text(re.compile("important updates about your organization"))
    ).to_be_visible()
    expect(page.get_by_role("switch")).to_have_count(0)

    step("Check settings navigation across supported viewport sizes")
    for viewport in (
        {"width": 320, "height": 720},
        {"width": 390, "height": 844},
        {"width": 768, "height": 1024},
        {"width": 1024, "height": 768},
        {"width": 1366, "height": 900},
        {"width": 1920, "height": 1080},
    ):
        page.set_viewport_size(viewport)
        expect(page.get_by_role("tab", name="General")).to_be_visible()
        expect(page.get_by_role("tab", name="API Credentials")).to_be_visible()
        expect(page.get_by_role("tab", name="Public page")).to_be_visible()
        expect(page.get_by_role("tab", name="Notifications")).to_be_visible()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth"
        ), f"Document overflows at viewport {viewport}"
        tab_list = page.get_by_role("tablist", name="Organization settings")
        tab_metrics = tab_list.evaluate(
            """element => {
              const active = element.querySelector('[role="tab"][aria-selected="true"]');
              const listRect = element.getBoundingClientRect();
              const activeRect = active.getBoundingClientRect();
              return {
                clientWidth: element.clientWidth,
                scrollWidth: element.scrollWidth,
                activeLeft: activeRect.left,
                activeRight: activeRect.right,
                listLeft: listRect.left,
                listRight: listRect.right,
              };
            }"""
        )
        assert tab_metrics["clientWidth"] <= viewport["width"]
        assert tab_metrics["scrollWidth"] == tab_metrics["clientWidth"], (
            f"Settings tabs should fit their responsive layout at {viewport}: "
            f"{tab_metrics}"
        )
        assert tab_metrics["activeLeft"] >= tab_metrics["listLeft"]
        assert tab_metrics["activeRight"] <= tab_metrics["listRight"]

    page.set_viewport_size({"width": 1280, "height": 720})
    page.screenshot(path="/tmp/org-notification-settings-desktop.png", full_page=True)

    page.get_by_role("textbox", name="Additional email address").fill(
        "operations@example.com"
    )
    page.get_by_role("textbox", name="Phone number").fill("+14155550123")
    page.get_by_role("textbox", name="Chat ID or channel username").fill(
        "-1001234567890"
    )
    page.get_by_role("textbox", name="Telegram bot token").fill(
        "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    )

    step("Save email, SMS, and Telegram destinations")
    page.get_by_role("button", name="Save notification settings").click()
    expect(page.get_by_role("status")).to_contain_text("Notification settings saved.")
    assert saved_payloads == [
        {
            "alert_email": "operations@example.com",
            "sms_phone": "+14155550123",
            "telegram_chat_id": "-1001234567890",
            "telegram_bot_token": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
        }
    ]

    step("Reload and verify saved destinations remain selected")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("textbox", name="Additional email address")).to_have_value(
        "operations@example.com"
    )
    expect(page.get_by_role("textbox", name="Phone number")).to_have_value(
        "+14155550123"
    )
    expect(
        page.get_by_role("textbox", name="Chat ID or channel username")
    ).to_have_value("-1001234567890")
    expect(page.get_by_text("Token saved")).to_be_visible()
    expect(page.get_by_role("textbox", name="Telegram bot token")).to_have_value("")

    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path="/tmp/org-notification-settings-mobile.png", full_page=True)
