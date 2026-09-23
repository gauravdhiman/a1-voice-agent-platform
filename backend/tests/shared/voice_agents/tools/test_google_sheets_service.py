"""Contract tests for the configurable, header-aware Sheets service."""

import json
from datetime import datetime, timezone

import httpx
import pytest

from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.google_sheets_service import GoogleSheetsService

HEADERS = [
    "Submission ID",
    "Captured at",
    "Lead source",
    "Caller name",
    "Caller email",
    "Caller phone",
    "Service needed",
    "Issue summary",
    "Service address",
    "Urgency",
    "Preferred callback window",
    "Status",
]


def _client_factory(handler):
    """Build a fresh async HTTP client over one deterministic transport."""
    transport = httpx.MockTransport(handler)

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    return factory


def _service(handler) -> GoogleSheetsService:
    """Create a demo-shaped service with a bounded working area."""
    return GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Orders!A1:L1000",
        header_range="Orders!A1:L1",
        agent_columns=(
            "Caller name, Caller email, Caller phone, Service needed, " "Issue summary"
        ),
        idempotency_column="Submission ID",
        timestamp_column="Captured at",
        source_column="Lead source",
        source_value="24x7 AI public demo",
        status_column="Status",
        status_value="New",
        required_columns="Caller name, Service needed",
        record_label="order request",
        client_factory=_client_factory(handler),
    )


def _context() -> ToolContext:
    """Return a fixed session context for deterministic generated cells."""
    return ToolContext(
        session_id="session-1",
        current_time=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
    )


def test_find_rows_model_schema_omits_empty_column_enum_value() -> None:
    """Optional all-column searches stay valid for Gemini Live schemas."""
    service = _service(lambda _request: httpx.Response(200))

    properties = service.model_function_properties(
        "find_rows",
        {"column": {"type": "string"}},
    )

    assert properties["column"]["enum"] == [
        "Caller name",
        "Caller email",
        "Caller phone",
        "Service needed",
        "Issue summary",
        "Submission ID",
        "Captured at",
        "Lead source",
        "Status",
    ]
    assert "" not in properties["column"]["enum"]


@pytest.mark.asyncio
async def test_create_row_uses_headers_and_generated_columns() -> None:
    """A row is assembled from header keys, not model-supplied column arrays."""
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/Orders!A1:L1"):
            return httpx.Response(200, json={"values": [HEADERS]})
        if request.method == "GET":
            return httpx.Response(200, json={"values": [HEADERS]})
        return httpx.Response(
            200,
            json={"updates": {"updatedRange": "Orders!A2:L2"}},
        )

    service = _service(handler)
    result = await service.create_row(
        context=_context(),
        values={
            "Caller name": "Maria Garcia",
            "Caller phone": "602-555-0101",
            "Service needed": "Two Sonoran grain bowls",
        },
    )

    assert result["status"] == "created"
    assert result["sheet"]["record_type"] == "row"
    assert result["sheet"]["record_label"] == "order request"
    assert result["sheet"]["record_id"] == "session-1"
    assert len(requests) == 3
    body = json.loads(requests[-1].content)
    assert body["values"] == [
        [
            "session-1",
            "2026-09-20T12:00:00Z",
            "24x7 AI public demo",
            "Maria Garcia",
            "",
            "602-555-0101",
            "Two Sonoran grain bowls",
            "",
            "",
            "",
            "",
            "New",
        ]
    ]
    assert all("google-access-token" not in str(request) for request in requests)


