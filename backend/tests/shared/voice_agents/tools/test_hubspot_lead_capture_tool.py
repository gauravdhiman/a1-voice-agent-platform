"""Contract tests for the HubSpot service-inquiry integration."""

import json

import httpx
import pytest

from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.hubspot_lead_service import HubSpotLeadService
from shared.voice_agents.tools.implementations.hubspot_lead_capture import (
    HubspotLeadCaptureTool,
)


def _client_factory(handler):
    """Build a fresh async client over one deterministic transport."""
    transport = httpx.MockTransport(handler)

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    return factory


@pytest.mark.asyncio
async def test_capture_lead_creates_contact_and_associated_note() -> None:
    """A new inquiry writes a standard contact and preserves full context in a note."""
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/contacts/search"):
            return httpx.Response(200, json={"results": []})
        if request.url.path.endswith("/contacts"):
            return httpx.Response(201, json={"id": "contact-123"})
        if request.url.path.endswith("/notes"):
            return httpx.Response(201, json={"id": "note-456"})
        return httpx.Response(404)

    service = HubSpotLeadService(
        access_token="private-app-token",
        lead_source="24x7 AI public demo",
        client_factory=_client_factory(handler),
    )

    result = await service.capture_lead(
        caller_name="Maria Garcia",
        caller_email="Maria@example.com",
        caller_phone="602-555-0101",
        service_needed="AC repair",
        issue_summary="The upstairs unit is blowing warm air.",
        property_address="123 Main Street, Phoenix, AZ",
        urgency="This week",
        preferred_callback_window="Weekday afternoons",
    )

    assert result["status"] == "created"
    assert result["crm"]["record_id"] == "contact-123"
    assert result["note"] == {"status": "created", "id": "note-456"}
    contact_request = next(
        request for request in requests if request.url.path.endswith("/contacts")
    )
    assert contact_request.method == "POST"
    assert contact_request.read().decode()
    contact_body = json.loads(contact_request.content)
    assert contact_body["properties"]["email"] == "maria@example.com"
    assert contact_body["properties"]["lifecyclestage"] == "lead"
    note_request = next(
        request for request in requests if request.url.path.endswith("/notes")
    )
    note_body = json.loads(note_request.content)
    assert (
        "The upstairs unit is blowing warm air."
        in note_body["properties"]["hs_note_body"]
    )
    assert note_body["associations"][0]["to"]["id"] == "contact-123"
    assert note_body["associations"][0]["types"][0]["associationTypeId"] == 202


@pytest.mark.asyncio
async def test_capture_lead_updates_existing_contact_by_email() -> None:
    """A retry searches first and patches the existing contact instead of duplicating it."""
    methods: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        methods.append((request.method, request.url.path))
        if request.url.path.endswith("/contacts/search"):
            return httpx.Response(200, json={"results": [{"id": "contact-existing"}]})
        if request.url.path.endswith("/contacts/contact-existing"):
            return httpx.Response(200, json={"id": "contact-existing"})
        if request.url.path.endswith("/notes"):
            return httpx.Response(201, json={"id": "note-retry"})
        return httpx.Response(404)

    service = HubSpotLeadService(
        access_token="private-app-token",
        client_factory=_client_factory(handler),
    )
    result = await service.capture_lead(
        caller_name="Alex Lee",
        caller_email="alex@example.com",
        service_needed="Heating tune-up",
        issue_summary="Please inspect the system before winter.",
    )

    assert result["status"] == "updated"
    assert ("POST", "/crm/v3/objects/contacts/search") in methods
    assert ("PATCH", "/crm/v3/objects/contacts/contact-existing") in methods
    assert not any(
        method == "POST" and path.endswith("/contacts") and not path.endswith("/search")
        for method, path in methods
    )


@pytest.mark.asyncio
async def test_capture_lead_does_not_claim_completion_when_note_fails() -> None:
    """A partial CRM write is reported as attention-needed, not success."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/contacts/search"):
            return httpx.Response(200, json={"results": []})
        if request.url.path.endswith("/contacts"):
            return httpx.Response(201, json={"id": "contact-partial"})
        if request.url.path.endswith("/notes"):
            return httpx.Response(503, json={"message": "provider unavailable"})
        return httpx.Response(404)

    service = HubSpotLeadService(
        access_token="private-app-token",
        client_factory=_client_factory(handler),
    )

    result = await service.capture_lead(
        caller_name="Taylor Smith",
        caller_phone="602-555-0199",
        service_needed="Duct cleaning",
        issue_summary="Please inspect the system.",
    )

    assert result["status"] == "failed"
    assert result["error"]["code"] == "temporary_failure"
    assert result["crm"]["record_id"] == "contact-partial"
    assert result["note"]["status"] == "failed"


@pytest.mark.asyncio
async def test_capture_lead_returns_safe_provider_error() -> None:
    """Provider failures are actionable without copying HubSpot response bodies."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "secret provider diagnostic"})

    service = HubSpotLeadService(
        access_token="expired-token",
        client_factory=_client_factory(handler),
    )
    result = await service.capture_lead(
        caller_name="Taylor Smith",
        caller_phone="602-555-0199",
        service_needed="Duct cleaning",
        issue_summary="I would like an estimate.",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "authentication_required"
    assert "secret provider diagnostic" not in str(result)


@pytest.mark.asyncio
async def test_lead_tool_requires_confirmation_and_connection() -> None:
    """The model cannot mutate HubSpot without confirmation or a connection."""
    context = ToolContext(
        organization_id="org-1",
        agent_id="agent-1",
        session_id="session-1",
        is_demo=True,
        demo_slug="copper-ridge-service-request",
    )
    tool = HubspotLeadCaptureTool()

    confirmation = await tool.capture_lead(
        context=context,
        caller_name="Taylor Smith",
        service_needed="Duct cleaning",
        issue_summary="I would like an estimate.",
        user_confirmed=False,
        caller_email="taylor@example.com",
    )
    assert confirmation["status"] == "confirmation_required"

    not_configured = await tool.capture_lead(
        context=context,
        caller_name="Taylor Smith",
        service_needed="Duct cleaning",
        issue_summary="I would like an estimate.",
        user_confirmed=True,
        caller_email="taylor@example.com",
    )
    assert not_configured["status"] == "not_configured"
    assert not_configured["error"]["code"] == "authentication_required"


def test_hubspot_config_does_not_include_email_policy() -> None:
    """CRM capture owns only its CRM mutation, not email delivery."""
    assert "send_confirmation_email" not in HubspotLeadCaptureTool.Config.model_fields
