"""Synthesize LiveKit ``function_tool`` wrappers from MCP tool definitions.

This is the Phase 1 glue between the MCP client
(:mod:`shared.voice_agents.tools.mcp.client`) and the LiveKit agent
runtime. For each tool an MCP server exposes, we build a LiveKit
``RawFunctionTool`` whose handler forwards the model's arguments to the
remote MCP server and surfaces the result (or a ``ToolError``) back to
the model.

Design notes:
    - We use LiveKit's ``raw_schema`` entry point
      (``function_tool(raw_schema=...)(handler)``) rather than decorating a
      real function with typed parameters. The MCP server already hands us a
      JSON Schema for the arguments, so we pass it through verbatim instead of
      re-deriving it from Python type hints. This keeps schemas faithful to what
      the server declared (including ``format``, ``enum``, nested objects, etc.).
    - The handler receives the model's arguments as a single dict injected into
      the ``raw_arguments`` parameter (LiveKit's ``RawFunctionTool`` contract).
      We forward that dict to ``McpClient.call_tool`` unchanged.
    - Server-reported errors (unknown tool, bad arguments, server-side failure)
      come back as ``McpToolResult.is_error=True``. We convert those into LiveKit
      ``ToolError`` so the model sees a structured failure it can recover from,
      rather than a silent empty string.
    - The legacy ``BaseTool`` / ``LiveKitToolRegistry`` path is untouched. This
      module is consumed only by the worker's per-agent assembly loop when a
      ``platform_tools`` row is marked as MCP-sourced (Phase 2). See
      ``docs/03_implementation/mcp_integration_rfc.md`` §1.1 (coexistence).
"""
import json
from typing import Any, Awaitable, Callable, Optional

from livekit.agents import ToolError, function_tool

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.models import McpToolDef
from shared.voice_agents.tools.mcp.schema_sanitize import (
    _sanitize_schema_for_gemini,
)

#: The callable signature LiveKit expects for a raw-argument tool handler.
McpToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def _build_raw_schema(tool_def: McpToolDef) -> dict[str, Any]:
    """Build the ``raw_schema`` dict LiveKit's ``function_tool`` consumes.

    The ``parameters`` (the MCP server's ``inputSchema``) are first run through
    :func:`_sanitize_schema_for_gemini` so that non-standard JSON Schema keys the
    Gemini realtime plugin rejects (e.g. ``x-google-enum-descriptions``,
    ``deprecated``) are stripped. Without this, LiveKit's Gemini plugin crashes
    in ``_build_connect_config`` via ``types.FunctionDeclaration.model_validate``
    with ``extra_forbidden``, the realtime session never connects, and the agent
    never responds.

    Args:
        tool_def: The MCP tool definition to convert.

    Returns:
        A dict with ``name``, ``description``, and ``parameters`` keys, shaped
        exactly as LiveKit's ``raw_schema`` expects. ``description`` defaults to
        an empty string (never ``None``) because the model-facing tool prompt
        must be a string. ``parameters`` defaults to a minimal
        ``{"type": "object", "properties": {}}`` schema when the server declares
        no arguments, so the model still receives a valid JSON Schema object.
    """
    parameters = tool_def.input_schema
    if not parameters:
        # Avoid passing an empty/{} schema with no ``type``; the model expects a
        # JSON Schema object describing the arguments (even if there are none).
        parameters = {"type": "object", "properties": {}}
    else:
        # Strip non-Gemini keys so the strict FunctionDeclaration validator does
        # not crash the realtime session on vendor extensions / ``deprecated``.
        parameters = _sanitize_schema_for_gemini(parameters)
    return {
        "name": tool_def.name,
        "description": tool_def.description or "",
        "parameters": parameters,
    }


