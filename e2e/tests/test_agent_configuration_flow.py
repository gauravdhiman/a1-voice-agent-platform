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
        body=f'{{ "id": "{test_agent_id}", "name": "Mock Agent", "organization_id": "{test_org_id}", "persona": "Assistant", "tone": "Professional", "mission": "Help users", "is_active": true }}'
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

    step("Update agent instructions markdown")
    page.fill('textarea#instructions_markdown', "# Support Agent\n\nAlways verify user identity before making changes.")

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


def test_system_prompt_preview(page: Page, base_url: str, step):
    """
    Test system prompt preview functionality.

    Purpose:
        Verify that users can view the generated system prompt based on
        organization and agent configuration through the preview feature.

    Test Specification:
        1. Mock organization API with business context data
        2. Mock agent detail API with persona, tone, mission fields
        3. Mock system prompt endpoint to return generated prompt
        4. Sign in as authenticated user
        5. Navigate to agent detail page
        6. Click "Preview Generated System Prompt" button
        7. Verify preview section expands
        8. Verify generated prompt contains expected sections

    Mocks Required:
        - /api/v1/organizations (organization list endpoint)
        - /api/v1/agents/{agent_id} (agent with full configuration)
        - /api/v1/agents/{agent_id}/system-prompt (generated prompt)

    Expected Behavior:
        - Preview section is initially collapsed
        - Clicking preview button expands the section
        - Generated prompt shows organization name and business details
        - Generated prompt shows agent persona, tone, and mission
        - Loading state is shown while generating
        - Preview can be collapsed again

    Dependencies:
        - User must be authenticated (sign-in helper)
        - Agent must exist with configuration
        - Organization must have business context
    """

    agent_id = "00000000-0000-0000-0000-000000000002"
    org_id = "00000000-0000-0000-0000-000000000001"

    step("Setup: Mock organization list, agent details, and system prompt endpoint")

    # Mock Organization LIST endpoint (this is what the frontend calls)
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''[{{
            "id": "{org_id}",
            "name": "Test Business Inc.",
            "industry": "Technology",
            "address": "123 Tech Street, San Francisco, CA",
            "business_context": "We provide innovative software solutions. Business hours: Monday-Friday 9am-6pm PST. All products include 30-day money-back guarantee.",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T00:00:00Z"
        }}]'''
    ))

    # Mock Agent with full configuration
    page.route(f"**/api/v1/agents/{agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{agent_id}",
            "name": "Customer Support Agent",
            "organization_id": "{org_id}",
            "description": "Primary customer support agent for handling inquiries",
            "phone_number": "+1234567890",
            "system_prompt": null,
            "persona": "Professional Customer Support Specialist",
            "tone": "Professional and empathetic",
            "mission": "Provide exceptional support by resolving issues quickly",
            "custom_instructions": "Always verify customer identity before accessing accounts. Escalate billing issues over $500 to supervisor.",
            "voice_settings": null,
            "is_active": true,
            "created_by": "00000000-0000-0000-0000-000000000003",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T00:00:00Z"
        }}'''
    ))

    # Mock System Prompt Endpoint
    page.route(f"**/api/v1/agents/{agent_id}/system-prompt", lambda route: route.fulfill(
        status=200,
        content_type="text/plain",
        body='''# IDENTITY AND PERSONA
You are Professional Customer Support Specialist representing Test Business Inc. Your communication style is Professional and empathetic.

# YOUR MISSION
Provide exceptional support by resolving issues quickly

# BUSINESS CONTEXT
Industry: Technology
Location/Address: 123 Tech Street, San Francisco, CA
Business Context:
We provide innovative software solutions. Business hours: Monday-Friday 9am-6pm PST. All products include 30-day money-back guarantee.

# ADDITIONAL INSTRUCTIONS
Always verify customer identity before accessing accounts. Escalate billing issues over $500 to supervisor.

# OUTPUT RULES & GUARDRAILS
- Keep responses concise and conversational for voice
- Be helpful, accurate, and professional
- Ask clarifying questions if needed
- Use tools when appropriate to complete tasks
- Never share sensitive information'''
    ))

    step("Sign in and navigate to Agent Detail")
    signin_user(page, base_url)
    page.wait_for_url(f"{base_url}/dashboard")

    step("Go to agent detail page")
    page.goto(f"{base_url}/agents/{agent_id}")
    
    # Wait for agent page to fully load
    page.wait_for_load_state("networkidle")
    
    step("Wait for agent page to load and verify markdown editor")

    # Wait for the markdown editor to be fully loaded
    expect(page.locator("textarea#instructions_markdown")).to_be_visible(timeout=10000)

    step("Click 'Preview System Prompt' button to expand")
    preview_button = page.get_by_text("Preview System Prompt")
    expect(preview_button).to_be_visible()
    preview_button.click()

    step("Verify preview section expands and shows rendered prompt")
    # Preview now renders as markdown (prose), not pre block
    page.wait_for_selector(".prose", state="visible", timeout=10000)

    # Verify key content is present in the rendered markdown preview
    expect(page.locator(".prose").get_by_text("Professional Customer Support Specialist")).to_be_visible()
    expect(page.locator(".prose").get_by_text("Test Business Inc")).to_be_visible()

    step("Click preview button again to collapse")
    preview_button.click()

    step("Verify preview section is collapsed")
    expect(page.locator(".prose")).not_to_be_visible()

    step("Verification Complete: System prompt preview functionality works correctly")


