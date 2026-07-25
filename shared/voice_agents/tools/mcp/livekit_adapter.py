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
from typing import Any, Awaitable, Callable

from livekit.agents import ToolError, function_tool

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.models import McpToolDef

#: The callable signature LiveKit expects for a raw-argument tool handler.
McpToolHandler = Callable[[dict[str, Any]], Awaitable[str]]

#: JSON Schema keys Google's Gemini ``Schema`` model accepts (camelCase, as
#: declared by ``google.genai.types.Schema`` field aliases). The Gemini realtime
#: plugin validates every tool schema strictly via
#: ``types.FunctionDeclaration.model_validate(schema)`` with ``extra_forbidden`` —
#: any key not in this set crashes ``_main_task`` during ``_build_connect_config``,
#: the realtime session never connects, and ``generate_reply`` times out (the agent
#: never speaks). Remote MCP servers (e.g. Google's official Calendar MCP at
#: ``https://calendarmcp.googleapis.com/mcp/v1``) routinely emit non-standard keys
#: such as ``x-google-enum-descriptions`` (a vendor extension) and ``deprecated``
#: that Gemini rejects, so :func:`_sanitize_schema_for_gemini` strips every key
#: outside this allowlist before the schema reaches LiveKit.
_GEMINI_SCHEMA_KEYS: frozenset[str] = frozenset(
    {
        "additionalProperties",
        "defs",
        "ref",
        "anyOf",
        "default",
        "description",
        "enum",
        "example",
        "format",
        "items",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "nullable",
        "pattern",
        "properties",
        "propertyOrdering",
        "required",
        "title",
        "type",
    }
)

#: Keys whose values are nested JSON Schemas (so the sanitizer must recurse into
#: them rather than treat them as opaque leaf values).
_PROPERTIES_KEYS = ("properties", "defs")


def _sanitize_schema_for_gemini(schema: Any) -> Any:
    """Strip JSON Schema keys Gemini's ``Schema`` model rejects, recursively.

    Google's Gemini realtime plugin validates tool argument schemas with a
    strict (``extra_forbidden``) pydantic model. Remote MCP servers frequently
    include non-standard keys — vendor extensions (``x-google-enum-descriptions``,
    ``x-goog-*``), ``deprecated``, ``$schema``, ``$comment``, ``examples`` — that
    Gemini does not model, and a single forbidden key aborts the entire realtime
    session (the agent goes silent). This walks the schema and keeps only the
    keys in :data:`_GEMINI_SCHEMA_KEYS`, recursing into ``properties``, ``items``,
    ``anyOf`` and ``defs`` so nested vendor extensions are stripped too.

    The allowlist approach is deliberate: a denylist could miss a future
    non-standard key and still crash the session. Keeping only what Gemini
    accepts guarantees the validator never sees a forbidden key.

    Args:
        schema: A JSON Schema fragment (dict, list, or scalar) from an MCP
            server's ``inputSchema``.

    Returns:
        A schema fragment with only Gemini-accepted keys retained. Standard
        keys (``type``, ``enum``, ``description``, ``items``, ``properties``,
        ``required``, ``format``, ``anyOf``, etc.) survive unchanged. ``oneOf``
        and ``allOf`` are NOT in Gemini's allowlist and are dropped — see the
        TODO below.

    Notes:
        - ``oneOf`` / ``allOf``: Gemini's ``Schema`` models only ``anyOf`` (a
          choice between schemas). ``oneOf``/``allOf`` are dropped outright. If
          a future MCP tool relies on ``oneOf``/``allOf`` for correctness, map
          ``oneOf``→``anyOf`` (closest Gemini equivalent) here rather than
          dropping it. No known Google Calendar tool uses them today.
        - ``$ref`` / ``$defs`` (standard JSON Schema references) are NOT in
          Gemini's allowlist (it uses ``ref``/``defs`` without the ``$`` prefix).
          They are dropped here. Remote MCP servers in practice inline their
          schemas (no ``$ref`` seen across Google Calendar's 9 tools); if a
          ``$ref``-using server appears, resolve references before sanitizing
          rather than mapping the prefix (Gemini's ``ref`` semantics differ).
        - ``additionalProperties`` may be a boolean or a schema; we recurse only
          when it is a dict.
    """
    if isinstance(schema, dict):
        sanitized: dict[str, Any] = {}
        for key, value in schema.items():
            if key not in _GEMINI_SCHEMA_KEYS:
                # TODO: Future Enhancement — translate ``oneOf``→``anyOf`` and
                # ``allOf``→``anyOf`` (flattened) if a tool relies on them, instead
                # of dropping. No known tool needs this today; dropped to keep the
                # Gemini validator from crashing the realtime session.
                continue
            if key in _PROPERTIES_KEYS and isinstance(value, dict):
                # dict[str, Schema] — recurse into each named sub-schema.
                sanitized[key] = {
                    name: _sanitize_schema_for_gemini(sub)
                    for name, sub in value.items()
                    if isinstance(sub, (dict, list))
                }
            elif key == "items":
                # A single nested schema (or a list of schemas in draft-older
                # JSON Schema; recurse element-wise if it's a list).
                if isinstance(value, list):
                    sanitized[key] = [
                        _sanitize_schema_for_gemini(sub) for sub in value if isinstance(sub, (dict, list))
                    ]
                elif isinstance(value, dict):
                    sanitized[key] = _sanitize_schema_for_gemini(value)
                else:
                    sanitized[key] = value
            elif key == "anyOf" and isinstance(value, list):
                sanitized[key] = [
                    _sanitize_schema_for_gemini(sub) for sub in value if isinstance(sub, (dict, list))
                ]
            elif key == "additionalProperties":
                sanitized[key] = (
                    _sanitize_schema_for_gemini(value) if isinstance(value, dict) else value
                )
            else:
                # Leaf key (type, enum, description, format, required, min/max*,
                # nullable, pattern, default, example, title, propertyOrdering,
                # ref) — keep verbatim.
                sanitized[key] = value
        return sanitized
    if isinstance(schema, list):
        return [_sanitize_schema_for_gemini(item) for item in schema if isinstance(item, (dict, list))]
    return schema


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


def _make_mcp_handler(client: McpClient, tool_name: str) -> McpToolHandler:
    """Build the async handler that forwards a LiveKit call to the MCP server.

    Args:
        client: The :class:`McpClient` used to reach the MCP server. The caller
            owns the client's lifecycle (typically via ``async with``); the
            handler does not open or close it.
        tool_name: The MCP tool name to invoke on each call.

    Returns:
        An async callable ``handler(raw_arguments: dict) -> str`` suitable for
        LiveKit's ``RawFunctionTool``. On success it returns the tool's text
        content. On a server-reported error it raises :class:`ToolError` carrying
        the error text (or a generic message when the server returned none).
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
            ToolError: If the MCP server reports the call as an error.
        """
        result = await client.call_tool(tool_name, raw_arguments)
        if result.is_error:
            raise ToolError(result.text or f"MCP tool '{tool_name}' returned an error")
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

    Args:
        client: The :class:`McpClient` the handler will use to reach the server.
            The caller owns its lifecycle.
        tool_def: The MCP tool definition to synthesize from.

    Returns:
        A LiveKit ``RawFunctionTool`` carrying the tool's name and JSON Schema,
        whose handler forwards calls to the MCP server via ``client``.
    """
    raw_schema = _build_raw_schema(tool_def)
    handler = _make_mcp_handler(client, tool_def.name)
    return function_tool(raw_schema=raw_schema)(handler)