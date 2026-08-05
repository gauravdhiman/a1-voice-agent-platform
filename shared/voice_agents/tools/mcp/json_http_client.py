"""JSON-only Streamable HTTP MCP client.

Some MCP servers (notably Twenty CRM's built-in ``/mcp``) behave reliably with
plain ``application/json`` POST exchanges but trip strict SSE clients when
``Accept`` includes ``text/event-stream``. Cursor and curl typically succeed
because they either negotiate JSON or handle SSE differently than the Python
``mcp`` SDK's streamable HTTP transport.

This module implements the minimal JSON-RPC handshake:

    1. ``initialize`` (request/response)
    2. ``notifications/initialized`` (notification, no response body)
    3. ``tools/list`` or ``tools/call`` (request/response)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import httpx

from shared.voice_agents.tools.mcp.models import McpServerConfig, McpToolDef, McpToolResult

logger = logging.getLogger(__name__)

_CLIENT_INFO = {"name": "247ai-platform", "version": "1.0"}
_PROTOCOL_VERSION = "2024-11-05"


class McpJsonRpcError(RuntimeError):
    """Raised when the remote MCP server returns a JSON-RPC error object."""

    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


def _unwrap_input_schema(schema: Any) -> dict[str, Any]:
    """Unwrap Twenty/AI-SDK ``{ jsonSchema: {...} }`` wrappers if present."""
    if isinstance(schema, dict) and "jsonSchema" in schema:
        inner = schema.get("jsonSchema")
        if isinstance(inner, dict):
            return inner
    if isinstance(schema, dict):
        return schema
    return {}


def _tool_from_dict(raw: dict[str, Any]) -> McpToolDef:
    schema = _unwrap_input_schema(raw.get("inputSchema") or raw.get("input_schema") or {})
    return McpToolDef(
        name=str(raw["name"]),
        description=raw.get("description"),
        input_schema=schema,
    )


def _rpc_error_message(body: dict[str, Any]) -> str:
    err = body.get("error") or {}
    message = err.get("message") or "MCP JSON-RPC error"
    code = err.get("code")
    if code is not None:
        return f"{message} (code {code})"
    return str(message)


def _request_headers(config: McpServerConfig) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        # JSON only — avoids Twenty's SSE path (matches curl/Cursor).
        "Accept": "application/json",
        **(config.headers or {}),
    }


def _result_from_body(body: dict[str, Any]) -> McpToolResult:
    if body.get("error"):
        message = _rpc_error_message(body)
        return McpToolResult(
            content=[{"type": "text", "text": message}],
            is_error=True,
        )
    result = body.get("result") or {}
    content = result.get("content") or []
    if not isinstance(content, list):
        content = [{"type": "text", "text": str(content)}]
    is_error = bool(result.get("isError") or result.get("is_error"))
    return McpToolResult(content=content, is_error=is_error)


@asynccontextmanager
async def _json_http_session(
    config: McpServerConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, str]]]:
    """Open httpx client and complete MCP initialize handshake."""
    request_headers = _request_headers(config)
    timeout = httpx.Timeout(config.timeout, read=config.timeout)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        init_response = await client.post(
            config.url,
            headers=request_headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": _PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": _CLIENT_INFO,
                },
            },
        )
        init_response.raise_for_status()
        init_body = init_response.json()
        if init_body.get("error"):
            raise McpJsonRpcError(_rpc_error_message(init_body))

        await client.post(
            config.url,
            headers=request_headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
        )
        yield client, request_headers


async def list_tools_json_http(config: McpServerConfig) -> list[McpToolDef]:
    """Discover tools via JSON POSTs (no MCP SDK / no SSE)."""
    async with _json_http_session(config) as (client, request_headers):
        tools_response = await client.post(
            config.url,
            headers=request_headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
        )
        tools_response.raise_for_status()
        tools_body = tools_response.json()
        if tools_body.get("error"):
            raise McpJsonRpcError(_rpc_error_message(tools_body))

        result = tools_body.get("result") or {}
        raw_tools = result.get("tools") or []
        tools = [_tool_from_dict(t) for t in raw_tools if isinstance(t, dict) and t.get("name")]
        logger.info(
            "JSON HTTP MCP discover url=%s tools=%d",
            config.url,
            len(tools),
        )
        return tools


async def call_tool_json_http(
    config: McpServerConfig,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> McpToolResult:
    """Invoke a tool via JSON POSTs (no MCP SDK / no SSE)."""
    async with _json_http_session(config) as (client, request_headers):
        call_response = await client.post(
            config.url,
            headers=request_headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            },
        )
        call_response.raise_for_status()
        call_body = call_response.json()
        result = _result_from_body(call_body)
        logger.info(
            "JSON HTTP MCP call url=%s tool=%s is_error=%s",
            config.url,
            name,
            result.is_error,
        )
        return result