@pytest.mark.asyncio
async def test_discover_sheet_headers_returns_tabs_without_cell_data() -> None:
    """Discovery exposes tab metadata and row-one labels for setup only."""
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        request_url = str(request.url)
        if request.url.path.endswith("/spreadsheets/sheet-id-123456"):
            return httpx.Response(
                200,
                json={
                    "sheets": [
                        {"properties": {"title": "Restaurant Orders", "sheetId": 42}},
                        {"properties": {"title": "Empty tab", "sheetId": 43}},
                    ]
                },
            )
        if "Restaurant%20Orders" in request_url:
            return httpx.Response(
                200,
                json={"values": [["Customer", "Items", "Quantity"]]},
            )
        if "Empty%20tab" in request_url:
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"error": "unexpected request"})

    result = await _service(handler).discover_sheet_headers()

    assert result["status"] == "succeeded"
    assert result["provider"] == "google_sheets"
    assert result["sheets"] == [
        {
            "title": "Restaurant Orders",
            "sheet_id": 42,
            "headers": ["Customer", "Items", "Quantity"],
            "header_range": "'Restaurant Orders'!A1:CV1",
            "issues": [],
        },
        {
            "title": "Empty tab",
            "sheet_id": 43,
            "headers": [],
            "header_range": "'Empty tab'!A1:CV1",
            "issues": ["Add a header row to this tab before configuring the agent."],
        },
    ]
    assert len(requests) == 3
    assert all("google-access-token" not in str(request) for request in requests)


@pytest.mark.asyncio
async def test_create_row_deduplicates_same_session_before_append() -> None:
    """A retry finds the configured idempotency key without a second write."""
    methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.url.path.endswith("/Orders!A1:L1"):
            return httpx.Response(200, json={"values": [HEADERS]})
        return httpx.Response(
            200,
            json={
                "values": [
                    HEADERS,
                    [
                        "session-1",
                        "",
                        "",
                        "Maria Garcia",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "New",
                    ],
                ]
            },
        )

    result = await _service(handler).create_row(
        context=_context(),
        values={"Caller name": "Maria Garcia", "Service needed": "Lunch"},
    )

    assert result["status"] == "created"
    assert result["deduplicated"] is True
    assert result["sheet"]["updated_range"] == "Orders!A2"
    assert methods == ["GET", "GET"]


@pytest.mark.asyncio
async def test_read_and_find_return_header_keyed_rows() -> None:
    """Reads and searches expose stable objects with bounded row metadata."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "values": [
                    HEADERS,
                    [
                        "session-1",
                        "",
                        "",
                        "Maria Garcia",
                        "",
                        "",
                        "Lunch",
                        "",
                        "",
                        "",
                        "",
                        "New",
                    ],
                    [
                        "session-2",
                        "",
                        "",
                        "Taylor Smith",
                        "",
                        "",
                        "Dinner",
                        "",
                        "",
                        "",
                        "",
                        "New",
                    ],
                ]
            },
        )

    service = _service(handler)
    rows = await service.read_rows(context=_context(), max_rows=1)
    matches = await service.find_rows(
        context=_context(), query="maria", column="Caller name"
    )

    assert rows["row_count"] == 1
    assert rows["truncated"] is True
    assert "Service address" not in rows["headers"]
    assert rows["rows"][0]["Caller name"] == "Maria Garcia"
    assert rows["rows"][0]["row_number"] == 2
    assert matches["match_count"] == 1
    assert matches["rows"][0]["Service needed"] == "Lunch"


@pytest.mark.asyncio
async def test_create_row_rejects_unknown_columns_before_writing() -> None:
    """The model cannot write arbitrary columns or provider ranges."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"values": [HEADERS]})

    result = await _service(handler).create_row(
        context=_context(),
        values={"Not a sheet column": "secret"},
    )

    assert result["status"] == "needs_details"
    assert result["error"]["code"] == "invalid_input"
    assert calls == 1


@pytest.mark.asyncio
async def test_create_row_reports_all_missing_required_columns() -> None:
    """One retry response should name every required field the caller still needs."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"values": [HEADERS]})

    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Orders!A1:L1000",
        header_range="Orders!A1:L1",
        agent_columns="Caller name, Caller email, Caller phone, Service needed",
        required_columns="Caller name, Caller email, Caller phone, Service needed",
        client_factory=_client_factory(handler),
    )

    result = await service.create_row(
        context=_context(),
        values={"Caller name": "Maria Garcia", "Service needed": "Lunch"},
    )

    assert result["status"] == "needs_details"
    assert result["error"]["field"] == "values"
    assert (
        result["message"] == "Provide a value for every required column before saving: "
        "Caller email, Caller phone."
    )


@pytest.mark.asyncio
async def test_create_row_rejects_model_values_for_managed_columns() -> None:
    """The model cannot override generated metadata during a create."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"values": [HEADERS]})

    result = await _service(handler).create_row(
        context=_context(),
        values={"Caller name": "Maria Garcia", "Submission ID": "forged"},
    )

    assert result["status"] == "needs_details"
    assert result["error"]["field"] == "Submission ID"
    assert "Managed columns" in result["error"]["message"]


