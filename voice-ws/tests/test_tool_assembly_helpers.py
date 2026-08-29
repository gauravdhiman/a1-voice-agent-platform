"""Focused tests for Pipecat tool schema and invocation helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from src.tools.assembly import (
    _is_function_unselected,
    build_function_schema,
    create_legacy_tool_handler,
)

from shared.voice_agents.tools.base.platform_tool_registry import PlatformToolRegistry
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations.google_calendar_appointment import (
    GoogleCalendarAppointmentTool,
)
from shared.voice_agents.tools.implementations.google_sheets import GoogleSheetsTool


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


async def _pep604_tool(
    context: Any,
    duration_minutes: int | None = None,
) -> dict[str, Any]:
    """Expose a PEP 604 optional integer for schema conversion tests."""
    return {
        "duration_minutes": duration_minutes,
        "timezone": context.organization_timezone,
    }


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

    def test_native_tool_docstring_becomes_model_facing_schema_description(
        self,
    ) -> None:
        """Tool capability guidance belongs to the native function schema."""
        schema = build_function_schema(
            GoogleCalendarAppointmentTool.find_available_slots
        )

        assert "free starts" in schema.description.lower()
        assert "time window" in schema.description.lower()
        assert "duration_minutes" in schema.properties
        assert "window_start" in schema.properties

    def test_build_function_schema_includes_array_items_for_gemini(self) -> None:
        """Gemini Live requires array parameters to declare item schemas."""
        schema = build_function_schema(GoogleSheetsTool.append_row)

        values_schema = schema.properties["values"]
        assert values_schema["type"] == "array"
        assert "items" in values_schema
        assert values_schema["items"]["type"] == "string"

    def test_build_function_schema_nested_arrays_and_object_items(self) -> None:
        """2D arrays and list-of-object params must also declare items."""
        update_schema = build_function_schema(GoogleSheetsTool.update_cell)
        values_schema = update_schema.properties["values"]
        assert values_schema["type"] == "array"
        assert values_schema["items"]["type"] == "array"
        assert values_schema["items"]["items"]["type"] == "string"

        batch_schema = build_function_schema(GoogleSheetsTool.batch_update_values)
        updates_schema = batch_schema.properties["updates"]
        assert updates_schema["type"] == "array"
        assert updates_schema["items"]["type"] == "object"

    def test_build_function_schema_preserves_pep604_optional_primitive_type(
        self,
    ) -> None:
        """PEP 604 unions must not silently become string parameters."""
        schema = build_function_schema(_pep604_tool)

        assert schema.properties["duration_minutes"]["type"] == "integer"

    def test_legacy_handler_injects_runtime_context(self) -> None:
        """Tool context comes from the trusted session, never model arguments."""
        handler = create_legacy_tool_handler(
            _pep604_tool,
            runtime_context=ToolContext(
                organization_timezone="America/Phoenix",
                session_id="session-123",
            ),
        )
        params = _FakeFunctionCallParams(
            {"duration_minutes": 60, "context": "untrusted"}
        )

        asyncio.run(handler(params))

        assert (
            params.result == '{"duration_minutes": 60, "timezone": "America/Phoenix"}'
        )

    def test_legacy_handler_filters_context_from_model_arguments(self) -> None:
        """A model-provided context key cannot override runtime ToolContext."""
        handler = create_legacy_tool_handler(_example_tool)
        params = _FakeFunctionCallParams(
            {"subject": "status", "count": 2, "context": "untrusted"}
        )

        asyncio.run(handler(params))

        assert params.result == '{"subject": "status", "count": 2}'

    def test_function_toggle_accepts_runtime_and_display_names(self) -> None:
        """UI-persisted display names must disable runtime functions too."""
        registry = PlatformToolRegistry()

        assert _is_function_unselected(
            registry,
            _example_tool,
            {"_example_tool"},
        )
        assert _is_function_unselected(
            registry,
            _example_tool,
            {"Example Tool"},
        )
        assert not _is_function_unselected(registry, _example_tool, {"Other Tool"})
