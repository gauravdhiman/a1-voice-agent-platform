"""Contract tests for the focused Google Sheets lead-capture integration."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from shared.voice_agents.tools.base.platform_tool_registry import PlatformToolRegistry
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.google_sheets_lead_service import GoogleSheetsLeadService
from shared.voice_agents.tools.implementations.google_sheets_lead_capture import (
    GoogleSheetsLeadCaptureTool,
)


def _client_factory(handler):
    """Build a fresh async client over one deterministic transport."""
    transport = httpx.MockTransport(handler)

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    return factory


def _capture_arguments() -> dict[str, str]:
    """Return a complete representative service inquiry."""
    return {
        "caller_name": "Maria Garcia",
        "caller_email": "Maria@example.com",
        "caller_phone": "602-555-0101",
        "service_needed": "AC repair",
        "issue_summary": "The upstairs unit is blowing warm air.",
        "property_address": "123 Main Street, Phoenix, AZ",
        "urgency": "This week",
        "preferred_callback_window": "Weekday afternoons",
    }


@pytest.mark.asyncio
async def test_capture_lead_appends_complete_row_after_dedupe_check() -> None:
    """A confirmed inquiry is written once with a stable, complete column order."""
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"values": [["Submission ID"], ["other"]]})
        return httpx.Response(
            200,
            json={"updates": {"updatedRange": "Lead submissions!A3:L3"}},
        )

    service = GoogleSheetsLeadService(
        access_token="google-access-token",
        spreadsheet_id="https://docs.google.com/spreadsheets/d/sheet-id-123456/edit",
        lead_source="24x7 AI public demo",
        client_factory=_client_factory(handler),
    )

    result = await service.capture_lead(
        **_capture_arguments(),
        submission_id="session-1",
        captured_at=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "created"
    assert result["provider"] == "google_sheets"
    assert result["sheet"]["record_type"] == "lead_row"
    assert result["sheet"]["record_id"] == "session-1"
    assert result["sheet"]["updated_range"] == "Lead submissions!A3:L3"
    assert result["deduplicated"] is False
    assert len(requests) == 2
    body = json.loads(requests[1].content)
    assert body["values"][0][0] == "session-1"
    assert body["values"][0][2] == "24x7 AI public demo"
    assert body["values"][0][3:] == [
        "Maria Garcia",
        "maria@example.com",
        "602-555-0101",
        "AC repair",
        "The upstairs unit is blowing warm air.",
        "123 Main Street, Phoenix, AZ",
        "This week",
        "Weekday afternoons",
        "New",
    ]
    assert all("google-access-token" not in str(request) for request in requests)


@pytest.mark.asyncio
async def test_capture_lead_recovers_same_session_without_duplicate_append() -> None:
    """A retry finds the session id and does not append another row."""
    methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(
                200, json={"values": [["Submission ID"], ["session-1"]]}
            )
        return httpx.Response(500, json={"message": "should not append"})

    service = GoogleSheetsLeadService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        client_factory=_client_factory(handler),
    )

    result = await service.capture_lead(
        **_capture_arguments(), submission_id="session-1"
    )

    assert result["status"] == "created"
    assert result["deduplicated"] is True
    assert result["sheet"]["updated_range"] == "Lead submissions!A2"
    assert methods == ["GET"]


@pytest.mark.asyncio
async def test_capture_lead_returns_safe_provider_failure() -> None:
    """Provider outages never become a false success or echo response data."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "secret provider diagnostic"})

    service = GoogleSheetsLeadService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        client_factory=_client_factory(handler),
    )

    result = await service.capture_lead(
        **_capture_arguments(), submission_id="session-1"
    )

    assert result["status"] == "error"
    assert result["provider"] == "google_sheets"
    assert result["error"]["code"] == "temporary_failure"
    assert result["error"]["retryable"] is True
    assert "secret provider diagnostic" not in str(result)