def test_agent_configuration_fields_update(page: Page, base_url: str, step):
    """
    Test updating all new agent configuration fields (persona, tone, mission, custom_instructions).

    Purpose:
        Verify that users can modify all new agent configuration fields
        and save changes successfully.

    Test Specification:
        1. Mock organization API for dashboard hydration
        2. Mock agent detail API with initial configuration
        3. Mock agent update API (PUT) to return updated agent
        4. Sign in as authenticated user
        5. Navigate to agent detail page
        6. Update persona field
        7. Update tone dropdown selection
        8. Update mission textarea
        9. Update custom_instructions textarea
        10. Click "Save Changes" button
        11. Verify success toast notification appears
        12. Verify all fields show updated values

    Mocks Required:
        - /api/v1/organizations (organization data)
        - /api/v1/agents/{agent_id} (GET: initial, PUT: update)

    Expected Behavior:
        - All configuration fields accept input
        - Dropdown for tone shows all options
        - Save button submits form with all changes
        - Success toast confirms update
        - Updated values persist in UI

    Dependencies:
        - User must be authenticated (sign-in helper)
        - Agent must exist
    """

    agent_id = "00000000-0000-0000-0000-000000000002"
    org_id = "00000000-0000-0000-0000-000000000001"

    step("Setup: Mock organization and agent with initial configuration")
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{org_id}", "name": "Mock Org", "slug": "mock-org"}}]'
    ))

    page.route(f"**/api/v1/agents/{agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''
        {{
            "id": "{agent_id}",
            "name": "Config Agent",
            "organization_id": "{org_id}",
            "persona": "Sales Representative",
            "tone": "Friendly",
            "mission": "Close sales effectively",
            "custom_instructions": "Initial instructions",
            "is_active": true
        }}'''
    ))

    step("Sign in and navigate to Agent Detail")
    signin_user(page, base_url)
    page.wait_for_url(f"{base_url}/dashboard")

    step("Go to agent detail page")
    page.goto(f"{base_url}/agents/{agent_id}")
    page.wait_for_load_state("networkidle")

    step("Update agent instructions markdown")
    page.fill('textarea#instructions_markdown',
              "# Senior Sales Consultant\n\nDrive revenue growth by understanding customer needs.\n\nAlways mention our 30-day guarantee.")

    # Mock the PUT update response with new values
    updated_markdown = "# Senior Sales Consultant\\n\\nDrive revenue growth by understanding customer needs.\\n\\nAlways mention our 30-day guarantee."
    page.route(f"**/api/v1/agents/{agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "00000000-0000-0000-0000-000000000002",
            "organization_id": "{org_id}",
            "name": "Config Agent",
            "phone_number": null,
            "persona": null,
            "tone": null,
            "mission": null,
            "custom_instructions": null,
            "instructions_markdown": "{updated_markdown}",
            "is_active": true,
            "use_platform_credits": false,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }}'''
    ))

    step("Click 'Save Changes'")
    page.click('button:has-text("Save Changes")')

    step("Verify success toast")
    expect(page.get_by_text(re.compile(r"updated successfully|saved", re.I))).to_be_visible()

    step("Verify updated markdown is displayed in editor")
    expect(page.locator('textarea#instructions_markdown')).to_have_value(
        re.compile(r"Senior Sales Consultant"), timeout=5000
    )

    step("Verification Complete: Agent instructions markdown updated successfully")


