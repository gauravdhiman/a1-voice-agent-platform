"""Focused tests for Pipecat tool schema and invocation helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from src.tools.assembly import (
    build_function_schema,
    create_legacy_tool_handler,
)


class _FakeFunctionCallParams:
    """Capture a Pipecat tool handler result without requiring a live LLM."""

    def __init__(self, arguments: dict[str, Any]) -> None:
        self.arguments = arguments
        self.result: str | None = None

    async def result_callback(self, result: str) -> None:
        """Store the result supplied by the handler."""
        self.result = result


async def _example_tool(
    context: Any,
    subject: str,
    count: int = 1,
) -> dict[str, Any]:
    """Create a test result from model supplied arguments."""
    assert context is not None
    return {"subject": subject, "count": count}


class TestToolAssemblyHelpers:
    """Validate schema conversion and safe legacy tool invocation."""

    def test_build_function_schema_omits_tool_context(self) -> None:
        """The model schema must not expose internal ToolContext."""
        schema = build_function_schema(_example_tool)

        assert schema.name == "_example_tool"
        assert set(schema.properties) == {"subject", "count"}
        assert schema.properties["subject"]["type"] == "string"
        assert schema.properties["count"]["type"] == "integer"
        assert schema.required == ["subject"]

    def test_legacy_handler_filters_context_from_model_arguments(self) -> None:
        """A model-provided context key cannot override runtime ToolContext."""
        handler = create_legacy_tool_handler(_example_tool)
        params = _FakeFunctionCallParams(
            {"subject": "status", "count": 2, "context": "untrusted"}
        )

        asyncio.run(handler(params))

        assert params.result == '{"subject": "status", "count": 2}'
