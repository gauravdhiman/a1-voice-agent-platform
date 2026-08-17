"""Async MCP client over Streamable HTTP.

This is the Phase 1 client described in ``docs/03_implementation/mcp_integration_rfc.md``.
It wraps the official ``mcp`` Python SDK's Streamable HTTP transport and
:class:`~mcp.ClientSession` behind a small, stable API so the rest of the
codebase (and the tests) do not depend on SDK internals.

Design notes:
    - A fresh :class:`~mcp.ClientSession` is opened **per call**. This is
      simpler to reason about than a long-lived session and matches the
      stateless direction of the 2026-07-28 MCP transport spec. The cost is a
      connection + ``initialize`` per call; acceptable for Phase 1, flagged as
      a perf TODO for later phases.
    - ``close()`` flips a flag that makes subsequent calls raise. Because
      sessions are per-call, ``close()`` does not need to tear down a
      persistent connection — it just refuses further use. This makes
      ``close()`` idempotent and safe.
    - Server-reported errors (unknown tool, bad arguments) are returned with
      ``is_error=True`` rather than raised; transport-level failures (network,
      non-2xx) propagate as exceptions.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import MCP_DEFAULT_SSE_READ_TIMEOUT, create_mcp_http_client

from shared.voice_agents.tools.mcp.models import (
    McpServerConfig,
    McpToolDef,
    McpToolResult,
)
from shared.voice_agents.tools.mcp.security import validate_mcp_server_url

logger = logging.getLogger(__name__)


def _create_secure_mcp_http_client(
    *, headers: Optional[dict[str, str]], timeout: httpx.Timeout
) -> httpx.AsyncClient:
    """Create an MCP SDK HTTP client with redirect following disabled.

    The MCP SDK currently defaults its internal ``httpx.AsyncClient`` to
    ``follow_redirects=True``. Disabling redirects is required because the
    client may carry bearer or other connection credentials, and forwarding
    those headers to a redirected host would expand the credential trust
    boundary without an explicit user action.

    Args:
        headers: Optional request headers, including connection credentials.
        timeout: HTTP timeout configuration for the MCP transport.

    Returns:
        A configured ``httpx.AsyncClient`` returned by the MCP SDK.

    Notes:
        The SDK constructs the client internally, so the redirect policy is
        set immediately after construction and before the client can issue a
        request. The JSON HTTP fallback applies the same policy directly.
    """
    http_client = create_mcp_http_client(headers=headers or None, timeout=timeout)
    http_client.follow_redirects = False
    return http_client


class McpClient:
    """Async client for a single remote MCP server over Streamable HTTP.

    The client is the new-path equivalent of a ``BaseTool`` subclass: it
    discovers a server's tools (``list_tools``) and invokes them
    (``call_tool``). It does not touch the legacy registry; the worker's
    per-agent assembly loop will dispatch to it based on the ``tool_source`` of
    the ``platform_tools`` row (Phase 2).

    Lifecycle:
        - Use as an async context manager for scoped access::

              async with McpClient(config) as client:
                  tools = await client.list_tools()
                  result = await client.call_tool("add", {"a": 1, "b": 2})

        - Or construct directly and call :meth:`close` when done. ``close`` is
          idempotent; any call after ``close`` raises ``RuntimeError``.

    Attributes:
        config: The :class:`McpServerConfig` this client was built from.
    """

    def __init__(self, config: McpServerConfig) -> None:
        """Create a client for the given server configuration.

        Args:
            config: Connection definition (URL, headers, timeout). The client
                does not connect on construction; the first call opens a
                session.
        """
        self.config = config
        self._closed = False

    async def list_tools(self) -> list[McpToolDef]:
        """Discover every tool the server exposes, with input schemas.

        Opens a session, calls ``tools/list``, and maps the SDK tool objects to
        :class:`McpToolDef` instances.

        Returns:
            List of tool definitions. Empty if the server exposes none.

        Raises:
            RuntimeError: If the client has been closed.
            Exception: On transport failure (network, non-2xx, protocol error).
        """
        from shared.voice_agents.tools.mcp.json_http_client import list_tools_json_http

        try:
            return await list_tools_json_http(self.config)
        except Exception as json_err:
            logger.debug(
                "JSON HTTP list_tools failed for MCP server; falling back to SDK (%s)",
                type(json_err).__name__,
            )
        async with self._session() as session:
            result = await session.list_tools()
        return [self._to_tool_def(tool) for tool in result.tools]

    async def call_tool(
        self, name: str, arguments: Optional[dict] = None
    ) -> McpToolResult:
        """Invoke a tool by name with the given arguments.

        Server-reported errors (unknown tool name, argument validation
        failure) come back as :class:`McpToolResult` with ``is_error=True``
        rather than raising — the agent loop decides how to surface them.

        Args:
            name: Tool name, as returned by :meth:`list_tools`.
            arguments: Argument dict matching the tool's ``input_schema``.
                ``None`` is treated as an empty dict.

        Returns:
            The tool result, with raw content blocks and an ``is_error`` flag.

        Raises:
            RuntimeError: If the client has been closed.
            Exception: On transport failure (network, non-2xx, protocol error).
        """
        from shared.voice_agents.tools.mcp.json_http_client import call_tool_json_http

        try:
            return await call_tool_json_http(self.config, name, arguments)
        except Exception as json_err:
            logger.debug(
                "JSON HTTP call_tool failed for MCP tool %s; falling back to SDK (%s)",
                name,
                type(json_err).__name__,
            )
        async with self._session() as session:
            result = await session.call_tool(name, arguments or {})
        content = [self._block_to_dict(block) for block in result.content]
        # The SDK exposes the error flag as ``isError`` (camelCase, per MCP spec).
        return McpToolResult(content=content, is_error=bool(result.isError))

    async def close(self) -> None:
        """Mark the client as closed.

        Idempotent: calling twice is a no-op. Subsequent :meth:`list_tools` /
        :meth:`call_tool` calls raise ``RuntimeError``. Because sessions are
        opened per call, there is no persistent connection to tear down here.
        """
        self._closed = True

    # --- async context manager protocol -------------------------------------

    async def __aenter__(self) -> "McpClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # --- internals ----------------------------------------------------------

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        """Open a one-shot Streamable HTTP session to the configured server.

        Yields an initialized :class:`~mcp.ClientSession`. The transport and
        session are torn down on exit, so callers do not need to manage them.
        """
        if self._closed:
            raise RuntimeError("McpClient is closed")
        valid_url, reason = validate_mcp_server_url(self.config.url)
        if not valid_url:
            raise ValueError(f"Cannot contact MCP server: {reason}")
        # Use the current MCP SDK transport API: auth/custom headers live on the
        # httpx client, not on StreamableHTTPTransport (the deprecated
        # ``streamablehttp_client(url, headers=...)`` wrapper is easy to misread
        # and some SDK versions ignore transport-level header params).
        # ``terminate_on_close=False`` — stateless servers such as Twenty CRM
        # expose POST /mcp only and return 405 on DELETE; session teardown is a
        # no-op for them (Cursor/other clients behave the same way).
        headers = dict(self.config.headers or {})
        timeout = httpx.Timeout(self.config.timeout, read=MCP_DEFAULT_SSE_READ_TIMEOUT)
        async with _create_secure_mcp_http_client(
            headers=headers or None,
            timeout=timeout,
        ) as http_client:
            async with streamable_http_client(
                self.config.url,
                http_client=http_client,
                terminate_on_close=False,
            ) as (read, write, _get_session_id):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    @staticmethod
    def _to_tool_def(tool: Any) -> McpToolDef:
        """Map an SDK ``Tool`` object to an :class:`McpToolDef`.

        The SDK exposes the input schema as ``inputSchema`` (camelCase, per the
        MCP spec). ``getattr`` fallback covers any future rename.
        """
        schema = getattr(tool, "inputSchema", None)
        if schema is None:
            schema = getattr(tool, "input_schema", None) or {}
        return McpToolDef(
            name=tool.name,
            description=getattr(tool, "description", None),
            input_schema=schema,
        )

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        """Normalize an SDK content block to a plain dict.

        SDK content blocks (``TextContent``, ``ImageContent``, ...) are
        pydantic models with ``model_dump()``. Anything already dict-like is
        passed through; unknown shapes are stringified so we never lose data.
        """
        if hasattr(block, "model_dump"):
            return block.model_dump()
        if isinstance(block, dict):
            return block
        return {"type": "unknown", "text": str(block)}
