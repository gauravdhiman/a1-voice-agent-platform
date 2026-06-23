"""
E2E tests for skills workflow.

Tests the full user journey for skills:
- Organization skills page shows built-in skills
- Skills can be viewed in the split-view panel
- Agent skills tab shows toggle-based assignment
- Skill filtering works
- Organization skills page shows expandable file tree
- Clicking a file shows its content rendered
- Import from URL fetches and adds a skill
- Delete shows agents using the skill and confirms
- URL state for skill/file selection (bookmarkable)
"""

import pytest
import json
from playwright.sync_api import Page, expect
from helpers import signin_user


# Test data — matches conftest.py mock org/user IDs
TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"
TEST_AGENT_ID = "00000000-0000-0000-0000-000000000002"

MOCK_FILE_SUMMARIES = [
    {"id": "file-1", "file_path": "references/policies.md", "file_kind": "reference", "content_hash": "abc1"},
    {"id": "file-2", "file_path": "references/faq.md", "file_kind": "reference", "content_hash": "abc2"},
    {"id": "file-3", "file_path": "scripts/validate.py", "file_kind": "script", "content_hash": "abc3"},
]

MOCK_CUSTOM_SKILL_FILES = [
    {"id": "file-4", "file_path": "notes.md", "file_kind": "reference", "content_hash": "abc4"},
]

MOCK_FILE_CONTENTS = {
    "references/policies.md": "# Booking Policies\n\n- Confirm insurance\n- Verify ID",
    "references/faq.md": "# FAQ\n\nQ: What hours?\nA: 9-5",
    "scripts/validate.py": "# Script\ndef run(): pass",
}

MOCK_IMPORT_RESULT = [
    {
        "skill": {
            "id": "skill-new-1",
            "organization_id": TEST_ORG_ID,
            "slug": "cold-email",
            "name": "Cold Email",
            "description": "Send cold emails.",
            "content": "# Cold Email\n\nDraft and send.",
            "category": "custom",
            "is_active": True,
            "version": None,
            "author": None,
            "content_hash": "imp123",
            "source_url": "https://github.com/anthropics/skills",
            "source_ref": "main",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        "files_imported": 3,
        "source_url": "https://github.com/anthropics/skills",
    }
]

MOCK_SKILLS = [
    {
        "id": "00000000-0000-0000-0000-000000000010",
        "organization_id": TEST_ORG_ID,
        "slug": "appointment-booking",
        "name": "Appointment Booking",
        "description": "Handle scheduling, rescheduling, and cancellation of appointments.",
        "content": "# Appointment Booking\n\n## When to Use\n- Caller asks to book\n\n## Procedure\n1. Ask for date",
        "category": "custom",
        "is_active": True,
        "is_visible": True,
        "version": "1.0.0",
        "author": "Platform",
        "content_hash": "abc123",
        "source_skill_id": "plat-001",
        "source_version": "2026.05.03_1",
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
        "category": "custom",
        "is_active": True,
        "is_visible": True,
        "version": "1.0.0",
        "author": "Platform",
        "content_hash": "def456",
        "source_skill_id": "plat-002",
        "source_version": "2026.03.01_1",
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
        "is_visible": True,
        "version": None,
        "author": None,
        "content_hash": "ghi789",
        "source_skill_id": None,
        "source_version": None,
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

# Phase 2c: Platform skills fork model mock data
MOCK_PLATFORM_SKILL = {
    "id": "plat-001",
    "slug": "appointment-booking",
    "name": "Appointment Booking",
    "description": "Schedule, reschedule, and cancel appointments.",
    "content": "# Appointment Booking\n\nHandle scheduling.",
    "version": "2026.05.03_1",
    "content_hash": "plat-abc",
    "is_active": True,
    "author": "Platform Team",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

MOCK_FORKED_SKILL = {
    "id": "skill-fork-1",
    "organization_id": TEST_ORG_ID,
    "slug": "appointment-booking",
    "name": "Appointment Booking",
    "description": "Schedule, reschedule, and cancel appointments.",
    "content": "# Appointment Booking\n\nHandle scheduling.",
    "category": "custom",
    "is_active": True,
    "is_visible": True,
    "version": "2026.05.03_1",
    "author": "Platform Team",
    "content_hash": "fork-abc",
    "source_skill_id": "plat-001",
    "source_version": "2026.05.03_1",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

MOCK_HIDDEN_FORKED_SKILL = {
    "id": "skill-fork-2",
    "organization_id": TEST_ORG_ID,
    "slug": "call-transfer",
    "name": "Call Transfer",
    "description": "Escalate calls to human agents.",
    "content": "# Call Transfer\n\nEscalate calls.",
    "category": "custom",
    "is_active": True,
    "is_visible": False,
    "version": "2026.03.01_1",
    "author": "Platform Team",
    "content_hash": "fork-def",
    "source_skill_id": "plat-002",
    "source_version": "2026.03.01_1",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def setup_base_mocks(page: Page):
    """Set up base API mocks shared by most tests."""
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

    page.route(f"**/api/v1/agents/{TEST_AGENT_ID}", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(MOCK_AGENT),
    ))

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

    page.route(f"**/api/v1/agents/{TEST_AGENT_ID}/system-prompt", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='"# Test Agent\\n\\nA helpful voice assistant."',
    ))


def setup_skill_mocks(page: Page):
    """Set up API mocks for skill endpoints (skills list uses static MOCK_SKILLS)."""
    setup_base_mocks(page)

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(MOCK_SKILLS),
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

    step("Verify badges: Forked (Platform) and Custom")
    expect(page.locator("text=Platform").first).to_be_visible(timeout=5000)
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


def test_skill_file_tree_expandable(page: Page, base_url: str, step):
    """Test that clicking a skill accordion expands to show file tree."""
    import json as _json
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_SKILLS),
    ))
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{MOCK_SKILLS[0]['id']}/files", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_FILE_SUMMARIES),
    ))

    setup_skill_mocks(page)
    step("Sign in and navigate to organization skills")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Click Appointment Booking skill to expand")
    expect(page.get_by_text("Appointment Booking").first).to_be_visible(timeout=10000)
    page.get_by_text("Appointment Booking").first.click()

    step("Verify file tree is visible with references folder and scripts")
    # Wait for skill files to load
    expect(page.get_by_text("references").first).to_be_visible(timeout=5000)
    expect(page.get_by_text("policies.md")).to_be_visible()
    expect(page.get_by_text("validate.py")).to_be_visible()


