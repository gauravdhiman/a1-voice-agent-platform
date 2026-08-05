"""Integration tests for McpClient against Twenty-like Streamable HTTP servers."""

from __future__ import annotations

import json

import httpx
import pytest

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.models import McpServerConfig


def _twenty_like_handler(request: httpx.Request) -> httpx.Response:
    """Minimal handler mimicking Twenty CRM's built-in /mcp endpoint."""
    auth = request.headers.get("authorization")
    if auth != "Bearer good-key":
        return httpx.Response(
            401,
            json={"statusCode": 401, "messages": ["Unauthorized"]},
            request=request,
        )

    if request.method in {"GET", "DELETE"}:
        return httpx.Response(405, request=request)

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
                "instructions": "test",
            },
        }
    elif method == "tools/list":
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "tools": [
                    {
                        "name": "get_tool_catalog",
                        "description": "List tools",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            },
        }
    elif method == "tools/call":
        payload = {
            "jsonrpc": "2.0",
            "id": body["id"],
            "result": {
                "content": [{"type": "text", "text": "ok"}],
                "isError": False,
            },
        }
    else:
        return httpx.Response(404, request=request)

    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        sse = f"event: message\ndata: {json.dumps(payload)}\n\n"
        return httpx.Response(
            200,
            content=sse,
            headers={"content-type": "text/event-stream"},
            request=request,
        )
    return httpx.Response(200, json=payload, request=request)


@pytest.fixture
def patch_mcp_http_client(monkeypatch):
    """Route McpClient HTTP through an in-memory Twenty-like mock."""

    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            transport=httpx.MockTransport(_twenty_like_handler),
            headers=headers,
            timeout=timeout or httpx.Timeout(30.0),
        )

    monkeypatch.setattr(
        "shared.voice_agents.tools.mcp.client.create_mcp_http_client",
        factory,
    )


@pytest.mark.asyncio
async def test_mcp_client_lists_tools_with_authorization_header(patch_mcp_http_client):
    client = McpClient(
        McpServerConfig(
            url="https://crm.example.com/mcp",
            headers={"Authorization": "Bearer good-key"},
        )
    )
    try:
        tools = await client.list_tools()
    finally:
        await client.close()

    assert [t.name for t in tools] == ["get_tool_catalog"]


@pytest.mark.asyncio
async def test_mcp_client_missing_authorization_returns_401(patch_mcp_http_client):
    client = McpClient(
        McpServerConfig(url="https://crm.example.com/mcp", headers={})
    )
    try:
        with pytest.raises(BaseExceptionGroup) as exc_info:
            await client.list_tools()
    finally:
        await client.close()

    assert any(
        isinstance(sub, httpx.HTTPStatusError) and sub.response.status_code == 401
        for sub in exc_info.value.exceptions
    )


@pytest.mark.asyncio
async def test_mcp_client_call_tool_uses_json_http(patch_mcp_http_client):
    client = McpClient(
        McpServerConfig(
            url="https://crm.example.com/mcp",
            headers={"Authorization": "Bearer good-key"},
        )
    )
    try:
        result = await client.call_tool("get_tool_catalog", {})
    finally:
        await client.close()

    assert result.is_error is False
    assert result.text == "ok"
