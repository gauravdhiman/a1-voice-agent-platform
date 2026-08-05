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
