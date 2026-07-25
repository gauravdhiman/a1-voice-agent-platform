"""Tests for the LiveKit ``function_tool`` synthesis adapter (Phase 1).

These prove that an MCP tool definition can be turned into a LiveKit
``RawFunctionTool`` whose handler calls the MCP server and surfaces the
result (or a ``ToolError``) to the voice model. The legacy ``BaseTool`` /
``LiveKitToolRegistry`` mechanism is **not** exercised or modified here —
this is the parallel path described in
``docs/03_implementation/mcp_integration_rfc.md`` §1.1.

The reference MCP server (``mcp_server_url`` / ``mcp_server_config``
fixtures) lives in ``conftest.py`` and is shared with
``tests/test_mcp_client.py``.

Red-green: this file is written FIRST. It fails at collection because
``shared.voice_agents.tools.mcp.livekit_adapter`` does not exist yet.
"""
import pytest
from livekit.agents import ToolError

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.livekit_adapter import (
    _build_raw_schema,
    _make_mcp_handler,
    mcp_tool_to_livekit_tool,
)
from shared.voice_agents.tools.mcp.models import McpToolDef


# A representative ``add`` tool definition, mirroring what the reference
# FastMCP calculator server reports via ``tools/list``.
ADD_SCHEMA = {
    "type": "object",
    "properties": {
        "a": {"type": "integer"},
        "b": {"type": "integer"},
    },
    "required": ["a", "b"],
}


def _add_tool_def(**overrides) -> McpToolDef:
    """Build an ``add`` McpToolDef, allowing per-test field overrides."""
    base = {"name": "add", "description": "Add two integers", "input_schema": ADD_SCHEMA}
    base.update(overrides)
    return McpToolDef(**base)


class TestBuildRawSchema:
    """``_build_raw_schema`` produces the dict LiveKit's ``function_tool`` expects."""

    def test_carries_name_description_and_parameters(self):
        schema = _build_raw_schema(_add_tool_def())
        assert schema["name"] == "add"
        assert schema["description"] == "Add two integers"
        assert schema["parameters"] == ADD_SCHEMA

    def test_description_defaults_to_empty_string(self):
        schema = _build_raw_schema(McpToolDef(name="t", description=None, input_schema={}))
        assert schema["description"] == ""

    def test_parameters_defaults_to_empty_object_schema_when_missing(self):
        # An empty input_schema must not produce ``parameters: {}`` with no
        # ``type``; LiveKit/the model expect a JSON Schema object.
        schema = _build_raw_schema(McpToolDef(name="t", description="d", input_schema={}))
        params = schema["parameters"]
        assert params["type"] == "object"
        assert params["properties"] == {}