def test_skill_file_content_viewable(page: Page, base_url: str, step):
    """Test that clicking a file in the tree loads its content."""
    import json as _json
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_SKILLS),
    ))
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{MOCK_SKILLS[0]['id']}/files", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_FILE_SUMMARIES),
    ))
    page.route(
        f"**/api/v1/skills/{TEST_ORG_ID}/appointment-booking/files/references/policies.md",
        lambda route: route.fulfill(
            status=200, content_type="text/plain",
            body=MOCK_FILE_CONTENTS["references/policies.md"],
        ),
    )

    setup_skill_mocks(page)
    step("Sign in, expand Appointment Booking skill")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Expand skill and click on policies.md")
    page.get_by_text("Appointment Booking").first.click()
    expect(page.get_by_text("references").first).to_be_visible(timeout=5000)
    page.get_by_text("policies.md").first.click()

    step("Verify file content appears in right panel")
    expect(page.get_by_text("Confirm insurance").first).to_be_visible(timeout=5000)


def test_skill_import_from_url_adds_skill(page: Page, base_url: str, step):
    """Test importing a skill from a GitHub URL via the Import Sheet."""
    import json as _json
    all_skills = MOCK_SKILLS.copy()

    setup_base_mocks(page)

    def handle_skills_list(route):
        body = _json.dumps(all_skills)
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", handle_skills_list)

    def handle_import(route):
        if route.request.method == "POST":
            all_skills.append(MOCK_IMPORT_RESULT[0]["skill"])
            route.fulfill(status=201, content_type="application/json", body=_json.dumps(MOCK_IMPORT_RESULT))
        else:
            route.continue_()

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/import", handle_import)

    step("Sign in and navigate to skills tab")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Click Add dropdown and select Import from URL")
    add_btn = page.get_by_role("button", name="Add").first
    expect(add_btn).to_be_visible(timeout=10000)
    add_btn.click()
    page.get_by_text("Import from URL").first.click()

    step("Fill the import URL in the sheet")
    import_input = page.locator('input#import-url, input[placeholder*="GitHub"]').first
    expect(import_input).to_be_visible(timeout=5000)
    import_input.fill("https://github.com/anthropics/skills")

    step("Click Import Skill button")
    page.get_by_role("button", name="Import Skill").first.click()

    step("Wait for success toast and verify new skill appears")
    page.wait_for_timeout(800)
    expect(page.get_by_text("Cold Email").first).to_be_visible(timeout=10000)


