"""Focused tests for Pipecat tool schema and invocation helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from src.tools.assembly import (
    _is_function_unselected,
    _resolve_runtime_sensitive_config,
    apply_model_function_guidance,
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

    def test_build_function_schema_exposes_header_keyed_row_values(self) -> None:
        """The generic contract passes a validated header-to-cell object."""
        schema = build_function_schema(GoogleSheetsTool.create_row)

        values_schema = schema.properties["values"]
        assert values_schema == {
            "type": "object",
            "additionalProperties": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "boolean"},
                ]
            },
        }

    def test_build_function_schema_update_requires_exact_match(self) -> None:
        """Updates expose a match key and a partial header-keyed patch."""
        schema = build_function_schema(GoogleSheetsTool.update_row)

        assert schema.required == ["match_column", "match_value", "values"]
        assert schema.properties["values"] == {
            "type": "object",
            "additionalProperties": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "boolean"},
                ]
            },
        }

    def test_configured_agent_fields_are_added_to_model_guidance(self) -> None:
        """The runtime schema teaches the model the attachment's field names."""
        tool = GoogleSheetsTool(
            config={
                "agent_columns": "Customer Name, Items, Quantity",
                "required_columns": "Customer Name, Items",
                "idempotency_column": "Order ID",
            }
        )
        schema = build_function_schema(GoogleSheetsTool.create_row)

        schema = apply_model_function_guidance(schema, tool)

        assert "`Customer Name`" in schema.description
        assert "`Items`" in schema.description
        assert "`Quantity`" in schema.description
        assert "Required for create_row" in schema.description
        assert "`Order ID` (idempotency key)" in schema.description

    def test_configured_row_schema_uses_exact_headers_and_required_fields(self) -> None:
        """Configured row values reject renamed keys before provider I/O."""
        tool = GoogleSheetsTool(
            config={
                "agent_columns": "Caller Name, Phone, Order details, Notes",
                "required_columns": "Caller Name, Phone, Order details",
                "idempotency_column": "Submission ID",
            }
        )

        schema = apply_model_function_guidance(
            build_function_schema(GoogleSheetsTool.create_row),
            tool,
        )

        values_schema = schema.properties["values"]
        assert values_schema["additionalProperties"] is False
        assert list(values_schema["properties"]) == [
            "Caller Name",
            "Phone",
            "Order details",
            "Notes",
        ]
        assert values_schema["required"] == [
            "Caller Name",
            "Phone",
            "Order details",
        ]
        assert "Submission ID" not in values_schema["properties"]

    def test_update_schema_allows_business_patch_but_not_managed_values(self) -> None:
        """Updates expose exact match headers and business-only patches."""
        tool = GoogleSheetsTool(
            config={
                "agent_columns": "Caller Name, Phone",
                "idempotency_column": "Submission ID",
                "timestamp_column": "Captured at",
            }
        )

        schema = apply_model_function_guidance(
            build_function_schema(GoogleSheetsTool.update_row),
            tool,
        )

        assert schema.properties["match_column"]["enum"] == [
            "Caller Name",
            "Phone",
            "Submission ID",
            "Captured at",
        ]
        assert schema.properties["values"]["additionalProperties"] is False
        assert list(schema.properties["values"]["properties"]) == [
            "Caller Name",
            "Phone",
        ]

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

    def test_resend_runtime_secret_comes_from_organization(self, monkeypatch) -> None:
        """Resend ignores stale per-agent secrets and resolves the org key."""
        monkeypatch.setattr(
            "src.tools.assembly.resolve_org_provider_credential",
            lambda _organization, provider: (
                "org-resend-key" if provider == "resend" else None
            ),
        )

        resolved = _resolve_runtime_sensitive_config(
            "Resend_email",
            {"api_key": "stale-agent-key", "other": "value"},
            object(),
        )

        assert resolved == {"other": "value", "api_key": "org-resend-key"}
