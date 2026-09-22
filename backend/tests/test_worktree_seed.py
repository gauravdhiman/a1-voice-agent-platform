"""Tests for deterministic local and release demo fixture records."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.src.worktree_seed import (
    CALENDAR_DEMO_DISABLED_FUNCTIONS,
    DEMO_ORGANIZATION_ID,
    GOOGLE_SHEETS_TOOL_NAME,
    HVAC_AGENT_ID,
    LEGACY_HVAC_ORGANIZATION_ID,
    LEGACY_SHEETS_TOOL_NAME,
    ORG_ADMIN_EMAIL,
    PLATFORM_ADMIN_EMAIL,
    REGULAR_USER_EMAIL,
    RESTAURANT_AGENT_ID,
    STAGING_AGENT_ID,
    WORKTREE_TEST_PASSWORD,
    build_public_demo_records,
    build_seed_records,
    sync_public_demo_fixtures,
)


def test_seed_records_are_stable_across_worktrees() -> None:
    """Every isolated database receives the same local demo fixture."""
    first = build_seed_records("calendar-contract")
    second = build_seed_records("prompt-contract")

    assert first == second
    assert first["agent"]["organization_id"] == first["organization"]["id"]
    assert {agent["organization_id"] for agent in first["agents"]} == {
        DEMO_ORGANIZATION_ID
    }
    assert first["organization"]["name"] == "24x7 AI Demo Studio"
    assert first["organization"]["slug"] == "247ai-demo-studio"
    assert first["agent"]["id"] == "59252f36-255e-4e71-9250-c4ce3ac27eaa"


def test_seed_records_keep_business_context_on_each_demo_agent() -> None:
    """The shared demo tenant is neutral while prompts contain business context."""
    records = build_seed_records("calendar-contract")

    organization = records["organization"]
    agent = records["agent"]

    assert organization["timezone"] == "America/Phoenix"
    assert organization["industry"] is None
    assert organization["location"] is None
    assert organization["business_details"] is None
    assert agent["name"] == "Alex"
    assert "schedule dental appointments" in agent["mission"]
    assert (
        "Read the date, time, service type, name, and email back"
        in agent["custom_instructions"]
    )
    assert "Pleasant Pediatric" in agent["instructions_markdown"]
    assert "helpful AI assistant" in agent["instructions_markdown"]
    assert "I'm Alex, a helpful AI assistant" in agent["custom_instructions"]
    assert "helpful AI assistant" in agent["persona"]
    assert "1234 Sunbeam Way" in agent["instructions_markdown"]
    assert (
        "Office hours: Monday-Friday, 8:00 AM-5:00 PM" in agent["instructions_markdown"]
    )
    assert "$95" in agent["instructions_markdown"]
    assert "$85" in agent["instructions_markdown"]
    assert "# Public-demo disclosure" in agent["custom_instructions"]
    assert "# Business context" in agent["custom_instructions"]
    assert "# Services and illustrative demo pricing" in agent["custom_instructions"]
    assert "# Appointment workflow" in agent["custom_instructions"]
    assert "# Email follow-up" in agent["custom_instructions"]
    alex_instructions = " ".join(agent["custom_instructions"].split())
    assert "spell the patient or guardian name one letter at a time" in (
        alex_instructions.lower()
    )
    assert "spell the email one character at a time" in alex_instructions.lower()
    assert "invoke that tool automatically" in alex_instructions
    assert "email confirmation was not sent" in alex_instructions
    assert "sent or accepted" in alex_instructions
    assert "do not repeat the notice" in alex_instructions
    assert "AI voice assistant" not in agent["instructions_markdown"]
    assert "{{org.name}}" not in agent["instructions_markdown"]
    assert agent["is_active"] is True
    assert agent["call_recording_enabled"] is True
    assert agent["is_demo"] is True
    assert agent["demo_slug"] == "pleasant-pediatric-appointments"
    assert agent["demo_calls_remaining"] == -1
    assert agent["demo_max_call_duration_seconds"] == 900


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
    """The appointment demo starts with a local OAuth-ready calendar link."""
    records = build_seed_records("calendar-contract")

    assert records["agent_tools"] == ["Google_calendar_appointment"]
    assert records["agent_tools_by_agent"][HVAC_AGENT_ID] == [GOOGLE_SHEETS_TOOL_NAME]
    assert records["agent_tools_by_agent"][RESTAURANT_AGENT_ID] == [
        GOOGLE_SHEETS_TOOL_NAME
    ]
    assert records["agent_tools_to_disable_by_agent"][HVAC_AGENT_ID] == [
        "HubSpot_lead_capture",
        LEGACY_SHEETS_TOOL_NAME,
    ]
    assert records["agent_tools_to_disable_by_agent"][STAGING_AGENT_ID] == [
        "HubSpot_lead_capture",
    ]
    assert (
        records["agent_tool_configs"][records["agent"]["id"]][
            "Google_calendar_appointment"
        ]["require_email"]
        is True
    )
    assert (
        "send_confirmation_email"
        not in records["agent_tool_configs"][records["agent"]["id"]][
            "Google_calendar_appointment"
        ]
    )
    assert (
        "send_confirmation_email"
        not in records["agent_tool_configs"][HVAC_AGENT_ID][GOOGLE_SHEETS_TOOL_NAME]
    )
    assert records["agent_tool_configs"][RESTAURANT_AGENT_ID][
        GOOGLE_SHEETS_TOOL_NAME
    ] == {
        "spreadsheet_id": "",
        "default_range": "Orders!A1:L1000",
        "header_range": "Orders!A1:L1",
        "agent_columns": "Customer Name, Phone, Items",
        "idempotency_column": "Submission ID",
        "timestamp_column": "Captured at",
        "source_column": "Lead source",
        "source_value": "24x7 AI Demo Call",
        "status_column": "",
        "status_value": "",
        "required_columns": "Customer Name, Phone, Items",
        "record_label": "order request",
    }


def test_seed_contains_three_public_demo_workflows() -> None:
    """The isolated fixture exposes appointment, service, and order demos."""
    records = build_seed_records("calendar-contract")

    assert len(records["agents"]) == 3
    assert len(records["organizations"]) == 1
    assert {agent["organization_id"] for agent in records["agents"]} == {
        records["organization"]["id"]
    }
    assert {agent["demo_slug"] for agent in records["agents"]} == {
        "pleasant-pediatric-appointments",
        "copper-ridge-service-request",
        "verdi-table-restaurant",
    }
    assert all(agent["demo_calls_remaining"] == -1 for agent in records["agents"])
    assert all(
        agent["demo_max_call_duration_seconds"] == 900 for agent in records["agents"]
    )
    alex = next(agent for agent in records["agents"] if agent["name"] == "Alex")
    jordan = next(agent for agent in records["agents"] if agent["name"] == "Jordan")
    sofia = next(agent for agent in records["agents"] if agent["name"] == "Sofia")
    assert (
        alex["organization_id"]
        == jordan["organization_id"]
        == sofia["organization_id"]
        == DEMO_ORGANIZATION_ID
    )
    assert (
        "never disclose, search for, reschedule, cancel, or modify"
        in alex["custom_instructions"].lower()
    )
    assert "4550 N Copper Ridge Way" in jordan["instructions_markdown"]
    assert "out-of-hours callback" in jordan["instructions_markdown"]
    assert "helpful AI assistant" in jordan["instructions_markdown"]
    jordan_instructions = " ".join(jordan["custom_instructions"].split())
    assert "I'm Jordan, a helpful AI assistant" in jordan_instructions
    assert "helpful AI assistant" in jordan["persona"]
    assert "$89" in jordan["instructions_markdown"]
    assert "$129" in jordan["instructions_markdown"]
    assert "# Public-demo disclosure" in jordan["custom_instructions"]
    assert "# Business context" in jordan["custom_instructions"]
    assert "# Services and illustrative demo pricing" in jordan["custom_instructions"]
    assert "# Service-inquiry workflow" in jordan["custom_instructions"]
    assert "# Email follow-up" in jordan["custom_instructions"]
    assert "spell the caller's name one letter at a time" in jordan_instructions.lower()
    assert "spell the email one character at a time" in jordan_instructions.lower()
    assert "do not rename them, convert them to snake_case, or invent aliases" in (
        jordan_instructions.lower()
    )
    assert "invoke that tool automatically" in jordan_instructions
    assert "email confirmation was not sent" in jordan_instructions
    assert "do not repeat the notice" in jordan_instructions
    assert "capture_lead" not in jordan_instructions
    assert "create_row" in jordan_instructions
    assert "AI voice assistant" not in jordan["instructions_markdown"]
    sofia_instructions = " ".join(sofia["custom_instructions"].split())
    assert "Verdi Table" in sofia["instructions_markdown"]
    assert "2201 E Juniper Lane" in sofia["instructions_markdown"]
    assert "$16" in sofia["instructions_markdown"]
    assert (
        "Do not call `create_row` for a menu or hours question"
        in sofia["custom_instructions"]
    )
    assert "create_row" in sofia_instructions
    assert "do not rename them, convert them to snake_case, or invent aliases" in (
        sofia_instructions.lower()
    )
    assert "spell the caller's name one letter at a time" in sofia_instructions
    assert "email confirmation was not sent" in sofia_instructions
    assert "quick 1-to-5 rating" in sofia_instructions
    assert records["retired_organization_ids"] == [LEGACY_HVAC_ORGANIZATION_ID]


def test_release_demo_records_exclude_local_and_operator_state() -> None:
    """Deployment sync cannot grant credits or overwrite runtime assignments."""
    records = build_public_demo_records()

    assert "accounts" not in records
    assert (
        not {
            "credit_balance",
            "admin_credit_balance",
            "purchased_credit_balance",
        }
        & records["organization"].keys()
    )
    for agent in records["agents"]:
        assert not {"phone_number", "preset_id", "is_published_on_public_page"} & (
            agent.keys()
        )
    assert {agent["demo_slug"] for agent in records["agents"]} == {
        "pleasant-pediatric-appointments",
        "copper-ridge-service-request",
        "verdi-table-restaurant",
    }


def test_public_demo_sync_only_writes_code_owned_fixture_records() -> None:
    """Release synchronization does not invoke local Auth-account setup."""
    client = MagicMock()
    supabase_module = SimpleNamespace(create_client=MagicMock(return_value=client))

    with (
        patch.dict(sys.modules, {"supabase": supabase_module}),
        patch("backend.src.worktree_seed._upsert_organization") as upsert_org,
        patch("backend.src.worktree_seed._retire_organizations") as retire_orgs,
        patch("backend.src.worktree_seed._upsert_agent") as upsert_agent,
        patch("backend.src.worktree_seed._ensure_agent_tools", return_value=[]),
        patch("backend.src.worktree_seed._disable_agent_tools"),
    ):
        result = sync_public_demo_fixtures("https://demo.supabase.co", "service-key")

    records = build_public_demo_records()
    upsert_org.assert_called_once_with(client, records["organization"])
    retire_orgs.assert_called_once_with(client, [LEGACY_HVAC_ORGANIZATION_ID])
    assert upsert_agent.call_count == 3
    assert result["demo_slugs"] == [
        "pleasant-pediatric-appointments",
        "copper-ridge-service-request",
        "verdi-table-restaurant",
    ]
    assert result["organization_id"] == DEMO_ORGANIZATION_ID


def test_seed_limits_public_calendar_demo_to_new_booking_functions() -> None:
    """An unauthenticated demo cannot inspect or mutate existing events."""
    records = build_seed_records("calendar-contract")

    assert (
        records["agent_tool_function_exclusions"][STAGING_AGENT_ID][
            "Google_calendar_appointment"
        ]
        == CALENDAR_DEMO_DISABLED_FUNCTIONS
    )


def test_seed_syncs_function_exclusions_for_an_existing_tool_link() -> None:
    """Reseeding restores the safe public function boundary after a restart."""
    platform_tools = MagicMock()
    platform_tools.select.return_value = platform_tools
    platform_tools.eq.return_value = platform_tools
    platform_tools.limit.return_value = platform_tools
    platform_tools.execute.return_value = SimpleNamespace(data=[{"id": "tool-1"}])

    agent_tools = MagicMock()
    agent_tools.select.return_value = agent_tools
    agent_tools.eq.return_value = agent_tools
    agent_tools.limit.return_value = agent_tools
    agent_tools.execute.return_value = SimpleNamespace(
        data=[{"id": "agent-tool-1", "config": {"timezone": "America/Phoenix"}}]
    )
    agent_tools.update.return_value = agent_tools

    client = MagicMock()
    client.table.side_effect = [platform_tools, agent_tools, agent_tools]

    from backend.src.worktree_seed import _ensure_agent_tools

    _ensure_agent_tools(
        client,
        STAGING_AGENT_ID,
        ["Google_calendar_appointment"],
        {"Google_calendar_appointment": {"timezone": "America/Phoenix"}},
        {"Google_calendar_appointment": CALENDAR_DEMO_DISABLED_FUNCTIONS},
    )

    agent_tools.update.assert_called_once_with(
        {
            "is_enabled": True,
            "unselected_functions": CALENDAR_DEMO_DISABLED_FUNCTIONS,
        }
    )
