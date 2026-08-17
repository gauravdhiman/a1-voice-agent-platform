"""Minimal Streamable HTTP MCP client.

Some MCP servers (notably Twenty CRM's built-in ``/mcp``) behave reliably with
plain ``application/json`` POST exchanges but trip strict SSE clients when
``Accept`` includes ``text/event-stream``. Cursor and curl typically succeed
because they either negotiate JSON or handle SSE differently than the Python
``mcp`` SDK's streamable HTTP transport.

This module implements the minimal JSON-RPC handshake while accepting either
JSON or server-sent-events responses:

    1. ``initialize`` (request/response)
    2. ``notifications/initialized`` (notification, no response body)
    3. ``tools/list`` or ``tools/call`` (request/response or SSE)
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from shared.voice_agents.tools.mcp.models import (
    McpServerConfig,
    McpToolDef,
    McpToolResult,
)
from shared.voice_agents.tools.mcp.security import validate_mcp_server_url

logger = logging.getLogger(__name__)

_CLIENT_INFO = {"name": "247ai-platform", "version": "1.0"}
_PROTOCOL_VERSION = "2025-06-18"
_STREAMABLE_ACCEPT = "application/json, text/event-stream"


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
    schema = _unwrap_input_schema(
        raw.get("inputSchema") or raw.get("input_schema") or {}
    )
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
    headers = {
        "Content-Type": "application/json",
        # Streamable HTTP requires clients to advertise both response formats.
        # Servers such as DeepWiki and Context7 reject JSON-only negotiation
        # with HTTP 406, while other servers legitimately choose SSE.
        "Accept": _STREAMABLE_ACCEPT,
        "MCP-Protocol-Version": _PROTOCOL_VERSION,
        **(config.headers or {}),
    }
    # A pasted host config may contain its own Accept value. Keep it, but make
    # the required Streamable HTTP formats available as well.
    custom_accept = next(
        (
            value
            for key, value in (config.headers or {}).items()
            if key.lower() == "accept"
        ),
        None,
    )
    if custom_accept:
        accept_values = [
            part.strip() for part in custom_accept.split(",") if part.strip()
        ]
        for required in ("application/json", "text/event-stream"):
            if not any(value.lower() == required for value in accept_values):
                accept_values.append(required)
        headers["Accept"] = ", ".join(dict.fromkeys(accept_values))
    return headers


def _response_json(response: httpx.Response) -> dict[str, Any]:
    """Decode a JSON or server-sent-events Streamable HTTP response.

    Streamable HTTP allows a server to return a single JSON-RPC response as
    ``application/json`` or to wrap that response in a ``text/event-stream``.
    The platform only needs the first JSON-RPC message for the stateless
    initialize/list/call requests, so this parser intentionally ignores SSE
    comments and unrelated event fields while accepting multiline ``data:``
    payloads.
    """
    content_type = response.headers.get("content-type", "").lower()
    if "text/event-stream" not in content_type:
        body = response.json()
        if not isinstance(body, dict):
            raise McpJsonRpcError("MCP response was not a JSON object")
        return body

    for event in response.text.replace("\r\n", "\n").split("\n\n"):
        data_lines = [
            line[5:].lstrip() for line in event.split("\n") if line.startswith("data:")
        ]
        if not data_lines:
            continue
        try:
            body = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            continue
        if isinstance(body, dict):
            return body

    raise McpJsonRpcError("MCP SSE response did not contain a JSON-RPC message")


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
    valid_url, reason = validate_mcp_server_url(config.url)
    if not valid_url:
        raise ValueError(f"Cannot contact MCP server: {reason}")

    request_headers = _request_headers(config)
    # The MCP-Protocol-Version header is negotiated during initialize and is
    # required on subsequent requests. Do not pin the initialize request to a
    # possibly stale version supplied by a host config or an older client.
    request_headers.pop("MCP-Protocol-Version", None)
    timeout = httpx.Timeout(config.timeout, read=config.timeout)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
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
        init_body = _response_json(init_response)
        if init_body.get("error"):
            raise McpJsonRpcError(_rpc_error_message(init_body))

        negotiated_version = (
            init_body.get("result", {}).get("protocolVersion")
            if isinstance(init_body.get("result"), dict)
            else None
        )
        request_headers["MCP-Protocol-Version"] = str(
            negotiated_version or _PROTOCOL_VERSION
        )

        session_id = init_response.headers.get("mcp-session-id")
        if session_id:
            request_headers["Mcp-Session-Id"] = session_id

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
    """Discover tools via Streamable HTTP JSON POSTs or SSE responses."""
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
        tools_body = _response_json(tools_response)
        if tools_body.get("error"):
            raise McpJsonRpcError(_rpc_error_message(tools_body))

        result = tools_body.get("result") or {}
        raw_tools = result.get("tools") or []
        tools = [
            _tool_from_dict(t)
            for t in raw_tools
            if isinstance(t, dict) and t.get("name")
        ]
        logger.info(
            "JSON HTTP MCP discover completed tools=%d",
            len(tools),
        )
        return tools


async def call_tool_json_http(
    config: McpServerConfig,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> McpToolResult:
    """Invoke a tool via Streamable HTTP JSON POSTs or SSE responses."""
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
        call_body = _response_json(call_response)
        result = _result_from_body(call_body)
        logger.info(
            "JSON HTTP MCP call tool=%s is_error=%s",
            name,
            result.is_error,
        )
        return result
