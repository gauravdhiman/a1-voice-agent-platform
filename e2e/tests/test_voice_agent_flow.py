import pytest
import re
import uuid
from playwright.sync_api import Page, expect
from helpers import signin_user


def test_agent_list_view_journey(page: Page, base_url: str, step):
    """
    Test that agents are displayed correctly in the agents list view.

    Purpose:
        Verify that the agents list page loads and displays
        agent cards with correct information.

    Test Specification:
        1. Mock organization API to return test organization
        2. Mock my-agents API to return list of agents
        3. Sign in as authenticated user
        4. Navigate to agents list page
        5. Verify agent "Support Bot" is displayed in the list
        6. Verify "Active" status badge is shown

    Mocks Required:
        - /api/v1/organizations (organization data)
        - /api/v1/agents/my-agents (returns "Support Bot" agent)

    Expected Behavior:
        - Agents list loads without errors
        - Agent cards display agent name ("Support Bot")
        - Status badges show current agent state ("Active")

    Dependencies:
        - User must be authenticated (sign-in helper)
        - Agent must exist in mocked data
    """

    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"

    step("Setup: Mock organization and agents list")
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "E2E Org", "slug": "e2e-org"}}]'
    ))

    # Mock agents list response (the hook calls /my-agents)
    page.route("**/api/v1/agents/my-agents", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='''[
            {
                "id": "agent-1",
                "name": "Support Bot",
                "organization_id": "00000000-0000-0000-0000-000000000001",
                "is_active": true,
                "phone_number": "+14155550001",
                "persona": "Support Assistant",
                "tone": "Professional",
                "mission": "Help customers with their issues",
                "created_at": "2026-01-21T00:00:00Z",
                "updated_at": "2026-01-21T00:00:00Z"
            }
        ]'''
    ))

    step("Sign in and navigate to Agents page")
    signin_user(page, base_url)

    step("Go to Agents list")
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")

    step("Verify agent 'Support Bot' is visible in the list")
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=15000)
    expect(page.get_by_text("Active", exact=True)).to_be_visible()


def test_create_voice_agent_journey(page: Page, base_url: str, step):
    """
    Test creation of a new voice agent through the UI wizard.

    Purpose:
        Verify end-to-end flow of creating a new voice agent through
        the multi-step UI wizard, including form validation, navigation
        between steps, and successful creation with redirection.

    Test Specification:
        1. Mock organization API to return test organization
        2. Mock POST /api/v1/agents to simulate agent creation
        3. Sign in as authenticated user
        4. Navigate to /agents/create
        5. Fill in Basic Information step (name, persona, tone, mission)
        6. Navigate to Phone Number step
        7. Enter phone number in E.164 format
        8. Navigate to Tools step (can skip configuration)
        9. Navigate to Review step
        10. Click "Create Agent" button
        11. Verify success toast notification
        12. Verify redirection to new agent's tools page

    Mocks Required:
        - /api/v1/organizations (organization list)
        - POST /api/v1/agents (agent creation)

    Expected Behavior:
        - Agent creation wizard loads with all steps
        - Form validation works on each step
        - Navigation between steps works correctly
        - Agent is created successfully
        - User is redirected to new agent's tools page
        - Success toast appears

    Dependencies:
        - User must be authenticated
        - Organization must exist in mocked data
    """

    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"
    new_agent_id = "00000000-0000-0000-0000-000000000003"

    step("Setup: Mock organization list and agent creation endpoint")
    
    # Mock organizations list (required for organization dropdown)
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "E2E Test Org", "slug": "e2e-test-org"}}]'
    ))

    # Mock agent creation POST endpoint
    def handle_create_agent(route):
        request_body = route.request.post_data_json
        route.fulfill(
            status=201,
            content_type="application/json",
            body=f'''
            {{
                "id": "{new_agent_id}",
                "name": "{request_body.get('name', 'Test Agent')}",
                "organization_id": "{test_org_id}",
                "phone_number": "{request_body.get('phone_number', '')}",
                "persona": "{request_body.get('persona', '')}",
                "tone": "{request_body.get('tone', '')}",
                "mission": "{request_body.get('mission', '')}",
                "custom_instructions": "{request_body.get('custom_instructions', '')}",
                "is_active": true,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }}'''
        )
    
    page.route("**/api/v1/agents", handle_create_agent)

    step("Sign in and navigate to agent creation page")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/create")
    page.wait_for_load_state("networkidle")

    step("Verify agent creation wizard is displayed")
    expect(page.get_by_text("Create New Voice Agent")).to_be_visible()
    expect(page.get_by_role("heading", name="Basic Information").first).to_be_visible()

    step("Fill in Basic Information step")
    # Select organization
    page.select_option('select[name="organization_id"]', test_org_id)
    
    # Enter agent name
    page.fill('input[name="name"]', "E2E Test Support Agent")
    
    # Enter persona
    page.fill('input[name="persona"]', "Technical Support Specialist")
    
    # Select tone (Professional is default)
    page.select_option('select[name="tone"]', "Professional")
    
    # Enter mission
    page.fill('textarea[name="mission"]', "Help customers resolve technical issues efficiently")
    
    # Optional: Add custom instructions
    page.fill('textarea[name="custom_instructions"]', 
              "Always verify customer ID before accessing account details")

    step("Navigate to Phone Number step")
    page.get_by_role("button", name="Next Step").click()
    
    step("Verify Phone Number step is displayed")
    expect(page.get_by_role("heading", name="Phone Number")).to_be_visible()
    
    step("Enter phone number in E.164 format")
    page.fill('input[name="phone_number"]', "+14155551234")

    step("Navigate to Tools step")
    page.get_by_role("button", name="Next Step").click()
    
    step("Verify Tools step is displayed")
    expect(page.get_by_role("heading", name="Platform Tools")).to_be_visible()
    expect(page.get_by_text("Tools Configuration")).to_be_visible()

    step("Navigate to Review step")
    page.get_by_role("button", name="Next Step").click()
    
    step("Verify Review step displays all configured values")
    expect(page.get_by_role("heading", name="Review & Create")).to_be_visible()
    expect(page.get_by_text("E2E Test Support Agent")).to_be_visible()
    expect(page.get_by_text("+14155551234")).to_be_visible()
    expect(page.get_by_text("Technical Support Specialist")).to_be_visible()

    step("Create the agent")
    page.get_by_role("button", name="Create Agent").click()
    
    step("Verify success toast and redirection")
    # Wait for success toast
    expect(page.get_by_text("Agent created successfully!")).to_be_visible(timeout=10000)
    
    # Verify redirection to new agent's tools page
    page.wait_for_url(f"{base_url}/agents/{new_agent_id}?tab=tools", timeout=10000)
    
    step("Verification Complete: Voice agent created successfully")