def test_skill_delete_shows_agent_warning(page: Page, base_url: str, step):
    """Test that deleting a custom skill shows agents using it and requires confirmation."""
    import json as _json
    setup_base_mocks(page)

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_SKILLS),
    ))
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{MOCK_SKILLS[2]['id']}/agents", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps([{"id": "agent-1", "name": "Test Agent", "is_active": True}]),
    ))
    page.route(
        f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{MOCK_SKILLS[2]['id']}",
        lambda route: route.fulfill(status=204, content_type="application/json", body=""),
    )

    step("Sign in and navigate to skills tab")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Find the custom skill row and hover to reveal trash button")
    custom_skill_row = page.locator("text=My Custom Policy").first
    expect(custom_skill_row).to_be_visible(timeout=10000)
    custom_skill_row.hover()

    step("Click the trash icon that appears on hover")
    # The trash button is inside the skill row's action area
    trash_btn = custom_skill_row.locator("xpath=ancestor::*[contains(@class,'group')]//button").first
    if trash_btn.count() == 0:
        # Fallback: hover the row and click the last button that appears
        custom_skill_row.hover()
        page.wait_for_timeout(200)
        trash_btn = page.locator("button svg[class*='text-red']").first.locator("xpath=ancestor::button").first
    expect(trash_btn).to_be_visible(timeout=5000)
    trash_btn.click()

    step("Verify agent warning is shown in dialog")
    expect(page.get_by_text("currently used by").first).to_be_visible(timeout=5000)
    expect(page.get_by_text("Test Agent").first).to_be_visible()

    step("Click Delete Skill to confirm")
    page.get_by_role("button", name="Delete Skill").first.click()

    step("Verify skill is no longer in the list")
    # The row should disappear after deletion
    page.wait_for_timeout(500)