@pytest.mark.asyncio
async def test_read_rows_cannot_expand_configured_working_area() -> None:
    """A model-supplied range may narrow the attachment, never widen it."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"values": [HEADERS]})

    result = await _service(handler).read_rows(
        context=_context(), range="Orders!A1:M1000"
    )

    assert result["status"] == "needs_details"
    assert result["error"]["code"] == "invalid_input"
    assert calls == 0


@pytest.mark.asyncio
async def test_find_rows_rejects_invalid_limit_before_provider_io() -> None:
    """A malformed result limit must not trigger a provider read."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"values": [HEADERS]})

    result = await _service(handler).find_rows(
        context=_context(), query="Maria", max_results=101
    )

    assert result["status"] == "needs_details"
    assert result["error"]["field"] == "max_results"
    assert calls == 0


@pytest.mark.asyncio
async def test_update_row_requires_one_exact_match() -> None:
    """Partial updates replace one matched row and refuse ambiguous matches."""
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "PUT":
            return httpx.Response(200, json={"updatedRange": "Orders!A2:L2"})
        if request.url.path.endswith("/Orders!A1:L1"):
            return httpx.Response(200, json={"values": [HEADERS]})
        return httpx.Response(
            200,
            json={
                "values": [
                    HEADERS,
                    [
                        "session-1",
                        "",
                        "",
                        "Maria Garcia",
                        "",
                        "",
                        "Lunch",
                        "",
                        "",
                        "",
                        "",
                        "New",
                    ],
                ]
            },
        )

    result = await _service(handler).update_row(
        context=_context(),
        match_column="Caller name",
        match_value="Maria Garcia",
        values={"Service needed": "Follow-up inspection"},
    )

    assert result["status"] == "updated"
    assert result["sheet"]["updated_range"] == "Orders!A2:L2"
    assert calls == ["GET", "GET", "PUT"]


