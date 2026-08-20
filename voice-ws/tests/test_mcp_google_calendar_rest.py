"""Tests for the Google Calendar REST connector (MCP server wrapping the REST API).

The connector (:mod:`shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest`)
exposes Google-Calendar-shaped MCP tools and, on each call, forwards the per-user
OAuth bearer (injected by the worker dispatch layer as ``Authorization: Bearer
<token>``) to Google's plain Calendar REST API
(``https://www.googleapis.com/calendar/v3``). The REST API is NOT gated by the
Google Workspace Developer Preview, so this works with a personal Gmail token
today — no Workspace account, no Preview enrollment. This is the path that
unblocks personal-Gmail testing while Google's remote ``calendarmcp.googleapis.com``
server remains Preview-gated.

All Google HTTP calls are faked with ``httpx.MockTransport`` by patching the
connector's ``_default_client_factory`` seam — no real network, no Google
credentials required.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import httpx
import pytest
import pytest_asyncio

from shared.voice_agents.tools import (
    google_calendar_appointment_service as appointment_service_module,
)
from shared.voice_agents.tools.mcp.models import McpServerConfig
from shared.voice_agents.tools.mcp.reference_servers import google_calendar_rest as gcr


@pytest_asyncio.fixture
async def google_calendar_rest_mcp_config(unused_tcp_port, monkeypatch):
    """Run the connector over Streamable HTTP for an in-process MCP test."""
    import uvicorn

    monkeypatch.setenv("MCP_ALLOW_LOCAL_URLS", "true")
    app = gcr.build_google_calendar_rest_server().streamable_http_app()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=unused_tcp_port,
            log_level="error",
        )
    )
    task = asyncio.create_task(server.serve())
    for _ in range(50):
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"http://127.0.0.1:{unused_tcp_port}/mcp", timeout=0.2)
            break
        except (httpx.ConnectError, httpx.ReadError):
            await asyncio.sleep(0.05)
    else:
        server.should_exit = True
        await task
        raise RuntimeError("MCP test server did not start")

    try:
        yield McpServerConfig(
            url=f"http://127.0.0.1:{unused_tcp_port}/mcp",
            name="google-calendar-appointment",
            headers={"Authorization": "Bearer TOK"},
        )
    finally:
        server.should_exit = True
        await task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_transport(monkeypatch, handler: Callable[[httpx.Request], httpx.Response]):
    """Point the connector's HTTP client factory at a MockTransport handler.

    The connector calls ``_default_client_factory()`` per tool invocation, so
    patching the module-level seam routes every Google call through ``handler``
    without touching real network.
    """
    monkeypatch.setattr(
        gcr,
        "_default_client_factory",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        appointment_service_module,
        "_default_client_factory",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _ok(json_body: dict) -> httpx.Response:
    return httpx.Response(200, json=json_body)


# ---------------------------------------------------------------------------
# list_calendars
# ---------------------------------------------------------------------------


class TestListCalendars:
    """list_calendars maps Google's calendarList response to a small JSON list."""

    async def test_returns_id_summary_primary(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.method == "GET"
            assert req.url.path == "/calendar/v3/users/me/calendarList"
            assert req.headers["authorization"] == "Bearer TOK"
            return _ok(
                {
                    "items": [
                        {
                            "id": "gauravd.chd@gmail.com",
                            "summary": "My Calendar",
                            "primary": True,
                        },
                        {"id": "work@group.com", "summary": "Work", "primary": False},
                    ]
                }
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.list_calendars_logic("TOK")
        assert result == [
            {"id": "gauravd.chd@gmail.com", "summary": "My Calendar", "primary": True},
            {"id": "work@group.com", "summary": "Work", "primary": False},
        ]

    async def test_empty_calendar_list(self, monkeypatch):
        _patch_transport(monkeypatch, lambda req: _ok({}))
        assert await gcr.list_calendars_logic("TOK") == []


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


class TestListEvents:
    """list_events maps Google's events list to compact event dicts."""

    async def test_returns_events_with_datetimes(self, monkeypatch):
        seen_params: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path == "/calendar/v3/calendars/primary/events"
            seen_params.update(req.url.params)
            return _ok(
                {
                    "items": [
                        {
                            "id": "evt1",
                            "summary": "Standup",
                            "start": {"dateTime": "2026-07-22T09:00:00-07:00"},
                            "end": {"dateTime": "2026-07-22T09:30:00-07:00"},
                        }
                    ]
                }
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.list_events_logic(
            "TOK",
            "2026-07-22T00:00:00-07:00",
            "2026-07-23T00:00:00-07:00",
            max_results=10,
        )
        assert result == [
            {
                "id": "evt1",
                "summary": "Standup",
                "start": "2026-07-22T09:00:00-07:00",
                "end": "2026-07-22T09:30:00-07:00",
            }
        ]
        # timeMin/timeMax forwarded; singleEvents + orderBy for correct ordering.
        assert seen_params["timeMin"] == "2026-07-22T00:00:00-07:00"
        assert seen_params["timeMax"] == "2026-07-23T00:00:00-07:00"
        assert seen_params["maxResults"] == "10"
        assert seen_params["singleEvents"] == "true"
        assert seen_params["orderBy"] == "startTime"

    async def test_all_day_event_falls_back_to_date_field(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            return _ok(
                {
                    "items": [
                        {
                            "id": "evt2",
                            "summary": "Holiday",
                            "start": {"date": "2026-07-23"},
                            "end": {"date": "2026-07-24"},
                        }
                    ]
                }
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.list_events_logic("TOK", "2026-07-22T00:00:00Z")
        assert result[0]["start"] == "2026-07-23"
        assert result[0]["end"] == "2026-07-24"

    async def test_uses_custom_calendar_id(self, monkeypatch):
        captured = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return _ok({"items": []})

        _patch_transport(monkeypatch, handler)
        await gcr.list_events_logic(
            "TOK", "2026-07-22T00:00:00Z", calendar_id="work@group.com"
        )
        assert captured["path"] == "/calendar/v3/calendars/work@group.com/events"


# ---------------------------------------------------------------------------
# get_event
# ---------------------------------------------------------------------------


class TestGetEvent:
    async def test_returns_full_event(self, monkeypatch):
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path == "/calendar/v3/calendars/primary/events/evt-123"
            return _ok(
                {
                    "id": "evt-123",
                    "summary": "1:1",
                    "start": {"dateTime": "2026-07-22T10:00:00Z"},
                    "end": {"dateTime": "2026-07-22T10:30:00Z"},
                    "htmlLink": "https://www.google.com/calendar/event?eid=evt-123",
                    "attendees": [{"email": "a@x.com"}, {"email": "b@x.com"}],
                }
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.get_event_logic("TOK", "evt-123")
        assert result == {
            "id": "evt-123",
            "summary": "1:1",
            "start": "2026-07-22T10:00:00Z",
            "end": "2026-07-22T10:30:00Z",
            "html_link": "https://www.google.com/calendar/event?eid=evt-123",
            "attendees": ["a@x.com", "b@x.com"],
        }

    async def test_not_found_returns_error_payload(self, monkeypatch):
        _patch_transport(
            monkeypatch,
            lambda req: httpx.Response(404, json={"error": {"message": "Not Found"}}),
        )
        assert await gcr.get_event_logic("TOK", "nope") == {"error": "not_found"}


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------


class TestCreateEvent:
    """create_event is the front-desk booking tool: it formats the caller's
    details into the organization's calendar event (caller name + purpose in the
    summary, contact details in the description, caller email as an invitee, end
    computed from duration). It does NOT accept a free-form summary/description
    — the agent supplies caller fields and the tool formats the event.
    """

    async def test_formats_caller_details_into_event(self, monkeypatch):
        posted: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            assert req.method == "POST"
            assert req.url.path == "/calendar/v3/calendars/primary/events"
            assert req.headers["authorization"] == "Bearer TOK"
            posted.update(json.loads(req.content.decode()))
            return httpx.Response(
                201, json={"id": "new-evt", "htmlLink": "https://g/cal/new"}
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.create_event_logic(
            "TOK",
            caller_name="Jane Doe",
            purpose="Dental cleaning",
            start="2026-07-23T14:00:00-07:00",
            duration_minutes=30,
            caller_phone="+15551234567",
            caller_email="jane@example.com",
            caller_dob="1990-04-12",
        )
        assert result == {
            "id": "new-evt",
            "status": "created",
            "summary": "Appointment: Jane Doe — Dental cleaning",
            "html_link": "https://g/cal/new",
        }
        # Summary carries the caller's name + purpose.
        assert "Jane Doe" in posted["summary"]
        assert "Dental cleaning" in posted["summary"]
        # Description carries purpose + every captured contact detail.
        assert "Dental cleaning" in posted["description"]
        assert "+15551234567" in posted["description"]
        assert "jane@example.com" in posted["description"]
        assert "1990-04-12" in posted["description"]
        # Caller email added as an invitee.
        assert posted["attendees"] == [{"email": "jane@example.com"}]
        # End computed from start + duration_minutes.
        assert posted["start"] == {"dateTime": "2026-07-23T14:00:00-07:00"}
        assert posted["end"]["dateTime"].startswith("2026-07-23T14:30:00")

    async def test_minimal_booking_without_optional_contact(self, monkeypatch):
        posted: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            posted.update(json.loads(req.content.decode()))
            return httpx.Response(201, json={"id": "new-evt"})

        _patch_transport(monkeypatch, handler)
        result = await gcr.create_event_logic(
            "TOK",
            caller_name="John Smith",
            purpose="Checkup",
            start="2026-07-23T09:00:00-07:00",
        )
        assert result["status"] == "created"
        assert "John Smith" in posted["summary"]
        # No email -> no invitee.
        assert "attendees" not in posted
        # Optional contact lines omitted when not provided.
        assert "Phone:" not in posted["description"]
        assert "Email:" not in posted["description"]
        assert "Date of birth:" not in posted["description"]
        # Default 30-minute duration.
        assert posted["end"]["dateTime"].startswith("2026-07-23T09:30:00")

    async def test_custom_calendar_id_used(self, monkeypatch):
        captured: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            captured["path"] = req.url.path
            return httpx.Response(201, json={"id": "x"})

        _patch_transport(monkeypatch, handler)
        await gcr.create_event_logic(
            "TOK",
            caller_name="A",
            purpose="P",
            start="2026-07-23T09:00:00-07:00",
            calendar_id="clinic@group.com",
        )
        assert captured["path"] == "/calendar/v3/calendars/clinic@group.com/events"

    async def test_error_returns_error_dict(self, monkeypatch):
        _patch_transport(
            monkeypatch,
            lambda req: httpx.Response(
                403, json={"error": {"message": "Insufficient scopes"}}
            ),
        )
        result = await gcr.create_event_logic(
            "TOK", caller_name="A", purpose="P", start="2026-07-23T09:00:00-07:00"
        )
        assert result == {"error": "Insufficient scopes", "status": 403}


# ---------------------------------------------------------------------------
# check_availability (freebusy)
# ---------------------------------------------------------------------------


class TestCheckAvailability:
    async def test_busy_when_window_overlaps(self, monkeypatch):
        posted: dict = {}

        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path == "/calendar/v3/freeBusy"
            assert req.method == "POST"
            posted.update(json.loads(req.content.decode()))
            return _ok(
                {
                    "calendars": {
                        "primary": {
                            "busy": [
                                {
                                    "start": "2026-07-22T10:00:00Z",
                                    "end": "2026-07-22T10:30:00Z",
                                }
                            ]
                        }
                    }
                }
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.check_availability_logic(
            "TOK", "2026-08-20T10:00:00Z", "2026-08-20T11:00:00Z"
        )
        assert result == {"status": "busy"}
        assert posted["timeMin"] == "2026-08-20T10:00:00Z"
        assert posted["timeMax"] == "2026-08-20T11:00:00Z"
        assert posted["items"] == [{"id": "primary"}]

    async def test_free_when_no_busy_blocks(self, monkeypatch):
        _patch_transport(
            monkeypatch, lambda req: _ok({"calendars": {"primary": {"busy": []}}})
        )
        assert await gcr.check_availability_logic(
            "TOK", "2026-08-20T10:00:00Z", "2026-08-20T11:00:00Z"
        ) == {"status": "free"}

    async def test_busy_when_google_keys_primary_as_email(self, monkeypatch):
        """Google freeBusy resolves ``primary`` to the account email in response keys.

        Looking up ``calendars["primary"]`` misses busy blocks and falsely reports
        free — the real API shape keys by email (e.g. ``user@gmail.com``).
        """

        def handler(req: httpx.Request) -> httpx.Response:
            return _ok(
                {
                    "calendars": {
                        "gauravd.chd@gmail.com": {
                            "busy": [
                                {
                                    "start": "2026-08-20T17:00:00Z",
                                    "end": "2026-08-20T17:30:00Z",
                                }
                            ]
                        }
                    }
                }
            )

        _patch_transport(monkeypatch, handler)
        result = await gcr.check_availability_logic(
            "TOK",
            "2026-08-20T10:00:00-07:00",
            "2026-08-20T10:30:00-07:00",
            calendar_id="primary",
        )
        assert result == {"status": "busy"}

    async def test_free_when_email_keyed_primary_has_empty_busy(self, monkeypatch):
        """Email-keyed primary calendar with empty busy list is free."""
        _patch_transport(
            monkeypatch,
            lambda req: _ok({"calendars": {"user@example.com": {"busy": []}}}),
        )
        assert await gcr.check_availability_logic(
            "TOK", "2026-08-20T10:00:00-07:00", "2026-08-20T10:30:00-07:00"
        ) == {"status": "free"}

    async def test_past_window_returns_past_without_calling_google(self, monkeypatch):
        """Slots before the reference instant must not be offered as free."""
        called = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return _ok({"calendars": {"primary": {"busy": []}}})

        _patch_transport(monkeypatch, handler)
        reference = datetime(2026, 8, 3, 16, 30, tzinfo=timezone(timedelta(hours=-7)))
        result = await gcr.check_availability_logic(
            "TOK",
            "2026-08-03T15:00:00-07:00",
            "2026-08-03T15:30:00-07:00",
            reference_now=reference,
        )
        assert result["status"] == "past"
        assert "message" in result
        assert called["n"] == 0


# ---------------------------------------------------------------------------
# error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    async def test_401_returns_error_with_status(self, monkeypatch):
        _patch_transport(
            monkeypatch,
            lambda req: httpx.Response(
                401, json={"error": {"message": "Invalid Credentials"}}
            ),
        )
        result = await gcr.list_events_logic("BAD", "2026-07-22T00:00:00Z")
        assert result == {"error": "Invalid Credentials", "status": 401}

    async def test_403_returns_error_with_status(self, monkeypatch):
        _patch_transport(
            monkeypatch,
            lambda req: httpx.Response(
                403, json={"error": {"message": "Insufficient scopes"}}
            ),
        )
        result = await gcr.list_calendars_logic("BAD")
        assert result["status"] == 403
        assert result["error"] == "Insufficient scopes"

    async def test_error_with_no_message_falls_back_to_status(self, monkeypatch):
        _patch_transport(monkeypatch, lambda req: httpx.Response(500, json={}))
        result = await gcr.list_calendars_logic("BAD")
        assert result["status"] == 500
        assert "500" in result["error"]


# ---------------------------------------------------------------------------
# bearer extraction
# ---------------------------------------------------------------------------


class TestBearerExtraction:
    def test_bearer_extracts_token(self):
        ctx = _ctx_with_header("authorization", "Bearer my-token-abc")
        assert gcr._bearer(ctx) == "my-token-abc"

    def test_bearer_missing_raises(self):
        ctx = _ctx_with_header("authorization", None)
        with pytest.raises(ValueError):
            gcr._bearer(ctx)

    def test_bearer_non_bearer_scheme_raises(self):
        ctx = _ctx_with_header("authorization", "Basic abc123")
        with pytest.raises(ValueError):
            gcr._bearer(ctx)


def _ctx_with_header(name: str, value: Any) -> Any:
    """Build a minimal stand-in for a FastMCP Context with a request header."""
    request = type("Req", (), {})()
    request.headers = httpx.Headers({name: value} if value else {})
    ctx = type("Ctx", (), {})()
    ctx.request_context = type("RC", (), {})()
    ctx.request_context.request = request
    return ctx


# ---------------------------------------------------------------------------
# Full pipeline: in-process MCP server + McpClient + Pipecat tool handler
# ---------------------------------------------------------------------------


class TestRestConnectorFullPipeline:
    """The connector behaves like any other MCP server from the platform's POV."""

    async def test_discovers_appointment_tools(self, google_calendar_rest_mcp_config):
        from shared.voice_agents.tools.mcp.client import McpClient

        async with McpClient(google_calendar_rest_mcp_config) as client:
            names = {t.name for t in await client.list_tools()}
        assert names == {
            "find_available_slots",
            "check_availability",
            "find_appointments",
            "create_appointment",
            "update_appointment",
            "cancel_appointment",
        }

    async def test_find_appointments_round_trip_through_mcp(
        self, monkeypatch, google_calendar_rest_mcp_config
    ):
        from shared.voice_agents.tools.mcp.client import McpClient

        def handler(req: httpx.Request) -> httpx.Response:
            assert req.url.path == "/calendar/v3/calendars/primary/events"
            return _ok(
                {
                    "items": [
                        {
                            "id": "evt1",
                            "summary": "Standup",
                            "start": {"dateTime": "2026-07-22T09:00:00Z"},
                            "end": {"dateTime": "2026-07-22T09:30:00Z"},
                        }
                    ]
                }
            )

        _patch_transport(monkeypatch, handler)
        async with McpClient(google_calendar_rest_mcp_config) as client:
            res = await client.call_tool(
                "find_appointments",
                {
                    "window_start": "2026-07-22T00:00:00Z",
                    "window_end": "2026-07-23T00:00:00Z",
                },
            )
        assert res.is_error is False
        payload = json.loads(res.content[0]["text"])
        assert payload.get("appointments"), payload
        assert payload["appointments"][0]["summary"] == "Standup"

    async def test_create_appointment_round_trip_through_mcp(
        self, monkeypatch, google_calendar_rest_mcp_config
    ):
        from shared.voice_agents.tools.mcp.client import McpClient

        def handler(req: httpx.Request) -> httpx.Response:
            body = json.loads(req.content.decode())
            if req.url.path == "/calendar/v3/freeBusy":
                return _ok({"calendars": {"primary": {"busy": []}}})
            assert "Jane Doe" in body["summary"]
            return httpx.Response(
                201, json={"id": "new-evt", "htmlLink": "https://g/cal/new"}
            )

        _patch_transport(monkeypatch, handler)
        async with McpClient(google_calendar_rest_mcp_config) as client:
            res = await client.call_tool(
                "create_appointment",
                {
                    "caller_name": "Jane Doe",
                    "purpose": "Cleaning",
                    "start_time": "2026-08-20T14:00:00-07:00",
                    "duration_minutes": 30,
                    "user_confirmed": True,
                },
            )
        payload = json.loads(res.content[0]["text"])
        assert payload["status"] == "created", payload
        assert "Jane Doe" in payload["appointment"]["caller_name"]


# ---------------------------------------------------------------------------
# Gemini schema cleanliness guard (regression guard for the silent-agent bug)
# ---------------------------------------------------------------------------


class TestToolDescriptionsPromptFrontDeskBehavior:
    """The tool descriptions the model sees live must instruct front-desk
    behavior: book into the ORGANIZATION'S calendar (not the caller's), collect
    the caller's details, check availability first, and get EXPLICIT
    confirmation before booking. Regression guard so a future terse rewrite
    doesn't silently restore the "book immediately without asking anything"
    behavior the user reported on 2026-07-22.
    """

    async def test_create_appointment_description_enforces_front_desk_protocol(
        self, google_calendar_rest_mcp_config
    ):
        from shared.voice_agents.tools.mcp.client import McpClient

        async with McpClient(google_calendar_rest_mcp_config) as client:
            tools = {t.name: t for t in await client.list_tools()}

        desc = (tools["create_appointment"].description or "").lower()
        # Books into the organization's calendar, not the caller's.
        assert "organization" in desc
        # Must gather the caller's details first.
        assert "collect" in desc and "name" in desc
        # Must confirm + get explicit confirmation before booking.
        assert "confirm" in desc and "explicit" in desc
        # Must check availability first to avoid double-booking.
        assert "check" in desc and "conflict" in desc

        # Caller-detail args exist in the schema so the model is prompted to
        # collect them during the call (not just free-text a summary).
        props = tools["create_appointment"].input_schema.get("properties", {})
        for arg in (
            "caller_name",
            "purpose",
            "caller_phone",
            "caller_email",
            "duration_minutes",
            "user_confirmed",
        ):
            assert arg in props, f"create_appointment missing front-desk arg {arg}"

    async def test_check_availability_description_mentions_avoiding_double_booking(
        self, google_calendar_rest_mcp_config
    ):
        from shared.voice_agents.tools.mcp.client import McpClient

        async with McpClient(google_calendar_rest_mcp_config) as client:
            tools = {t.name: t for t in await client.list_tools()}
        desc = (tools["check_availability"].description or "").lower()
        assert "free" in desc and "busy" in desc

    async def test_update_description_covers_all_existing_appointment_changes(
        self, google_calendar_rest_mcp_config
    ):
        """MCP guidance must route existing changes to update_appointment."""
        from shared.voice_agents.tools.mcp.client import McpClient

        async with McpClient(google_calendar_rest_mcp_config) as client:
            tools = {t.name: t for t in await client.list_tools()}

        update_desc = (tools["update_appointment"].description or "").lower()
        check_desc = (tools["check_availability"].description or "").lower()

        for phrase in ("reschedul", "extend", "shorten", "existing appointment"):
            assert phrase in update_desc
        assert "new_duration_minutes" in update_desc
        assert "new booking" in check_desc
        assert "existing appointment" in check_desc


class TestSchemasAreGeminiClean:
    """Every tool schema the connector reports must pass Gemini's strict
    FunctionDeclaration validator (after the worker's sanitize step), so the
    realtime session never aborts on a schema key Gemini rejects. Mirrors the
    guard in voice-ws MCP dispatch tests.
    """

    async def test_all_tool_schemas_pass_gemini_validation(
        self, google_calendar_rest_mcp_config
    ):
        types = pytest.importorskip("google.genai").types

        from shared.voice_agents.tools.mcp.client import McpClient
        from shared.voice_agents.tools.mcp.schema_sanitize import (
            build_gemini_function_declaration,
        )

        async with McpClient(google_calendar_rest_mcp_config) as client:
            tools = await client.list_tools()

        # Must not raise for any tool — this is the exact check that crashed the
        # realtime session before the sanitization fix.
        for tool in tools:
            built = build_gemini_function_declaration(tool)
            fd = types.FunctionDeclaration.model_validate(built)
            assert fd.name == tool.name
