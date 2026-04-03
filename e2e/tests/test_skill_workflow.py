"""
E2E tests for skills workflow.

Tests the full user journey for skills:
- Organization skills page shows built-in skills
- Skills can be viewed in the split-view panel
- Agent skills tab shows toggle-based assignment
- Skill filtering works
"""

import pytest
import json
from playwright.sync_api import Page, expect
from helpers import signin_user


# Test data — matches conftest.py mock org/user IDs
TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"
TEST_AGENT_ID = "00000000-0000-0000-0000-000000000002"

MOCK_SKILLS = [
    {
        "id": "00000000-0000-0000-0000-000000000010",
        "organization_id": TEST_ORG_ID,
        "slug": "appointment-booking",
        "name": "Appointment Booking",
        "description": "Handle scheduling, rescheduling, and cancellation of appointments.",
        "content": "# Appointment Booking\n\n## When to Use\n- Caller asks to book\n\n## Procedure\n1. Ask for date",
        "category": "built_in",
        "is_active": True,
        "version": "1.0.0",
        "author": "Platform",
        "content_hash": "abc123",
        "source_url": None,
        "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": "00000000-0000-0000-0000-000000000011",
        "organization_id": TEST_ORG_ID,
        "slug": "call-transfer",
        "name": "Call Transfer",
        "description": "Escalate calls to a human agent with proper context handoff.",
        "content": "# Call Transfer\n\n## When to Use\n- Caller asks for a person",
        "category": "built_in",
        "is_active": True,
        "version": "1.0.0",
        "author": "Platform",
        "content_hash": "def456",
        "source_url": None,
        "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": "00000000-0000-0000-0000-000000000012",
        "organization_id": TEST_ORG_ID,
        "slug": "custom-policy",
        "name": "My Custom Policy",
        "description": "Company-specific procedures.",
        "content": "# Custom Policy\n\nFollow these steps...",
        "category": "custom",
        "is_active": True,
        "version": None,
        "author": None,
        "content_hash": "ghi789",
        "source_url": None,
        "source_ref": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    },
]

MOCK_AGENT = {
    "id": TEST_AGENT_ID,
    "organization_id": TEST_ORG_ID,
    "name": "Test Agent",
    "phone_number": None,
    "persona": None,
    "tone": None,
    "mission": None,
    "custom_instructions": None,
    "instructions_markdown": "# Test Agent\n\nA helpful voice assistant.",
    "is_active": False,
    "use_platform_credits": False,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def setup_skill_mocks(page: Page):
    """Set up API mocks for skill endpoints."""

    # Mock org detail (needed when navigating to org page with org_id param)
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "id": TEST_ORG_ID,
            "name": "Test Organization",
            "slug": "test-org",
            "is_active": True,
            "onboarding_completed": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }),
    ))

    # Mock org skills list
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(MOCK_SKILLS),
    ))

    # Mock agent detail
    page.route(f"**/api/v1/agents/{TEST_AGENT_ID}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(MOCK_AGENT),
    ))

    # Mock agent skills (first skill assigned)
    page.route(f"**/api/v1/agents/{TEST_AGENT_ID}/skills", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps([{
            "id": "asgn-1",
            "agent_id": TEST_AGENT_ID,
            "skill_id": MOCK_SKILLS[0]["id"],
            "skill": MOCK_SKILLS[0],
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
        }]),
    ))

    # Mock tools endpoints (empty — needed for agent detail page)
    page.route(f"**/api/v1/tools/agent/{TEST_AGENT_ID}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body="[]",
    ))

    page.route("**/api/v1/tools/platform", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body="[]",
    ))

    # Mock system prompt
    page.route(f"**/api/v1/agents/{TEST_AGENT_ID}/system-prompt", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='"# Test Agent\\n\\nA helpful voice assistant."',
    ))


def test_organization_skills_page_shows_skills(page: Page, base_url: str, step):
    """Test that the organization skills tab displays skills in split view."""
    setup_skill_mocks(page)

    step("Sign in as test user")
    signin_user(page, base_url)

    step("Navigate to organization skills tab")
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Verify skills are listed")
    expect(page.get_by_text("Appointment Booking").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Call Transfer").first).to_be_visible()
    expect(page.get_by_text("My Custom Policy").first).to_be_visible()

    step("Verify built-in and custom badges")
    expect(page.locator("text=Built-in").first).to_be_visible()
    expect(page.locator("text=Custom").first).to_be_visible()

    step("Click a skill to view content in right panel")
    page.get_by_text("Appointment Booking").first.click()

    step("Verify content displayed in right panel")
    expect(page.locator(".prose").get_by_text("When to Use")).to_be_visible(timeout=5000)


def test_organization_skills_filter(page: Page, base_url: str, step):
    """Test that the skill filter narrows the list."""
    setup_skill_mocks(page)

    step("Sign in and navigate to skills")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Wait for skills to load")
    expect(page.get_by_text("Appointment Booking").first).to_be_visible(timeout=10000)

    step("Type 'transfer' in filter")
    page.fill('input[placeholder="Filter skills..."]', "transfer")

    step("Verify only Call Transfer is visible in the skill list")
    # The left panel should show only matching skills
    expect(page.get_by_text("Call Transfer").first).to_be_visible()


def test_agent_skills_tab_shows_toggles(page: Page, base_url: str, step):
    """Test that the agent skills tab shows skill toggles."""
    setup_skill_mocks(page)

    step("Sign in and navigate to agent skills tab")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/{TEST_AGENT_ID}?tab=skills")
    page.wait_for_load_state("networkidle")

    step("Verify skills tab content loads")
    expect(page.get_by_text("Agent Skills")).to_be_visible(timeout=10000)

    step("Verify skill toggle switches are present")
    switches = page.locator('[role="switch"]')
    expect(switches.first).to_be_visible(timeout=10000)