@pytest.mark.asyncio
async def test_update_row_rejects_managed_column_changes() -> None:
    """A correction may not overwrite platform-generated metadata."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"values": [HEADERS]})

    result = await _service(handler).update_row(
        context=_context(),
        match_column="Submission ID",
        match_value="session-1",
        values={"Status": "Fulfilled"},
    )

    assert result["status"] == "needs_details"
    assert result["error"]["field"] == "Status"
    assert "cannot be changed" in result["error"]["message"]


@pytest.mark.asyncio
async def test_update_row_refuses_ambiguous_match_without_writing() -> None:
    """An exact match that is not unique cannot overwrite multiple rows."""
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "PUT":
            pytest.fail("ambiguous updates must never write")
        if request.url.path.endswith("/Orders!A1:L1"):
            return httpx.Response(200, json={"values": [HEADERS]})
        duplicate = [
            "session-1",
            "",
            "",
            "Maria Garcia",
            "",
            "",
            "Lunch",
            "",
            "",
            "",
            "",
            "New",
        ]
        return httpx.Response(200, json={"values": [HEADERS, duplicate, duplicate]})

    result = await _service(handler).update_row(
        context=_context(),
        match_column="Submission ID",
        match_value="session-1",
        values={"Service needed": "Follow-up inspection"},
    )

    assert result["status"] == "conflict"
    assert result["error"]["code"] == "ambiguous_match"
    assert result["error"]["retryable"] is True
    assert calls == ["GET", "GET"]


@pytest.mark.asyncio
async def test_create_row_returns_safe_provider_failure() -> None:
    """Provider outages are retryable and never expose response details."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "internal token data"}})

    result = await _service(handler).create_row(
        context=_context(),
        values={"Caller name": "Maria Garcia", "Service needed": "Lunch"},
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "temporary_failure"
    assert result["error"]["retryable"] is True
    assert "internal token data" not in str(result)


def test_configuration_requires_destination_and_keeps_ranges_on_one_tab() -> None:
    """Invalid destinations are visible before a runtime call begins."""
    service = GoogleSheetsService(
        access_token="",
        spreadsheet_id="",
        default_range="Orders!A1:L1000",
        header_range="Other!A1:L1",
        status_value="New",
    )

    assert service.configuration_issues() == [
        "spreadsheet destination is not set",
        "agent fields are not set",
        "header range must use the configured sheet tab",
        "status column is not set",
    ]


@pytest.mark.asyncio
async def test_create_row_supports_use_case_specific_agent_columns() -> None:
    """A restaurant schema can use its own headers and generated metadata."""
    headers = [
        "Order ID",
        "Created At",
        "Channel",
        "Customer Name",
        "Phone",
        "Items",
        "Quantity",
        "Pickup Time",
        "Special Instructions",
        "Order Status",
    ]
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"values": [headers]})
        return httpx.Response(
            200,
            json={"updates": {"updatedRange": "Orders!A2:J2"}},
        )

    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Orders!A1:J1000",
        header_range="Orders!A1:J1",
        agent_columns="Customer Name, Phone, Items, Quantity, Pickup Time, Special Instructions",
        idempotency_column="Order ID",
        timestamp_column="Created At",
        source_column="Channel",
        source_value="24x7 AI public demo",
        status_column="Order Status",
        status_value="New",
        required_columns="Customer Name, Items, Quantity",
        record_label="restaurant order",
        client_factory=_client_factory(handler),
    )

    result = await service.create_row(
        context=_context(),
        values={
            "Customer Name": "Maria Garcia",
            "Phone": "602-555-0101",
            "Items": "Sonoran grain bowl",
            "Quantity": 2,
            "Pickup Time": "6:30 PM",
        },
    )

    assert result["status"] == "created"
    body = json.loads(requests[-1].content)
    assert body["values"] == [
        [
            "session-1",
            "2026-09-20T12:00:00Z",
            "24x7 AI public demo",
            "Maria Garcia",
            "602-555-0101",
            "Sonoran grain bowl",
            "2",
            "6:30 PM",
            "",
            "New",
        ]
    ]


@pytest.mark.asyncio
async def test_restaurant_schema_keeps_quantities_in_items_when_no_quantity_header() -> (
    None
):
    """Sofia's compact sheet stores item names and quantities in one business cell."""
    headers = [
        "Submission ID",
        "Captured at",
        "Lead source",
        "Customer Name",
        "Phone",
        "Items",
    ]
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"values": [headers]})
        return httpx.Response(
            200,
            json={"updates": {"updatedRange": "Restaurant Orders!A2:F2"}},
        )

    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Restaurant Orders!A1:F1000",
        header_range="Restaurant Orders!A1:F1",
        agent_columns="Customer Name, Phone, Items",
        idempotency_column="Submission ID",
        timestamp_column="Captured at",
        source_column="Lead source",
        source_value="24x7 AI Demo Call",
        required_columns="Customer Name, Phone, Items",
        record_label="order request",
        client_factory=_client_factory(handler),
    )

    result = await service.create_row(
        context=_context(),
        values={
            "Customer Name": "Maria Garcia",
            "Phone": "602-555-0101",
            "Items": "2 Ember chicken sandwiches, 1 Citrus-chili cauliflower",
        },
    )

    assert result["status"] == "created"
    body = json.loads(requests[-1].content)
    assert body["values"][0][3:] == [
        "Maria Garcia",
        "602-555-0101",
        "2 Ember chicken sandwiches, 1 Citrus-chili cauliflower",
    ]


