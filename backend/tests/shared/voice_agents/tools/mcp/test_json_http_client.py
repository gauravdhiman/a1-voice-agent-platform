"""Tests for JSON-only MCP discovery."""

from __future__ import annotations

import json

import httpx
import pytest

from shared.voice_agents.tools.mcp.json_http_client import list_tools_json_http
from shared.voice_agents.tools.mcp.models import McpServerConfig


def _twenty_like_handler(request: httpx.Request) -> httpx.Response:
    auth = request.headers.get("authorization")
    if auth != "Bearer good-key":
        return httpx.Response(401, json={"statusCode": 401}, request=request)

    body = json.loads(request.content.decode())
    method = body.get("method")

    if method == "notifications/initialized":
        return httpx.Response(202, request=request)

    if method == "initialize":
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "Twenty MCP Server", "version": "0.0.1"},
            },
        }
    elif method == "tools/list":
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "tools": [
                    {
                        "name": "execute_tool",
                        "description": "Run a tool",
                        "inputSchema": {
                            "jsonSchema": {"type": "object", "properties": {}},
                        },
                    }
                ]
            },
        }
    else:
        return httpx.Response(404, request=request)

    return httpx.Response(200, json=payload, request=request)


def _strict_streamable_handler(request: httpx.Request) -> httpx.Response:
    """Reject JSON-only negotiation like DeepWiki and Context7 do."""
    if "text/event-stream" not in request.headers.get("accept", ""):
        return httpx.Response(406, request=request)
    return _twenty_like_handler(request)


def _sse_streamable_handler(request: httpx.Request) -> httpx.Response:
    """Return valid Streamable HTTP responses as server-sent events."""
    body = json.loads(request.content.decode())
    method = body.get("method")
    if method == "notifications/initialized":
        return httpx.Response(202, request=request)

    if method == "initialize":
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {"protocolVersion": "2025-06-18", "capabilities": {}},
        }
    else:
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "tools": [
                    {
                        "name": "sse_tool",
                        "description": "Returned over SSE",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            },
        }
    content = f"event: message\ndata: {json.dumps(payload)}\n\n"
    return httpx.Response(
        200,
        content=content,
        headers={"content-type": "text/event-stream"},
        request=request,
    )


def _negotiated_version_handler(request: httpx.Request) -> httpx.Response:
    """Require the protocol revision negotiated by initialize on later calls."""
    body = json.loads(request.content.decode())
    method = body.get("method")
    if method == "initialize":
        assert request.headers.get("mcp-protocol-version") is None
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
            },
        }
    elif method == "notifications/initialized":
        assert request.headers.get("mcp-protocol-version") == "2025-06-18"
        return httpx.Response(202, request=request)
    elif method == "tools/list":
        assert request.headers.get("mcp-protocol-version") == "2025-06-18"
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {"tools": []},
        }
    else:
        return httpx.Response(404, request=request)
    return httpx.Response(200, json=payload, request=request)


@pytest.mark.asyncio
async def test_list_tools_json_http_discovers_tools():
    transport = httpx.MockTransport(_twenty_like_handler)
    config = McpServerConfig(
        url="https://crm.example.com/mcp",
        headers={"Authorization": "Bearer good-key"},
    )

    async with httpx.AsyncClient(transport=transport) as _:
        pass

    # Patch client creation by using MockTransport via monkeypatched factory
    import shared.voice_agents.tools.mcp.json_http_client as mod

    original = httpx.AsyncClient

    class _Client(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    mod.httpx.AsyncClient = _Client  # type: ignore[misc]
    try:
        tools = await list_tools_json_http(config)
    finally:
        mod.httpx.AsyncClient = original

    assert len(tools) == 1
    assert tools[0].name == "execute_tool"
    assert tools[0].input_schema == {"type": "object", "properties": {}}


@pytest.mark.asyncio
async def test_list_tools_json_http_supports_standard_streamable_accept_header():
    """Strict Streamable HTTP servers must not fail with HTTP 406."""
    transport = httpx.MockTransport(_strict_streamable_handler)
    config = McpServerConfig(
        url="https://strict.example.com/mcp",
        headers={"Authorization": "Bearer good-key"},
    )

    import shared.voice_agents.tools.mcp.json_http_client as mod

    original = httpx.AsyncClient

    class _Client(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    mod.httpx.AsyncClient = _Client  # type: ignore[misc]
    try:
        tools = await list_tools_json_http(config)
    finally:
        mod.httpx.AsyncClient = original

    assert [tool.name for tool in tools] == ["execute_tool"]


@pytest.mark.asyncio
async def test_list_tools_json_http_parses_streamable_sse_responses():
    """Streamable HTTP discovery also accepts a text/event-stream response."""
    transport = httpx.MockTransport(_sse_streamable_handler)
    config = McpServerConfig(url="https://sse.example.com/mcp")

    import shared.voice_agents.tools.mcp.json_http_client as mod

    original = httpx.AsyncClient

    class _Client(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    mod.httpx.AsyncClient = _Client  # type: ignore[misc]
    try:
        tools = await list_tools_json_http(config)
    finally:
        mod.httpx.AsyncClient = original

    assert [tool.name for tool in tools] == ["sse_tool"]


@pytest.mark.asyncio
async def test_list_tools_json_http_uses_negotiated_protocol_version_on_later_requests():
    """The HTTP header after initialize must match the server negotiation."""
    transport = httpx.MockTransport(_negotiated_version_handler)
    config = McpServerConfig(url="https://negotiated.example.com/mcp")

    import shared.voice_agents.tools.mcp.json_http_client as mod

    original = httpx.AsyncClient

    class _Client(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    mod.httpx.AsyncClient = _Client  # type: ignore[misc]
    try:
        tools = await list_tools_json_http(config)
    finally:
        mod.httpx.AsyncClient = original

    assert tools == []