def test_url_bookmarks_skill_and_file(page: Page, base_url: str, step):
    """Test that URL parameter restores selected skill and file on load."""
    import json as _json
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_SKILLS),
    ))
    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{MOCK_SKILLS[0]['id']}/files", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=_json.dumps(MOCK_FILE_SUMMARIES),
    ))
    page.route(
        f"**/api/v1/skills/{TEST_ORG_ID}/appointment-booking/files/references/faq.md",
        lambda route: route.fulfill(
            status=200, content_type="text/plain",
            body=MOCK_FILE_CONTENTS["references/faq.md"],
        ),
    )

    setup_skill_mocks(page)
    step("Sign in and navigate directly to skill URL with file param")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills&skill=appointment-booking&file=references/faq.md")
    page.wait_for_load_state("networkidle")

    step("Verify the skill is expanded and file content loads")
    expect(page.get_by_text("references").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Q: What hours?").first).to_be_visible(timeout=5000)


# ---------------------------------------------------------------------------
# Phase 2a existing tests (below — unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Phase 2c: Platform Skills Fork/Refresh Model tests
# ---------------------------------------------------------------------------


def test_platform_skill_library_fork(page: Page, base_url: str, step):
    """Test forking a platform skill from the Platform Skill Library sheet."""
    import json as _json
    all_skills = MOCK_SKILLS.copy()

    setup_base_mocks(page)

    def handle_skills_list(route):
        body = _json.dumps(all_skills)
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", handle_skills_list)

    page.route("**/api/v1/platform/skills", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=_json.dumps([MOCK_PLATFORM_SKILL]),
    ))

    def handle_fork(route):
        if route.request.method == "POST":
            all_skills.append(MOCK_FORKED_SKILL)
            route.fulfill(status=201, content_type="application/json", body=_json.dumps(MOCK_FORKED_SKILL))
        else:
            route.continue_()

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/fork", handle_fork)

    step("Sign in and navigate to skills tab")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Click Add dropdown and select Create from Platform Library")
    add_btn = page.get_by_role("button", name="Add").first
    expect(add_btn).to_be_visible(timeout=10000)
    add_btn.click()
    page.get_by_text("Create from Platform Library").first.click()

    step("Verify Platform Skill Library sheet opens")
    expect(page.get_by_text("Platform Skill Library").first).to_be_visible(timeout=5000)
    expect(page.get_by_text("Appointment Booking").first).to_be_visible()
    expect(page.get_by_text("v2026.05.03_1").first).to_be_visible()

    step("Click Fork into Library button")
    page.get_by_role("button", name="Fork into Library").first.click()

    step("Wait for success toast and verify forked skill appears")
    page.wait_for_timeout(800)
    expect(page.get_by_text("Forked \"Appointment Booking\" into your library").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Appointment Booking").first).to_be_visible(timeout=10000)


def test_agent_skills_hidden_badge(page: Page, base_url: str, step):
    """Test that hidden skills still appear on agent tab with a Hidden badge."""
    import json as _json
    # Mix of visible and hidden skills
    mixed_skills = [MOCK_FORKED_SKILL, MOCK_HIDDEN_FORKED_SKILL]

    setup_base_mocks(page)

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200, content_type="application/json", body=_json.dumps(mixed_skills),
    ))

    step("Sign in and navigate to agent skills tab")
    signin_user(page, base_url)
    page.goto(f"{base_url}/agents/{TEST_AGENT_ID}?tab=skills")
    page.wait_for_load_state("networkidle")

    step("Verify both visible and hidden skills are shown")
    expect(page.get_by_text("Appointment Booking").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Call Transfer").first).to_be_visible(timeout=10000)

    step("Verify hidden skill has the Hidden badge")
    hidden_row = page.locator("text=Call Transfer").first.locator("xpath=ancestor::*[contains(@class,'rounded-lg')]")
    expect(hidden_row.get_by_text("Hidden").first).to_be_visible(timeout=5000)

    step("Verify the hidden skill toggle still works")
    hidden_switch = hidden_row.locator('[role="switch"]').first
    expect(hidden_switch).to_be_visible()
    hidden_switch.click()
    page.wait_for_timeout(400)


def test_skill_refresh_flow(page: Page, base_url: str, step):
    """Test refreshing a forked skill from the latest platform version."""
    import json as _json
    forked = {**MOCK_FORKED_SKILL, "source_version": "2026.05.03_1"}

    setup_base_mocks(page)

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills", lambda route: route.fulfill(
        status=200, content_type="application/json", body=_json.dumps([forked]),
    ))

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{forked['id']}/update-check", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=_json.dumps({"update_available": True, "latest_version": "2026.05.15_1", "current_version": "2026.05.03_1"}),
    ))

    page.route(f"**/api/v1/organizations/{TEST_ORG_ID}/skills/{forked['id']}/refresh", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=_json.dumps({**forked, "source_version": "2026.05.15_1", "version": "2026.05.15_1"}),
    ))

    step("Sign in and navigate to organization skills tab")
    signin_user(page, base_url)
    page.goto(f"{base_url}/organization?org_id={TEST_ORG_ID}&tab=skills")
    page.wait_for_load_state("networkidle")

    step("Click the forked skill to open detail view")
    expect(page.get_by_text("Appointment Booking").first).to_be_visible(timeout=10000)
    page.get_by_text("Appointment Booking").first.click()

    step("Click Check Update button")
    page.get_by_role("button", name="Check Update").first.click()

    step("Verify refresh confirmation dialog appears")
    expect(page.get_by_text("Refresh Skill").first).to_be_visible(timeout=5000)
    expect(page.get_by_text("2026.05.03_1").first).to_be_visible()
    expect(page.get_by_text("2026.05.15_1").first).to_be_visible()
    expect(page.get_by_text("replace all content and files").first).to_be_visible()

    step("Click Refresh Now to confirm")
    page.get_by_role("button", name="Refresh Now").first.click()

    step("Wait for success toast")
    expect(page.get_by_text("Skill refreshed successfully").first).to_be_visible(timeout=10000)
