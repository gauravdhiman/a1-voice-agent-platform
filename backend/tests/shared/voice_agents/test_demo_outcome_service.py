"""Tests for signed and allowlisted public demo receipts."""

from datetime import timedelta
from unittest.mock import Mock

import pytest

from shared.voice_agents.demo_outcome_service import (
    DemoOutcomeService,
    build_demo_outcome_payload,
    create_demo_outcome_token,
    verify_demo_outcome_token,
)
from shared.voice_agents.tools.base.tool_context import ToolContext


def test_outcome_payload_allowlists_lead_fields_and_provider_summary() -> None:
    """Secrets and arbitrary tool arguments never enter a visitor receipt."""
    payload = build_demo_outcome_payload(
        function_name="capture_lead",
        arguments={
            "caller_name": "Maria Garcia",
            "caller_email": "maria@example.com",
            "service_needed": "AC repair",
            "issue_summary": "Warm air upstairs",
            "password": "must-not-be-recorded",
        },
        result={
            "status": "created",
            "message": "Service inquiry captured in HubSpot.",
            "crm": {"record_id": "contact-123"},
            "secret_response_body": "must-not-be-recorded",
        },
    )

    assert payload is not None
    assert payload["status"] == "succeeded"
    assert payload["captured_fields"]["caller_name"] == "Maria Garcia"
    assert "password" not in payload["captured_fields"]
    assert "secret_response_body" not in payload["provider_result"]
    assert payload["provider_result"]["record_id"] == "contact-123"


def test_outcome_payload_supports_google_sheets_lead_rows() -> None:
    """The visitor receipt names the actual lead provider and row resource."""
    payload = build_demo_outcome_payload(
        function_name="capture_lead",
        arguments={
            "caller_name": "Maria Garcia",
            "caller_email": "maria@example.com",
            "service_needed": "AC repair",
            "issue_summary": "Warm air upstairs",
        },
        result={
            "status": "created",
            "provider": "google_sheets",
            "message": "Service inquiry captured in Google Sheets.",
            "sheet": {
                "record_type": "lead_row",
                "record_id": "session-123",
                "updated_range": "Lead submissions!A2:L2",
            },
            "deduplicated": False,
        },
    )

    assert payload is not None
    assert payload["provider"] == "google_sheets"
    assert payload["provider_result"] == {
        "record_type": "lead_row",
        "record_id": "session-123",
        "record_status": "created",
        "note_id": None,
        "updated_range": "Lead submissions!A2:L2",
        "deduplicated": False,
        "message": "Service inquiry captured in Google Sheets.",
    }


def test_outcome_payload_supports_generic_google_sheets_rows() -> None:
    """Generic row creation gets a truthful, bounded visitor receipt."""
    payload = build_demo_outcome_payload(
        function_name="create_row",
        arguments={
            "values": {
                "Caller name": "Maria Garcia",
                "Service needed": "Two Sonoran grain bowls",
                "Submission ID": "session-1",
                "Secret note": "must-not-be-recorded",
            }
        },
        result={
            "status": "created",
            "provider": "google_sheets",
            "message": "Order request saved in Google Sheets.",
            "sheet": {
                "record_type": "row",
                "record_label": "order request",
                "record_id": "session-1",
                "updated_range": "Orders!A2:L2",
            },
            "deduplicated": False,
        },
    )

    assert payload == {
        "action_type": "sheet_row_created",
        "provider": "google_sheets",
        "status": "succeeded",
        "error_code": None,
        "captured_fields": {
            "Caller name": "Maria Garcia",
            "Service needed": "Two Sonoran grain bowls",
        },
        "provider_result": {
            "record_type": "row",
            "record_label": "order request",
            "record_id": "session-1",
            "record_status": "created",
            "updated_range": "Orders!A2:L2",
            "deduplicated": False,
            "message": "Order request saved in Google Sheets.",
        },
    }


def test_outcome_payload_records_gmail_as_a_separate_pii_free_action() -> None:
    """An attached Gmail tool is shown independently without exposing its message."""
    payload = build_demo_outcome_payload(
        function_name="send_email",
        arguments={
            "to": "maria@example.com",
            "subject": "Your service request",
            "body": "A private message that must not enter the receipt.",
        },
        result={"id": "gmail-message-123", "threadId": "gmail-thread-123"},
    )

    assert payload == {
        "action_type": "email_delivery",
        "provider": "gmail",
        "status": "succeeded",
        "error_code": None,
        "captured_fields": {},
        "provider_result": {
            "record_type": "email",
            "record_id": "gmail-message-123",
            "record_status": None,
            "message": "Gmail confirmed the email was sent.",
        },
    }
    assert "maria@example.com" not in str(payload)
    assert "private message" not in str(payload)


