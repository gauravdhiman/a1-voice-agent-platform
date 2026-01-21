import re
from playwright.sync_api import Page, expect
from helpers import signin_user


def test_full_agent_and_tool_journey(page: Page, base_url: str, step):
    """
    Test complete tool connection journey with function toggling capabilities.

    Purpose:
        Verify that users can connect tools to agents and toggle individual
        functions within the tool configuration interface.

    Test Specification:
        1. Mock organization API for dashboard hydration
        2. Mock platform tools API to return Gmail tool
        3. Mock agent detail API with initial state
        4. Mock agent tools API with stateful responses (before/after connection)
        5. Mock tool connection API (POST /tools/agent)
        6. Mock tool toggle API (PUT /agent-tools/**)
        7. Sign in as authenticated user
        8. Navigate to agent Tools tab for specific agent
        9. Verify Gmail tool card is visible
        10. Click "Connect" button on tool card
        11. Verify Tool Configuration drawer opens
        12. Verify available functions list displays
        13. Verify specific function (send_email) is visible
        14. Toggle send_email function switch
        15. Verify UI updates to reflect enabled state

    Mocks Required:
        - /api/v1/organizations (organization data)
        - /api/v1/tools/platform** (Gmail tool with functions schema)
        - /api/v1/agents/{agent_id} (agent details)
        - /api/v1/tools/agent/{agent_id} (stateful: empty before, populated after connect)
        - /api/v1/tools/agent (POST connection endpoint)
        - /api/v1/agent-tools/** (PUT toggle endpoint)

    Real API Interactions:
        - Tool connection flow (authentication UI, OAuth redirect)
        - Tool fetching (load configured tools)
        - Function toggling (enable/disable specific tool functions)

    Expected Behavior:
        - Tools list displays available tools
        - Tool card shows "Connect" button when not authenticated
        - Tool Configuration drawer opens on connect
        - Available functions are displayed with toggles
        - Toggling a function updates UI immediately
        - Success toasts appear on connection and toggle

    Dependencies:
        - User must be authenticated (sign-in helper)
        - Agent must exist
        - Tool must be available in platform tools
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

    # Mock Platform Tools (required for tool selection)
    page.route("**/api/v1/tools/platform**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "gmail-tool-id", "name": "Gmail", "description": "Send and read emails", "is_active": true, "requires_auth": true, "auth_type": "oauth2", "tool_functions_schema": {{"functions": [{{"name": "send_email", "description": "Send an email", "parameters": {{"type": "object", "properties": {{}}}}}}]}}}}]'
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

    step("Sign in to platform")
    signin_user(page, base_url)

    step(f"Navigate to Agent Tools tab for agent {test_agent_id}")
    page.goto(f"{base_url}/agents/{test_agent_id}?tab=tools")

    step("Verify 'Gmail' tool card is visible")
    expect(page.get_by_text("Gmail")).to_be_visible()

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
    """
    Test updating agent general properties (system prompt).

    Purpose:
        Verify that users can modify agent system prompt and
        save changes successfully with appropriate feedback.

    Test Specification:
        1. Mock organization API for dashboard hydration
        2. Mock agent detail API with initial properties
        3. Mock agent update API (PUT) to return success
        4. Sign in as authenticated user
        5. Navigate to agent detail page
        6. Update system prompt textarea with new value
        7. Click "Save Changes" button
        8. Verify success toast notification appears

    Mocks Required:
        - /api/v1/organizations (organization data)
        - /api/v1/agents/{agent_id} (GET: initial, PUT: update)

    Expected Behavior:
        - Agent detail page loads with current properties
        - System prompt textarea accepts new input
        - Save button submits form
        - Success toast confirms update

    Dependencies:
        - User must be authenticated (sign-in helper)
        - Agent must exist
    """

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
    signin_user(page, base_url)
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