def _accepted_params(input_schema: Any) -> list[str]:
    """Return the tool's accepted parameter names from its ``inputSchema``.

    These are threaded into the handler so a server-reported argument error can
    name what the tool DOES accept, letting the model self-correct on retry
    (drop an unsupported arg, or switch to a different tool) instead of giving
    up and surfacing a cryptic validation string to the user.

    Real-world motivation: DeepWiki's ``read_wiki_contents`` accepts only
    ``repoName``; the model called it with an extra ``question`` and the server
    rejected the call with a bare ``unexpected_keyword_argument``. Surfacing
    ``accepted arguments: repoName`` lets the model drop ``question`` (or reach
    for ``ask_question``) on the next turn rather than reporting failure.

    Args:
        input_schema: The MCP server's ``inputSchema`` for a tool (a JSON Schema
            dict, or ``None``/empty when the server declares no arguments).

    Returns:
        The ordered list of property names declared under ``properties``.
        Empty when the schema is missing or has no ``properties`` object.
    """
    if not isinstance(input_schema, dict):
        return []
    properties = input_schema.get("properties")
    if not isinstance(properties, dict):
        return []
    return list(properties.keys())


def _make_mcp_handler(
    client: McpClient,
    tool_name: str,
    accepted_params: Optional[list[str]] = None,
) -> McpToolHandler:
    """Build the async handler that forwards a LiveKit call to the MCP server.

    Args:
        client: The :class:`McpClient` used to reach the MCP server. The caller
            owns the client's lifecycle (typically via ``async with``); the
            handler does not open or close it.
        tool_name: The MCP tool name to invoke on each call.
        accepted_params: The tool's accepted parameter names (from
            :func:`_accepted_params`). When provided, a server-reported error
            is augmented with ``accepted arguments: <names>`` so the model can
            self-correct on retry. ``None`` (default) preserves the legacy
            behaviour — surface the raw server error unchanged — so call sites
            that do not pass params are unaffected.

    Returns:
        An async callable ``handler(raw_arguments: dict) -> str`` suitable for
        LiveKit's ``RawFunctionTool``. On success it returns the tool's text
        content. On a server-reported error it raises :class:`ToolError` carrying
        the error text (or a generic message when the server returned none),
        optionally suffixed with the accepted-arguments hint.
        Non-text or empty content falls back to a JSON dump so the model always
        receives something it can reason over.
    """

    async def handler(raw_arguments: dict[str, Any]) -> str:
        """Forward the model's arguments to the named MCP tool.

        Args:
            raw_arguments: The argument dict LiveKit injects from the model's
                function call. Forwarded verbatim to the MCP server.

        Returns:
            The tool's text content as a string.

        Raises:
            ToolError: If the MCP server reports the call as an error. When
                ``accepted_params`` is provided the message is suffixed with the
                tool's accepted argument names so the model can self-correct.
        """
        result = await client.call_tool(tool_name, raw_arguments)
        if result.is_error:
            base = result.text or f"MCP tool '{tool_name}' returned an error"
            if accepted_params is not None:
                # Surface the tool's accepted arguments so the model can recover
                # (drop an unsupported arg, or pick a different tool) instead of
                # reporting a cryptic server-side validation string to the user.
                params_str = ", ".join(accepted_params) or "none"
                raise ToolError(f"{base} — accepted arguments: {params_str}")
            raise ToolError(base)
        text = result.text
        if text:
            return text
        # No text content (e.g. image/resource-only result). Fall back to JSON so
        # the model still gets a structured payload rather than an empty string.
        return json.dumps(result.content)

    return handler


def mcp_tool_to_livekit_tool(client: McpClient, tool_def: McpToolDef):
    """Register an MCP tool as a LiveKit ``RawFunctionTool``.

    Combines :func:`_build_raw_schema` and :func:`_make_mcp_handler` into a single
    LiveKit tool the worker can hand to ``agent.update_tools(...)`` alongside
    legacy ``BaseTool``-derived tools (the two are compatible; coexistence per
    RFC §1.1).

    The tool's accepted parameter names are extracted from its ``inputSchema``
    and threaded into the handler so a server-reported argument error names what
    the tool accepts — letting the model self-correct on retry.

    Args:
        client: The :class:`McpClient` the handler will use to reach the server.
            The caller owns its lifecycle.
        tool_def: The MCP tool definition to synthesize from.

    Returns:
        A LiveKit ``RawFunctionTool`` carrying the tool's name and JSON Schema,
        whose handler forwards calls to the MCP server via ``client``.
    """
    raw_schema = _build_raw_schema(tool_def)
    accepted_params = _accepted_params(tool_def.input_schema)
    handler = _make_mcp_handler(client, tool_def.name, accepted_params=accepted_params)
    return function_tool(raw_schema=raw_schema)(handler)