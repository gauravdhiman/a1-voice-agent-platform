import pytest
import re
from playwright.sync_api import Page, expect

def test_create_voice_agent_journey(page: Page, base_url: str):
    """Test the complete journey of creating a voice agent."""
    
    # 1. Sign in (Mocked)
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    
    # 2. Navigate to Voice Agents page
    page.goto(f"{base_url}/agents")
    expect(page.get_by_role("heading", name=re.compile(r"Voice Agents", re.I))).to_be_visible()

    # 3. Start creation process
    page.click('button:has-text("New Agent")')
    expect(page).to_have_url(re.compile(r".*/agents/create"))

    # 4. Stage 1: Basic Information
    # The organization dropdown should have "Mock Org" from our conftest mocks
    page.select_option('select', label="Mock Org")
    page.fill('input[placeholder*="Support Agent"]', "E2E Test Agent")
    page.fill('textarea', "This is a system prompt for the E2E test agent. It must be at least ten characters long.")
    page.click('button:has-text("Next Step")')

    # 5. Stage 2: Phone Number
    page.fill('input[placeholder="+1234567890"]', "+14155551234")
    page.click('button:has-text("Next Step")')

    # 6. Stage 3: Tools (Information stage)
    page.click('button:has-text("Next Step")')

    # 7. Stage 4: Review & Create
    expect(page.get_by_text("E2E Test Agent", exact=True)).to_be_visible()
    
    # Mock the POST response for agent creation
    test_agent_id = "00000000-0000-0000-0000-000000000002"
    page.route("**/api/v1/agents", lambda route: route.fulfill(
        status=201,
        content_type="application/json",
        body=f'{{"id": "{test_agent_id}", "name": "E2E Test Agent", "is_active": true}}'
    ))

    page.click('button:has-text("Create Agent")')

    # 8. Verify Success and Redirection
    # Wait for navigation and check URL
    page.wait_for_url(re.compile(rf".*/agents/{test_agent_id}.*"), timeout=15000)
    expect(page.get_by_text("Agent created successfully!", exact=True)).to_be_visible()

def test_agent_list_view(page: Page, base_url: str):
    """Test that agents are displayed correctly in the list."""
    
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
            },
            {
                "id": "agent-2",
                "name": "Sales Bot",
                "organization_id": "00000000-0000-0000-0000-000000000001",
                "is_active": false,
                "phone_number": "+14155550002",
                "system_prompt": "Prompt 2",
                "created_by": "user-1",
                "created_at": "2026-01-21T00:00:00Z",
                "updated_at": "2026-01-21T00:00:00Z"
            }
        ]'''
    ))

    # Sign in (Mocked)
    page.goto(f"{base_url}/auth/signin")
    page.fill('input#email', "test@gmail.com")
    page.fill('input#password', "Password123!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard")

    # Navigate to Agents
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000) # Small extra wait for hydration
    
    # Verify both agents are visible using explicit locators
    expect(page.get_by_text("Support Bot", exact=True)).to_be_visible(timeout=15000)
    expect(page.get_by_text("Sales Bot", exact=True)).to_be_visible(timeout=15000)
    
    # Verify status indicators (Active/Inactive) using exact match to avoid partial overlaps
    expect(page.get_by_text("Active", exact=True)).to_be_visible()
    expect(page.get_by_text("Inactive", exact=True)).to_be_visible()
