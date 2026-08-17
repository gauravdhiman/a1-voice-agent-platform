"""Helpers for surfacing MCP transport failures to API callers."""

from __future__ import annotations

import httpx


def format_mcp_client_error(exc: BaseException) -> str:
    """Convert MCP SDK / httpx transport errors into a readable message.

    The official ``mcp`` Streamable HTTP client wraps failures in
    ``ExceptionGroup`` ("unhandled errors in a TaskGroup"). Unwrap those so
    callers (and the platform-admin UI) see the underlying cause — usually a
    401 from the remote server when the API key is wrong or missing.
    """
    if isinstance(exc, BaseExceptionGroup):
        messages = [format_mcp_client_error(sub) for sub in exc.exceptions]
        # Preserve order, drop duplicates from nested groups.
        return "; ".join(dict.fromkeys(messages))

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            return (
                "MCP server returned 401 Unauthorized — the platform did not "
                "authenticate to the remote MCP server. If the same URL/key work "
                "in Cursor, set Authentication to 'No auth' and put "
                '{"Authorization": "Bearer <api-key>"} in Public headers only '
                "(or use Static API key mode with the Test API key field). "
                "Use a Twenty workspace API key from Settings → Developers → "
                "API & Webhooks, not a browser login token."
            )
        if status == 403:
            return (
                "MCP server returned 403 Forbidden. The token was accepted but "
                "lacks permission for MCP (check API key role/scopes)."
            )
        reason = exc.response.reason_phrase or "error"
        return f"MCP server returned HTTP {status} {reason}"

    # MCP servers control JSON-RPC error text. Never echo it to an admin
    # response: a misbehaving provider could reflect an Authorization header,
    # token, or other request material in that string.
    return "MCP request failed"
