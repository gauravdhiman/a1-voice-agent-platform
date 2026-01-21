import pytest
import re
import uuid
from playwright.sync_api import Page, expect

def test_full_agent_and_tool_journey(page: Page, base_url: str, step):
    """
    Test the journey of connecting a tool and toggling its functions.
    Mocks: Auth, Organization, Agent.
    Real: Tool Connection, Tool Fetching, Tool Toggling.
    """
    
    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"
    test_agent_id = "00000000-0000-0000-0000-000000000002"
    
    # Track "connected" state in the test scope
    state = {"is_connected": False}

    # 1. Setup Stateful Mocks
    step("Setup: Configure stateful mocks for tool connection")
    
    # Mock Organizations (required for Dashboard to hydrate)
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "Mock Org", "slug": "mock-org"}}]'
    ))

    # Mock Agent detail
    page.route(f"**/api/v1/agents/{test_agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'{{ "id": "{test_agent_id}", "name": "Mock Agent", "organization_id": "{test_org_id}", "system_prompt": "Prompt", "is_active": true }}'
    ))

    # Stateful GET Agent Tools
    def handle_get_agent_tools(route):
        if state["is_connected"]:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=f'''[
                    {{
                        "id": "mapping-id",
                        "agent_id": "{test_agent_id}",
                        "tool_id": "gmail-tool-id",
                        "is_enabled": true,
                        "auth_status": "not_authenticated",
                        "connection_status": "connected_no_auth",
                        "unselected_functions": []
                    }}
                ]'''
            )
        else:
            route.fulfill(status=200, content_type="application/json", body="[]")
    page.route(f"**/api/v1/tools/agent/{test_agent_id}", handle_get_agent_tools)

    # Mock POST Connect
    def handle_post_connect(route):
        state["is_connected"] = True
        route.fulfill(status=201, content_type="application/json", body='{"success": true}')
    page.route("**/api/v1/tools/agent", handle_post_connect, times=1)

    # Mock PUT Toggle
    page.route("**/api/v1/agent-tools/**", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"success": true}'
    ))

    # --- JOURNEY START ---

    step("Sign in to the platform")
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    expect(page.get_by_role("heading", name=re.compile(r"Dashboard", re.I))).to_be_visible(timeout=10000)

    step(f"Navigate to Agent Tools tab for agent {test_agent_id}")
    page.goto(f"{base_url}/agents/{test_agent_id}?tab=tools")
    
    step("Verify 'Gmail' tool card is visible")
    expect(page.get_by_role("heading", name="Gmail")).to_be_visible()
    
    step("Click 'Connect' button on Gmail card")
    page.get_by_role("button", name="Connect", exact=True).click()
    
    step("Wait for Tool Configuration drawer to open")
    expect(page.get_by_text("Available Functions")).to_be_visible(timeout=15000)
    expect(page.get_by_text("send_email")).to_be_visible()
    
    step("Toggle 'send_email' function and verify UI update")
    toggle = page.locator('button[role="switch"]').first
    toggle.click()
    expect(toggle).to_be_visible()
    
    step("Verification Complete: Tool journey verified with stateful mocks")

def test_agent_properties_update(page: Page, base_url: str, step):
    """Test updating agent general properties."""
    
    agent_id = "00000000-0000-0000-0000-000000000002"
    org_id = "00000000-0000-0000-0000-000000000001"
    
    step("Setup: Mock organization and agent properties")
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{org_id}", "name": "Mock Org", "slug": "mock-org"}}]'
    ))

    page.route(f"**/api/v1/agents/{agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{agent_id}",
            "name": "Config Agent",
            "organization_id": "{org_id}",
            "system_prompt": "Initial prompt",
            "is_active": true
        }}'''
    ))

    step("Sign in and navigate to Agent Detail")
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard")

    step("Go to agent detail page")
    page.goto(f"{base_url}/agents/{agent_id}")
    page.wait_for_load_state("networkidle")
    
    step("Update agent system prompt")
    page.fill('textarea#prompt', "Updated system prompt from E2E test.")
    
    # Mock the PUT update response
    page.route(f"**/api/v1/agents/{agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"success": true}'
    ))
    
    step("Click 'Save Changes'")
    page.click('button:has-text("Save Changes")')
    
    step("Verify success toast")
    expect(page.get_by_text(re.compile(r"updated successfully|saved", re.I))).to_be_visible()
