"""Tests for deterministic local worktree seed records."""

from backend.src.worktree_seed import (
    ORG_ADMIN_EMAIL,
    PLATFORM_ADMIN_EMAIL,
    REGULAR_USER_EMAIL,
    WORKTREE_TEST_PASSWORD,
    build_seed_records,
)


def test_seed_records_are_stable_across_worktrees() -> None:
    """Every isolated database receives the same staging-derived fixture."""
    first = build_seed_records("calendar-contract")
    second = build_seed_records("prompt-contract")

    assert first == second
    assert first["agent"]["organization_id"] == first["organization"]["id"]
    assert first["organization"]["name"] == "Pleasant Pediatric"
    assert first["organization"]["slug"] == "pleasant-pediatric"
    assert first["agent"]["id"] == "59252f36-255e-4e71-9250-c4ce3ac27eaa"


def test_seed_records_include_business_context_for_manual_calls() -> None:
    """The generated agent mirrors the current staging appointment receptionist."""
    records = build_seed_records("calendar-contract")

    organization = records["organization"]
    agent = records["agent"]

    assert organization["timezone"] == "America/Phoenix"
    assert organization["industry"] == "dental"
    assert organization["location"] == "Peoria, AZ"
    assert organization["business_details"] is None
    assert agent["name"] == "Alex"
    assert "schedule dental appointments" in agent["mission"]
    assert "Always confirm appointment details" in agent["custom_instructions"]
    assert "Pleasant Pediatric" in agent["instructions_markdown"]
    assert agent["is_active"] is True
    assert agent["call_recording_enabled"] is True


def test_seed_accounts_use_shared_manual_login_credentials() -> None:
    """All worktrees expose the same three intentionally local test accounts."""
    accounts = build_seed_records("calendar-contract")["accounts"]

    assert WORKTREE_TEST_PASSWORD == "Password123!"
    assert {account["email"] for account in accounts} == {
        REGULAR_USER_EMAIL,
        ORG_ADMIN_EMAIL,
        PLATFORM_ADMIN_EMAIL,
    }
    assert {account["role"] for account in accounts} == {
        "regular_user",
        "org_admin",
        "platform_admin",
    }
    assert (
        next(account for account in accounts if account["role"] == "platform_admin")[
            "organization_id"
        ]
        is None
    )


def test_seed_attaches_native_calendar_appointment_tool_without_auth_state() -> None:
    """The staging-derived agent starts with a local OAuth-ready calendar link."""
    records = build_seed_records("calendar-contract")

    assert records["agent_tools"] == ["Google_calendar_appointment"]