class TestSchemaSanitization:
    """MCP tool schemas carry non-standard JSON Schema keys that Gemini's strict
    ``FunctionDeclaration`` rejects with ``extra_forbidden``.

    Real-world failure (Google's OFFICIAL remote Calendar MCP server,
    ``https://calendarmcp.googleapis.com/mcp/v1``): the ``list_events`` tool's
    ``inputSchema`` contains ``eventType.items.x-google-enum-descriptions`` (a
    Google vendor extension) and ``eventTypeFilter.deprecated`` (a standard JSON
    Schema key Gemini does not model). LiveKit's Gemini plugin validates every
    tool schema via ``types.FunctionDeclaration.model_validate(schema)`` during
    ``_build_connect_config``; a single forbidden key crashes ``_main_task``, the
    realtime session never connects, and ``generate_reply`` times out — the agent
    never speaks.

    ``_build_raw_schema`` must therefore strip every key Gemini's ``Schema``
    model does not accept before handing the schema to LiveKit's
    ``function_tool(raw_schema=...)``. The allowlist (Gemini ``Schema`` field
    aliases): ``type, enum, description, items, properties, required, anyOf,
    format, nullable, default, example, title, pattern, minimum, maximum,
    minLength, maxLength, minItems, maxItems, minProperties, maxProperties,
    propertyOrdering, additionalProperties, defs, ref``.
    """

    # Mirrors the real list_events inputSchema shape that crashed the session.
    _RAW_SCHEMA = {
        "type": "object",
        "properties": {
            "eventType": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["DEFAULT", "OUT_OF_OFFICE"],
                    "x-google-enum-descriptions": [
                        "Treated as DEFAULT.",
                        "Out of office event cannot be created.",
                    ],
                    "deprecated": True,
                },
            },
            "eventTypeFilter": {
                "type": "string",
                "deprecated": True,
                "description": "Filter by event type.",
            },
        },
        "required": ["eventType"],
        "x-google-vendor-ext": {"foo": "bar"},
    }

    def test_strips_vendor_extensions_and_deprecated(self):
        built = _build_raw_schema(
            McpToolDef(name="list_events", description="List events", input_schema=self._RAW_SCHEMA)
        )
        params = built["parameters"]

        # Forbidden keys stripped at every depth.
        items = params["properties"]["eventType"]["items"]
        assert "x-google-enum-descriptions" not in items
        assert "deprecated" not in items
        assert "deprecated" not in params["properties"]["eventTypeFilter"]
        assert "x-google-vendor-ext" not in params

        # Standard keys survive.
        assert items["enum"] == ["DEFAULT", "OUT_OF_OFFICE"]
        assert items["type"] == "string"
        assert params["properties"]["eventTypeFilter"]["description"] == "Filter by event type."
        assert params["required"] == ["eventType"]

    def test_sanitized_schema_passes_gemini_function_declaration_validation(self):
        """The real proof: Gemini's strict pydantic validator must accept it.

        Before the fix this raises ``pydantic_core.ValidationError`` (the exact
        crash from the worker logs), aborting the realtime session.
        """
        from google.genai import types

        built = _build_raw_schema(
            McpToolDef(name="list_events", description="List events", input_schema=self._RAW_SCHEMA)
        )
        # Must not raise.
        fd = types.FunctionDeclaration.model_validate(built)
        assert fd.name == "list_events"

    def test_preserves_pure_standard_schema_unchanged(self):
        # A schema with only Gemini-allowed keys is passed through unchanged
        # (sanitization is a no-op for already-clean schemas).
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "integer", "minimum": 0, "maximum": 10},
                "b": {"type": "string", "enum": ["x", "y"], "nullable": True},
            },
            "required": ["a"],
        }
        built = _build_raw_schema(McpToolDef(name="t", description="d", input_schema=schema))
        assert built["parameters"] == schema

    def test_strips_nested_anyof_vendor_extensions(self):
        # Vendor extensions nested inside anyOf members are stripped too.
        schema = {
            "type": "object",
            "properties": {
                "when": {
                    "anyOf": [
                        {"type": "string", "format": "date-time"},
                        {"type": "object", "x-google-extra": True, "properties": {}},
                    ]
                }
            },
        }
        built = _build_raw_schema(McpToolDef(name="t", description="d", input_schema=schema))
        members = built["parameters"]["properties"]["when"]["anyOf"]
        assert "x-google-extra" not in members[1]
        assert members[0]["format"] == "date-time"


class TestMcpHandler:
    """The synthesized handler calls the MCP server and returns/raises correctly."""

    async def test_handler_returns_tool_text_on_success(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            handler = _make_mcp_handler(client, "add")
            result = await handler({"a": 2, "b": 3})

        assert result.strip() == "5"

    async def test_handler_raises_tool_error_on_unknown_tool(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            handler = _make_mcp_handler(client, "does_not_exist")
            with pytest.raises(ToolError):
                await handler({})

    async def test_handler_raises_tool_error_on_bad_arguments(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            handler = _make_mcp_handler(client, "add")
            with pytest.raises(ToolError):
                await handler({"a": "not-a-number", "b": 1})


class TestMcpToolToLiveKitTool:
    """``mcp_tool_to_livekit_tool`` registers a LiveKit RawFunctionTool."""

    async def test_returns_raw_function_tool_with_name_and_schema(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            tool = mcp_tool_to_livekit_tool(client, _add_tool_def())

        # The object is a LiveKit RawFunctionTool carrying the name + schema.
        assert type(tool).__name__ == "RawFunctionTool"
        assert tool.info.name == "add"
        assert tool.info.raw_schema["name"] == "add"
        assert tool.info.raw_schema["description"] == "Add two integers"
        # The parameters we passed through must be preserved verbatim.
        assert tool.info.raw_schema["parameters"] == ADD_SCHEMA

    async def test_registered_tool_invokes_mcp_server(self, mcp_server_config):
        """The synthesized handler wired into the LiveKit tool actually calls out."""
        async with McpClient(mcp_server_config) as client:
            tool = mcp_tool_to_livekit_tool(client, _add_tool_def())
            # LiveKit stores the wrapped callable under ``__wrapped__`` (the
            # standard functools convention). Invoking it proves the handler
            # built by ``_make_mcp_handler`` is the one wired into the tool and
            # that it reaches the MCP server end-to-end.
            handler = tool.__wrapped__
            result = await handler({"a": 7, "b": 8})

        assert result.strip() == "15"