"""Tests for the MCP client adapter (Phase 1 of the MCP integration RFC).

These tests prove the new tool-integration path end-to-end against a real,
in-process MCP reference server (a FastMCP ``calculator``) running over
Streamable HTTP on an ephemeral localhost port. The legacy ``BaseTool`` tool
mechanism is **not** exercised or modified here — this is the parallel path
described in ``docs/03_implementation/mcp_integration_rfc.md`` §1.1.

The reference server here is the same shape that task #53 ("reference MCP
server + e2e proof") will containerize; keeping it in-process makes the unit
tests deterministic (localhost, no third-party OAuth, no external network).

Red-green: this file is written FIRST. It fails because
``shared.voice_agents.tools.mcp.client`` does not exist yet.
"""
import pytest

from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.models import McpToolDef, McpToolResult

# The reference MCP server (``mcp_server_url`` / ``mcp_mcp_server_config`` fixtures)
# lives in ``conftest.py`` so it can be shared with
# ``tests/test_mcp_livekit_adapter.py``.


class TestMcpClientListTools:
    """list_tools() discovers every tool the server exposes, with schemas."""

    async def test_list_tools_returns_all_tools(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            tools = await client.list_tools()

        names = {t.name for t in tools}
        assert names == {"add", "multiply"}

    async def test_list_tools_returns_typed_tool_defs(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            tools = await client.list_tools()

        assert all(isinstance(t, McpToolDef) for t in tools)

    async def test_list_tools_includes_input_schema_with_params(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            tools_list = await client.list_tools()
            tools = {t.name: t for t in tools_list}

        add_schema = tools["add"].input_schema
        # JSON-Schema properties must surface the two integer params.
        props = add_schema.get("properties", {})
        assert set(props.keys()) == {"a", "b"}
        # FastMCP derives types from the signature; both are integers.
        assert props["a"]["type"] == "integer"
        assert props["b"]["type"] == "integer"
        assert "a" in add_schema.get("required", [])


class TestMcpClientCallTool:
    """call_tool() invokes a server tool and returns its result."""

    async def test_call_tool_add(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            result = await client.call_tool("add", {"a": 2, "b": 3})

        assert isinstance(result, McpToolResult)
        assert result.is_error is False
        assert result.text.strip() == "5"

    async def test_call_tool_multiply(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            result = await client.call_tool("multiply", {"a": 4, "b": 5})

        assert result.is_error is False
        assert result.text.strip() == "20"

    async def test_call_tool_with_no_arguments(self, mcp_server_config):
        # A tool that takes no args would still succeed; here we just confirm
        # the arguments dict is forwarded as-is (smoke check of the path).
        async with McpClient(mcp_server_config) as client:
            result = await client.call_tool("add", {"a": 0, "b": 0})
        assert result.is_error is False
        assert result.text.strip() == "0"


class TestMcpClientErrors:
    """Error handling for unknown tools and bad arguments."""

    async def test_call_unknown_tool_reports_error(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            result = await client.call_tool("does_not_exist", {})

        # The MCP server returns an error result (is_error=True) for an
        # unknown tool name, rather than crashing the session.
        assert result.is_error is True

    async def test_call_tool_bad_argument_reports_error(self, mcp_server_config):
        async with McpClient(mcp_server_config) as client:
            result = await client.call_tool("add", {"a": "not-a-number", "b": 1})

        assert result.is_error is True


class TestMcpClientLifecycle:
    """Connection lifecycle: close is safe and idempotent."""

    async def test_close_is_idempotent(self, mcp_server_config):
        client = McpClient(mcp_server_config)
        await client.close()
        # Closing again must not raise.
        await client.close()

    async def test_list_tools_after_close_reconnects_or_raises_cleanly(self, mcp_server_config):
        # After explicit close the client should not silently produce stale
        # results; it must either re-open or raise. Either is acceptable as
        # long as it does not return a wrong/empty tool list silently.
        client = McpClient(mcp_server_config)
        await client.close()
        with pytest.raises(Exception):
            await client.list_tools()


class TestMcpClientHelpers:
    """Unit tests for the static normalization helpers (no server needed).

    These cover the defensive fallback branches that the live-server tests
    do not exercise: the ``inputSchema`` fallback and the non-pydantic content
    block shapes.
    """

    def test_to_tool_def_uses_input_schema_fallback_when_missing(self):
        """When inputSchema is absent, fall back to input_schema, then {}."""
        from types import SimpleNamespace

        # Has neither attribute -> empty schema.
        tool_no_schema = SimpleNamespace(name="t1", description="d1")
        def1 = McpClient._to_tool_def(tool_no_schema)
        assert def1.name == "t1"
        assert def1.input_schema == {}

        # inputSchema is None, input_schema present -> use input_schema.
        tool_fallback = SimpleNamespace(
            name="t2", description="d2", inputSchema=None, input_schema={"x": 1}
        )
        def2 = McpClient._to_tool_def(tool_fallback)
        assert def2.input_schema == {"x": 1}

    def test_to_tool_def_prefers_camel_case_input_schema(self):
        """inputSchema (camelCase) takes precedence over input_schema."""
        from types import SimpleNamespace

        tool = SimpleNamespace(
            name="t",
            description="d",
            inputSchema={"a": 1},
            input_schema={"b": 2},
        )
        def_ = McpClient._to_tool_def(tool)
        assert def_.input_schema == {"a": 1}

    def test_block_to_dict_passes_through_dict_blocks(self):
        """A block that is already a dict is returned unchanged."""
        block = {"type": "text", "text": "hi"}
        assert McpClient._block_to_dict(block) == {"type": "text", "text": "hi"}

    def test_block_to_dict_stringifies_unknown_shapes(self):
        """A block with no model_dump and not a dict is stringified, never lost."""
        block = 42
        out = McpClient._block_to_dict(block)
        assert out["type"] == "unknown"
        assert out["text"] == "42"

    def test_block_to_dict_uses_model_dump_when_present(self):
        """A pydantic-like block is dumped via model_dump()."""
        from types import SimpleNamespace

        block = SimpleNamespace(model_dump=lambda: {"type": "text", "text": "x"})
        assert McpClient._block_to_dict(block) == {"type": "text", "text": "x"}


class TestMcpToolResultText:
    """The McpToolResult.text convenience property joins text content blocks."""

    def test_text_joins_only_text_blocks(self):
        result = McpToolResult(
            content=[
                {"type": "text", "text": "5"},
                {"type": "image", "data": "base64..."},
                {"type": "text", "text": "!"},
            ]
        )
        assert result.text == "5!"

    def test_text_empty_when_no_text_blocks(self):
        result = McpToolResult(content=[{"type": "image", "data": "x"}])
        assert result.text == ""