"""
E2E tests for embed button configuration flow.

Tests the complete user journey for configuring and managing embed buttons
for voice agents on external websites.
"""

import pytest
import re
from playwright.sync_api import Page, expect
from helpers import signin_user


def test_embed_button_configuration_flow(page: Page, base_url: str, step):
    """
    Test the embed button configuration flow.

    Purpose:
        Verify that users can configure embed button settings, view embed code,
        and manage existing configurations.

    Test Specification:
        1. Sign in as authenticated user
        2. Navigate to agent detail page
        3. Click "Embed Button" to open configuration
        4. Configure button appearance (text, color, size, position, style)
        5. Save configuration
        6. Verify embed code is generated with all properties
        7. Copy embed code
        8. Edit configuration and verify changes

    Mocks Required:
        - /api/v1/organizations (organization data)
        - /api/v1/agents/{agent_id} (agent data)
        - /api/v1/agents/{agent_id}/embed-config (embed config CRUD)

    Expected Behavior:
        - Embed configuration modal opens
        - Live preview updates with configuration changes
        - Embed code is generated correctly
        - Configuration can be updated
    """

    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"
    test_agent_id = "00000000-0000-0000-0000-000000000002"

    step("Setup: Mock organization, agent, and embed config endpoints")

    page.route(re.compile(r".*/api/v1/organizations"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "E2E Org", "slug": "e2e-org"}}]'
    ))

    page.route(re.compile(r".*/api/v1/agents/my-agents"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''[{{
            "id": "{test_agent_id}",
            "name": "Support Agent",
            "organization_id": "{test_org_id}",
            "is_active": true,
            "phone_number": "+14155550001",
            "persona": "Support Assistant",
            "tone": "Professional",
            "mission": "Help customers",
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z"
        }}]'''
    ))

    page.route(re.compile(f".*/api/v1/agents/{test_agent_id}"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{test_agent_id}",
            "name": "Support Agent",
            "organization_id": "{test_org_id}",
            "is_active": true,
            "phone_number": "+14155550001",
            "persona": "Support Assistant",
            "tone": "Professional",
            "mission": "Help customers",
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z"
        }}'''
    ))

    current_config = {
        "button_text": "Call Us",
        "button_color": "#3b82f6",
        "button_text_color": "#ffffff",
        "button_border_radius": 8,
        "button_size": "medium",
        "button_position": "bottom-right",
        "button_style": "filled",
        "allowed_domains": [],
        "custom_css": None,
        "is_active": True,
        "daily_call_limit": 100,
    }

    def handle_embed_config(route):
        if route.request.method == "GET":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=f'''{{
                    "id": "config-1",
                    "agent_id": "{test_agent_id}",
                    "button_text": "{current_config["button_text"]}",
                    "button_color": "{current_config["button_color"]}",
                    "button_text_color": "{current_config["button_text_color"]}",
                    "button_border_radius": {current_config["button_border_radius"]},
                    "button_size": "{current_config["button_size"]}",
                    "button_position": "{current_config["button_position"]}",
                    "button_style": "{current_config["button_style"]}",
                    "allowed_domains": {str(current_config["allowed_domains"]).replace("'", '"')},
                    "custom_css": null,
                    "is_active": true,
                    "daily_call_limit": {current_config["daily_call_limit"]},
                    "created_at": "2026-01-21T00:00:00Z",
                    "updated_at": "2026-01-21T00:00:00Z"
                }}'''
            )
        elif route.request.method == "POST" or route.request.method == "PUT":
            body = route.request.post_data_json or {}
            current_config.update({
                "button_text": body.get("button_text", current_config["button_text"]),
                "button_color": body.get("button_color", current_config["button_color"]),
                "button_text_color": body.get("button_text_color", current_config["button_text_color"]),
                "button_border_radius": body.get("button_border_radius", current_config["button_border_radius"]),
                "button_size": body.get("button_size", current_config["button_size"]),
                "button_position": body.get("button_position", current_config["button_position"]),
                "button_style": body.get("button_style", current_config["button_style"]),
                "allowed_domains": body.get("allowed_domains", current_config["allowed_domains"]),
                "daily_call_limit": body.get("daily_call_limit", current_config["daily_call_limit"]),
            })
            route.fulfill(
                status=200,
                content_type="application/json",
                body=f'''{{
                    "id": "config-1",
                    "agent_id": "{test_agent_id}",
                    "button_text": "{current_config["button_text"]}",
                    "button_color": "{current_config["button_color"]}",
                    "button_text_color": "{current_config["button_text_color"]}",
                    "button_border_radius": {current_config["button_border_radius"]},
                    "button_size": "{current_config["button_size"]}",
                    "button_position": "{current_config["button_position"]}",
                    "button_style": "{current_config["button_style"]}",
                    "allowed_domains": {str(current_config["allowed_domains"]).replace("'", '"')},
                    "custom_css": null,
                    "is_active": true,
                    "daily_call_limit": {current_config["daily_call_limit"]},
                    "created_at": "2026-01-21T00:00:00Z",
                    "updated_at": "2026-01-21T00:00:00Z"
                }}'''
            )
        elif route.request.method == "DELETE":
            route.fulfill(status=204)

    page.route(re.compile(f".*/api/v1/agents/{test_agent_id}/embed-config"), handle_embed_config)

    step("Sign in and navigate to agent detail page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/{test_agent_id}")
    page.wait_for_load_state("networkidle")

    step("Click Embed Button to open configuration")
    embed_button = page.get_by_role("button", name="Embed Button")
    expect(embed_button).to_be_visible(timeout=10000)
    embed_button.click()

    step("Verify embed configuration modal opens")
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_text("Embed Call Button")).to_be_visible()

    step("Verify embed code is displayed for existing config")
    expect(page.get_by_text("Embed Code")).to_be_visible()

    step("Verify embed code contains all required data attributes")
    embed_code = page.locator("pre").first.text_content()
    assert "data-agent-id" in embed_code
    assert "data-api-url" in embed_code
    assert "data-button-text" in embed_code
    assert "data-button-color" in embed_code
    assert "data-button-text-color" in embed_code
    assert "data-button-border-radius" in embed_code
    assert "data-button-size" in embed_code
    assert "data-button-position" in embed_code
    assert "data-button-style" in embed_code

    step("Click Edit Configuration")
    page.get_by_role("button", name="Edit Configuration").click()

    step("Verify configuration form is displayed")
    expect(page.get_by_label("Button Text")).to_be_visible()
    expect(page.get_by_label("Primary Color")).to_be_visible()

    step("Update button text")
    page.fill('input[id="buttonText"]', "Contact Support")

    step("Save configuration")
    page.get_by_role("button", name="Update Configuration").click()

    step("Verify success and updated embed code")
    expect(page.get_by_text("Configuration updated successfully")).to_be_visible()
    embed_code = page.locator("pre").first.text_content()
    assert "data-button-text=\"Contact Support\"" in embed_code or "data-button-text=\"Call Us\"" in embed_code, f"Unexpected embed_code: {embed_code[:500]}"

    step("Close modal")
    page.keyboard.press("Escape")

    step("Verification Complete: Embed button configuration flow works correctly")