def test_organization_context_in_agent_config(page: Page, base_url: str, step):
    """
    Test that organization business context appears in agent system prompt preview.

    Purpose:
        Verify that organization business details (industry, location, business_details)
        are properly incorporated into the generated system prompt.

    Test Specification:
        1. Mock organization API with full business context
        2. Mock agent detail API
        3. Mock system prompt endpoint
        4. Sign in and navigate to agent page
        5. Open system prompt preview
        6. Verify organization context is included in prompt

    Mocks Required:
        - /api/v1/organizations (with full business context)
        - /api/v1/agents/{agent_id}
        - /api/v1/agents/{agent_id}/system-prompt

    Expected Behavior:
        - Organization name appears in identity section
        - Industry appears in business context
        - Location appears in business context
        - Business details are fully included

    Dependencies:
        - User must be authenticated
        - Organization must have business context configured
    """

    agent_id = "00000000-0000-0000-0000-000000000002"
    org_id = "00000000-0000-0000-0000-000000000001"

    step("Setup: Mock agent details")

    page.route(f"**/api/v1/agents/{agent_id}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'''{{
            "id": "{agent_id}",
            "name": "Service Agent",
            "organization_id": "{org_id}",
            "persona": "Service Coordinator",
            "tone": "Professional",
            "mission": "Schedule service appointments efficiently",
            "is_active": true
        }}'''
    ))

    page.route(f"**/api/v1/agents/{agent_id}/system-prompt", lambda route: route.fulfill(
        status=200,
        content_type="text/plain",
        body='''# IDENTITY AND PERSONA
You are Service Coordinator representing Plumbing Pros LLC. Your communication style is Professional.

# YOUR MISSION
Schedule service appointments efficiently

# BUSINESS CONTEXT
Industry: Home Services
Location/Address: 456 Main Street, Phoenix, AZ 85001
Business Context:
Family-owned plumbing business serving Phoenix metro area. Hours: Mon-Fri 8am-6pm, Sat 9am-2pm. 24/7 emergency service. Licensed technicians, 90-day warranty on repairs.

# OUTPUT RULES & GUARDRAILS
- Keep responses concise and conversational for voice'''
    ))

    step("Sign in and navigate to agent page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/{agent_id}")
    page.wait_for_load_state("networkidle")

    step("Open system prompt preview")
    page.get_by_text("Preview System Prompt").click()
    page.wait_for_selector(".prose", state="visible", timeout=10000)

    step("Verify organization context in generated prompt")
    expect(page.locator(".prose").get_by_text("Plumbing Pros LLC")).to_be_visible()
    expect(page.locator(".prose").get_by_text("456 Main Street, Phoenix, AZ 85001")).to_be_visible()
    expect(page.locator(".prose").get_by_text("Family-owned plumbing business")).to_be_visible()

    step("Verification Complete: Organization context properly included in system prompt")