@pytest.mark.asyncio
async def test_capture_lead_validates_before_provider_io() -> None:
    """Missing follow-up details are returned without touching the sheet."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    service = GoogleSheetsLeadService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        client_factory=_client_factory(handler),
    )

    result = await service.capture_lead(
        caller_name="Taylor Smith",
        caller_email="",
        caller_phone="",
        service_needed="Duct cleaning",
        issue_summary="I would like an estimate.",
        submission_id="session-1",
    )

    assert result["status"] == "needs_details"
    assert result["error"]["code"] == "missing_or_invalid_detail"
    assert calls == 0


def test_registry_does_not_publish_the_retired_lead_only_adapter() -> None:
    """The retired adapter remains runtime-compatible but is not cataloged."""
    registry = PlatformToolRegistry()
    registry.register_tools_from_package("shared.voice_agents.tools.implementations")

    assert registry.get_tool_class("Google_Sheets_lead_capture") is not None
    assert registry.get_tool_functions("Google_Sheets_lead_capture")
    assert "Google_Sheets" in registry.get_tool_names()
    assert GoogleSheetsLeadCaptureTool.DEPRECATED_TOOL is True


@pytest.mark.asyncio
async def test_registry_does_not_resync_the_retired_lead_only_adapter() -> None:
    """Catalog sync skips the prototype so it stays unavailable for new links."""
    registry = PlatformToolRegistry()
    registry.register_tools_from_package("shared.voice_agents.tools.implementations")
    synced_names: list[str] = []

    class FakeToolService:
        async def upsert_platform_tool(self, tool_data):
            synced_names.append(tool_data.name)
            return None, None

    await registry.sync_with_db(FakeToolService())

    assert "Google_Sheets" in synced_names
    assert "Google_Sheets_lead_capture" not in synced_names


@pytest.mark.asyncio
async def test_tool_requires_confirmation_and_connection() -> None:
    """The adapter protects both caller consent and its provider connection."""
    context = ToolContext(
        organization_id="org-1",
        agent_id="agent-1",
        session_id="session-1",
        is_demo=True,
        demo_slug="copper-ridge-service-request",
    )
    tool = GoogleSheetsLeadCaptureTool()

    confirmation = await tool.capture_lead(
        context=context,
        caller_name="Taylor Smith",
        service_needed="Duct cleaning",
        issue_summary="I would like an estimate.",
        user_confirmed=False,
        caller_email="taylor@example.com",
    )
    assert confirmation["status"] == "confirmation_required"
    assert confirmation["provider"] == "google_sheets"

    not_configured = await tool.capture_lead(
        context=context,
        caller_name="Taylor Smith",
        service_needed="Duct cleaning",
        issue_summary="I would like an estimate.",
        user_confirmed=True,
        caller_email="taylor@example.com",
    )
    assert not_configured["status"] == "error"
    assert not_configured["error"]["code"] == "authentication_required"


@pytest.mark.asyncio
async def test_tool_returns_only_the_sheet_result_after_success(monkeypatch) -> None:
    """The Sheets actor does not invoke or configure an email actor."""
    context = ToolContext(
        organization_id="org-1",
        agent_id="agent-1",
        session_id="session-1",
        is_demo=True,
        demo_slug="copper-ridge-service-request",
    )
    tool = GoogleSheetsLeadCaptureTool(
        config={
            "spreadsheet_id": "sheet-id-123456",
        },
        sensitive_config={"access_token": "google-access-token"},
    )
    service = Mock()
    service.capture_lead = AsyncMock(
        return_value={
            "status": "created",
            "provider": "google_sheets",
            "message": "Service inquiry captured in Google Sheets.",
            "sheet": {"record_id": "session-1"},
        }
    )
    monkeypatch.setattr(tool, "_service", lambda: service)

    result = await tool.capture_lead(
        context=context, **_capture_arguments(), user_confirmed=True
    )

    assert result["status"] == "created"
    assert "confirmation_email" not in result
    service.capture_lead.assert_awaited_once()