def test_outcome_payload_records_resend_acceptance_separately() -> None:
    """Resend acceptance is independently represented without coupling tools."""
    payload = build_demo_outcome_payload(
        function_name="send_resend_email",
        arguments={
            "route_id": "customer-support",
            "subject": "New inquiry",
            "body": "Internal lead details",
        },
        result={
            "status": "accepted",
            "provider_message_ids": ["resend-message-123"],
        },
    )

    assert payload is not None
    assert payload["action_type"] == "email_delivery"
    assert payload["provider"] == "resend"
    assert payload["status"] == "succeeded"
    assert payload["provider_result"]["record_id"] == "resend-message-123"
    assert payload["provider_result"]["message"] == (
        "Resend accepted the email for the configured route."
    )


def test_outcome_payload_does_not_claim_partial_email_delivery_as_success() -> None:
    """A provider partial result remains visible as an incomplete action."""
    payload = build_demo_outcome_payload(
        function_name="send_resend_email",
        arguments={},
        result={
            "status": "partial",
            "code": "partial_delivery",
            "provider_message_ids": ["resend-message-123"],
        },
    )

    assert payload is not None
    assert payload["status"] == "failed"
    assert payload["error_code"] == "partial_delivery"


def test_outcome_payload_exposes_only_safe_google_calendar_record_links() -> None:
    """A provider-generated Calendar event link can be opened from the receipt."""
    payload = build_demo_outcome_payload(
        function_name="create_appointment",
        arguments={
            "caller_name": "Maria Garcia",
            "caller_email": "maria@example.com",
            "purpose": "Cleaning",
            "start_time": "2026-09-01T14:00:00-07:00",
            "duration_minutes": 30,
        },
        result={
            "status": "created",
            "message": "Appointment booked.",
            "appointment": {
                "id": "event-1",
                "record_url": "https://calendar.google.com/calendar/event?eid=event-1",
            },
        },
    )

    assert payload is not None
    assert payload["provider_result"]["record_url"].startswith(
        "https://calendar.google.com/calendar/"
    )

    unsafe = build_demo_outcome_payload(
        function_name="create_appointment",
        arguments={"caller_name": "Maria Garcia", "purpose": "Cleaning"},
        result={
            "status": "created",
            "appointment": {
                "id": "event-2",
                "record_url": "https://evil.example.test/calendar/event?eid=event-2",
            },
        },
    )
    assert unsafe is not None
    assert "record_url" not in unsafe["provider_result"]


def test_demo_outcome_token_is_bound_to_slug_and_session() -> None:
    """A receipt token cannot be replayed for another demo slug."""
    token = create_demo_outcome_token(
        session_id="session-1",
        agent_id="agent-1",
        demo_slug="demo-one",
        secret="test-secret",
        expires_in=timedelta(minutes=5),
    )

    claims = verify_demo_outcome_token(token, secret="test-secret")
    assert claims is not None
    assert claims.session_id == "session-1"
    assert claims.demo_slug == "demo-one"
    assert verify_demo_outcome_token(token, secret="wrong-secret") is None


@pytest.mark.asyncio
async def test_record_uses_demo_context_and_service_role_client() -> None:
    """Only demo sessions may create a receipt row."""
    table = Mock()
    table.insert.return_value = table
    table.execute.return_value = Mock(data=[{"id": "receipt-1"}])
    client = Mock()
    client.table.return_value = table
    service = DemoOutcomeService(client=client)
    context = ToolContext(
        organization_id="org-1",
        agent_id="agent-1",
        session_id="session-1",
        is_demo=True,
        demo_slug="demo-one",
    )
    payload = build_demo_outcome_payload(
        function_name="create_appointment",
        arguments={
            "caller_name": "Maria Garcia",
            "purpose": "Cleaning",
            "start_time": "2026-09-01T14:00:00-07:00",
            "duration_minutes": 30,
        },
        result={
            "status": "created",
            "message": "Appointment booked.",
            "appointment": {"id": "event-1"},
        },
    )
    assert payload is not None

    assert await service.record(context=context, payload=payload) is True
    row = table.insert.call_args.args[0]
    assert row["session_id"] == "session-1"
    assert row["action_type"] == "appointment_booking"
    assert row["captured_fields"]["caller_name"] == "Maria Garcia"

    non_demo = ToolContext(session_id="session-2")
    assert await service.record(context=non_demo, payload=payload) is False
    assert table.insert.call_count == 1