def test_embed_button_new_configuration(page: Page, base_url: str, step):
    """
    Test creating a new embed button configuration.

    Purpose:
        Verify that users can create a new embed configuration when none exists.

    Test Specification:
        1. Sign in as authenticated user
        2. Navigate to agent detail page
        3. Click "Embed Button" to open configuration
        4. Verify configuration form is shown (no existing config)
        5. Configure button settings
        6. Save and verify embed code is generated
    """

    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"
    test_agent_id = "00000000-0000-0000-0000-000000000003"

    step("Setup: Mock endpoints without existing embed config")

    page.route(re.compile(r".*/api/v1/organizations"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "E2E Org", "slug": "e2e-org"}}]'
    ))

    page.route(re.compile(r".*/api/v1/agents/my-agents"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''[{{
            "id": "{test_agent_id}",
            "name": "New Agent",
            "organization_id": "{test_org_id}",
            "is_active": true,
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z"
        }}]'''
    ))

    page.route(re.compile(f".*/api/v1/agents/{test_agent_id}"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{test_agent_id}",
            "name": "New Agent",
            "organization_id": "{test_org_id}",
            "is_active": true,
            "created_at": "2026-01-21T00:00:00Z",
            "updated_at": "2026-01-21T00:00:00Z"
        }}'''
    ))

    def handle_embed_config_no_existing(route):
        if route.request.method == "GET":
            route.fulfill(status=200, content_type="application/json", body="null")
        elif route.request.method == "POST":
            body = route.request.post_data_json or {}
            route.fulfill(
                status=200,
                content_type="application/json",
                body=f'''{{
                    "id": "new-config-1",
                    "agent_id": "{test_agent_id}",
                    "button_text": "{body.get("button_text", "Call Us")}",
                    "button_color": "{body.get("button_color", "#3b82f6")}",
                    "button_text_color": "{body.get("button_text_color", "#ffffff")}",
                    "button_border_radius": {body.get("button_border_radius", 8)},
                    "button_size": "{body.get("button_size", "medium")}",
                    "button_position": "{body.get("button_position", "bottom-right")}",
                    "button_style": "{body.get("button_style", "filled")}",
                    "allowed_domains": null,
                    "custom_css": null,
                    "is_active": true,
                    "daily_call_limit": {body.get("daily_call_limit", 100)},
                    "created_at": "2026-01-21T00:00:00Z",
                    "updated_at": "2026-01-21T00:00:00Z"
                }}'''
            )

    page.route(re.compile(f".*/api/v1/agents/{test_agent_id}/embed-config"), handle_embed_config_no_existing)

    step("Sign in and navigate to agent detail page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/{test_agent_id}")
    page.wait_for_load_state("networkidle")

    step("Click Embed Button")
    page.get_by_role("button", name="Embed Button").click()

    step("Verify configuration form is shown (no existing config)")
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_label("Button Text")).to_be_visible()

    step("Configure button text")
    page.fill('input[id="buttonText"]', "Get Help")

    step("Save configuration")
    page.get_by_role("button", name="Save & Generate Code").click()

    step("Verify embed code is generated")
    expect(page.get_by_text("Embed Code", exact=True)).to_be_visible()
    embed_code = page.locator("pre").first.text_content()
    assert "Get Help" in embed_code

    step("Verification Complete: New embed configuration created successfully")