@pytest.mark.asyncio
async def test_agent_columns_reject_unconfigured_business_fields() -> None:
    """Configured field guidance is also enforced at the write boundary."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"values": [HEADERS]},
        )

    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Orders!A1:L1000",
        header_range="Orders!A1:L1",
        agent_columns="Caller name, Service needed",
        required_columns="Caller name, Service needed",
        client_factory=_client_factory(handler),
    )

    result = await service.create_row(
        context=_context(),
        values={"Caller name": "Maria Garcia", "Urgency": "today"},
    )

    assert result["status"] == "needs_details"
    assert result["error"]["code"] == "invalid_input"
    assert result["error"]["field"] == "Urgency"
    assert "configured agent fields" in result["error"]["message"]
    assert calls == 1


@pytest.mark.asyncio
async def test_agent_columns_reject_header_aliases_before_writing() -> None:
    """Snake-case aliases cannot silently map to configured human headers."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"values": [HEADERS]})

    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Orders!A1:L1000",
        header_range="Orders!A1:L1",
        agent_columns="Caller Name, Service needed",
        required_columns="Caller Name, Service needed",
        client_factory=_client_factory(handler),
    )

    result = await service.create_row(
        context=_context(),
        values={"Caller_Name": "Maria Garcia", "Service_needed": "Lunch"},
    )

    assert result["status"] == "needs_details"
    assert result["error"]["code"] == "invalid_input"
    assert result["error"]["field"] == "Caller_Name"


@pytest.mark.asyncio
async def test_stale_saved_columns_fail_as_configuration_error_before_writing() -> None:
    """A changed sheet schema asks the admin to rediscover instead of retrying bad input."""
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(
            200,
            json={
                "values": [
                    [
                        "Submission ID",
                        "Captured at",
                        "Lead source",
                        "Customer Name",
                        "Phone",
                        "Items",
                    ]
                ]
            },
        )

    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        default_range="Restaurant Orders!A1:F1000",
        header_range="Restaurant Orders!A1:F1",
        agent_columns="Customer Name, Items, Quantity",
        idempotency_column="Submission ID",
        timestamp_column="Captured at",
        source_column="Lead source",
        source_value="24x7 AI public demo",
        required_columns="Customer Name, Items, Quantity",
        client_factory=_client_factory(handler),
    )

    result = await service.create_row(
        context=_context(),
        values={"Customer Name": "Maria Garcia", "Items": "Lunch"},
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_configuration"
    assert "Quantity" in result["message"]
    assert "Re-discover" in result["message"]
    assert calls == ["GET"]


def test_model_guidance_excludes_managed_columns_from_required_business_fields() -> (
    None
):
    """Generated metadata must not be presented as caller data to collect."""
    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        agent_columns="Submission ID, Captured at, Customer Name, Items",
        idempotency_column="Submission ID",
        timestamp_column="Captured at",
        required_columns="Submission ID, Customer Name",
    )

    guidance = service.model_function_guidance("create_row")

    fields_text = guidance.split(". Pass business data", 1)[0]
    required_text = guidance.split("Required for create_row:", 1)[1].split(
        " The attachment manages", 1
    )[0]
    assert "Customer Name" in fields_text
    assert "Items" in fields_text
    assert "Submission ID" not in fields_text
    assert "Captured at" not in fields_text
    assert "Customer Name" in required_text
    assert "Submission ID" not in required_text


def test_configuration_rejects_reusing_one_header_for_managed_roles() -> None:
    """One sheet column cannot safely hold two generated metadata values."""
    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        agent_columns="Customer Name",
        idempotency_column="Metadata",
        timestamp_column="Metadata",
    )

    assert (
        "managed columns must use different headers" in service.configuration_issues()
    )


def test_configuration_rejects_managed_headers_in_agent_fields() -> None:
    """Generated metadata cannot also be presented as caller fields."""
    service = GoogleSheetsService(
        access_token="google-access-token",
        spreadsheet_id="sheet-id-123456",
        agent_columns="Customer Name, Status",
        status_column="Status",
        status_value="New",
    )

    assert service.configuration_issues() == [
        "managed columns must be removed from Agent fields: Status"
    ]
