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
                "system_prompt": "Prompt 1",
                "created_by": "user-1",
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


@pytest.mark.skip(reason="Real DB creation flow needs more specific validation tuning")
def test_create_voice_agent_journey(page: Page, base_url: str, step):
    """
    Test creation of a new voice agent (currently skipped).

    Purpose:
        Verify end-to-end flow of creating a new voice agent through
        the UI, including form validation and success handling.

    Test Specification:
        [Test is currently skipped pending validation tuning]

    Mocks Required:
        [To be defined when test is implemented]

    Expected Behavior:
        [To be defined when test is implemented]

    Dependencies:
        - [To be defined when test is implemented]
    """
    pass