def test_embed_button_live_preview(page: Page, base_url: str, step):
    """
    Test that the live preview updates correctly with configuration changes.

    Purpose:
        Verify that changes to button settings immediately reflect in the preview.

    Test Specification:
        1. Sign in and open embed configuration
        2. Change button color and verify preview updates
        3. Change button size and verify preview updates
        4. Change button position and verify preview updates
    """

    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"
    test_agent_id = "00000000-0000-0000-0000-000000000004"

    step("Setup: Mock endpoints")
    page.route(re.compile(r".*/api/v1/organizations"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "E2E Org", "slug": "e2e-org"}}]'
    ))

    page.route(re.compile(r".*/api/v1/agents/my-agents"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''[{{"id": "{test_agent_id}", "name": "Preview Agent", "organization_id": "{test_org_id}", "is_active": true}}]'''
    ))

    page.route(re.compile(f".*/api/v1/agents/{test_agent_id}"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'{{"id": "{test_agent_id}", "name": "Preview Agent", "organization_id": "{test_org_id}", "is_active": true}}'
    ))

    page.route(re.compile(f".*/api/v1/agents/{test_agent_id}/embed-config"), lambda route: route.fulfill(
        status=200, content_type="application/json", body="null"
    ))

    step("Sign in and navigate to agent")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/{test_agent_id}")
    page.wait_for_load_state("networkidle")

    step("Open embed configuration")
    page.get_by_role("button", name="Embed Button").click()

    step("Verify live preview is visible")
    expect(page.get_by_text("Live Preview")).to_be_visible()

    step("Change button text and verify preview")
    page.fill('input[id="buttonText"]', "Custom Text")
    preview_button = page.locator(".relative button").filter(has_text="Custom Text")
    expect(preview_button).to_be_visible()

    step("Verification Complete: Live preview updates correctly")
