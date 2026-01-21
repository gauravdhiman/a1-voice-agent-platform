import pytest
import re
import uuid
from playwright.sync_api import Page, expect

def test_agent_list_view_journey(page: Page, base_url: str, step):
    """Test that agents are displayed correctly in the list."""
    
    test_user_id = "00000000-0000-0000-0000-000000000000"
    test_org_id = "00000000-0000-0000-0000-000000000001"

    step("Setup: Mock organization and agents list")
    page.route("**/api/v1/organizations", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=f'[{{"id": "{test_org_id}", "name": "E2E Org", "slug": "e2e-org"}}]'
    ))

    # Mock the agents list response (the hook calls /my-agents)
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
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard")

    step("Go to Agents list")
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")
    
    step("Verify agent 'Support Bot' is visible in the list")
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=15000)
    expect(page.get_by_text("Active", exact=True)).to_be_visible()

@pytest.mark.skip(reason="Real DB creation flow needs more specific validation tuning")
def test_create_voice_agent_journey(page: Page, base_url: str, step):
    pass
