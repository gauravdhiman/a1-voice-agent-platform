"""Browser coverage for organization OAuth notification preferences."""

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
        "sms_enabled": False,
        "telegram_chat_id": None,
        "telegram_enabled": False,
        "sms_sender_configured": True,
        "telegram_bot_configured": True,
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
            settings.update(payload)
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
    expect(page.get_by_role("link", name="Organization", exact=True)).to_be_visible()
    step("Open the notification preferences tab")
    page.goto(f"{base_url}/organization?tab=notifications")
    page.wait_for_load_state("networkidle")

    expect(page.get_by_role("tab", name="Notifications")).to_be_visible()
    expect(page.get_by_text("SMS provider ready")).to_be_visible()
    expect(page.get_by_text("Telegram bot ready")).to_be_visible()

    page.get_by_role("textbox", name="Additional alert email").fill(
        "operations@example.com"
    )
    page.get_by_role("textbox", name="Phone number").fill("+14155550123")
    page.get_by_role("switch", name="Enable SMS alerts").click()
    page.get_by_role("textbox", name="Chat ID or channel username").fill(
        "-1001234567890"
    )
    page.get_by_role("switch", name="Enable Telegram alerts").click()

    step("Save email, SMS, and Telegram destinations")
    page.get_by_role("button", name="Save notification settings").click()
    expect(page.get_by_role("status")).to_contain_text(
        "Organization notification settings saved."
    )
    assert saved_payloads == [
        {
            "alert_email": "operations@example.com",
            "sms_phone": "+14155550123",
            "sms_enabled": True,
            "telegram_chat_id": "-1001234567890",
            "telegram_enabled": True,
        }
    ]

    step("Reload and verify saved destinations remain selected")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("textbox", name="Additional alert email")).to_have_value(
        "operations@example.com"
    )
    expect(page.get_by_role("textbox", name="Phone number")).to_have_value(
        "+14155550123"
    )
    expect(
        page.get_by_role("textbox", name="Chat ID or channel username")
    ).to_have_value("-1001234567890")
    expect(page.get_by_role("switch", name="Enable SMS alerts")).to_have_attribute(
        "aria-checked", "true"
    )
    expect(page.get_by_role("switch", name="Enable Telegram alerts")).to_have_attribute(
        "aria-checked", "true"
    )
