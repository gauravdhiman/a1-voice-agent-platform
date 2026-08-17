"""Tests for MCP client error formatting."""

from __future__ import annotations

import httpx
import pytest

from shared.voice_agents.tools.mcp.errors import format_mcp_client_error


def _http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://crm.example.com/mcp")
    response = httpx.Response(status, request=request, text="Unauthorized")
    return httpx.HTTPStatusError("client error", request=request, response=response)


def test_unwraps_exception_group_with_http_401():
    inner = _http_status_error(401)
    group = ExceptionGroup("task group failed", [inner])

    message = format_mcp_client_error(group)

    assert "401 Unauthorized" in message
    assert "Twenty workspace API key" in message


def test_formats_http_403():
    message = format_mcp_client_error(_http_status_error(403))
    assert "403 Forbidden" in message


def test_formats_generic_http_status():
    message = format_mcp_client_error(_http_status_error(502))
    assert "HTTP 502" in message


def test_redacts_arbitrary_remote_exception_details():
    """Remote error text must not echo a bearer or provider response body."""
    message = format_mcp_client_error(
        RuntimeError("refresh_token=do-not-return-to-the-browser")
    )

    assert message == "MCP request failed"
    assert "do-not-return" not in message
