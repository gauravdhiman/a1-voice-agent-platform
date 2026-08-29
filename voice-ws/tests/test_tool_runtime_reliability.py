"""Tests for reliable tool assembly and non-fabricating voice prompts."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.tools.assembly import create_legacy_tool_handler

from shared.voice_agents.default_voice_rules import DEFAULT_VOICE_SYSTEM_PROMPT


class _FakeFunctionCallParams:
    """Capture a Pipecat tool handler result without a live LLM."""

    def __init__(self, arguments: dict[str, Any]) -> None:
        self.arguments = arguments
        self.result: str | None = None

    async def result_callback(self, result: str) -> None:
        """Store the result supplied by the handler."""
        self.result = result


async def _boom_tool(context: Any, subject: str) -> dict[str, Any]:
    """Raise so the Pipecat adapter must return an error payload."""
    raise RuntimeError(f"calendar offline for {subject}")


class TestToolRuntimeReliability:
    """Ensure failed tools cannot silently become invented booking success."""

    def test_default_prompt_forbids_fabricated_tool_outcomes(self) -> None:
        """Voice rules must require successful tool results before confirming."""
        prompt = DEFAULT_VOICE_SYSTEM_PROMPT.lower()
        assert "never invent" in prompt or "do not invent" in prompt
        assert "successful tool" in prompt or "tool result" in prompt
        assert "follow each tool" in prompt
        assert "google calendar" not in prompt
        assert "gmail" not in prompt
        assert "booking" not in prompt
        assert "availability" not in prompt
        assert "before saying" in prompt or "before claiming" in prompt
        assert "pending tool" in prompt or "tool call has not" in prompt

    def test_legacy_handler_returns_error_json_on_exception(self) -> None:
        """Tool exceptions must become model-visible errors, not silent drops."""
        handler = create_legacy_tool_handler(_boom_tool)
        params = _FakeFunctionCallParams({"subject": "monday"})

        asyncio.run(handler(params))

        assert params.result is not None
        assert "error" in params.result
        assert "calendar offline" in params.result

    def test_resend_uses_org_credential_and_discards_legacy_agent_key(self) -> None:
        """The native Resend tool receives only the org-owned runtime secret."""
        from src.tools.assembly import _resolve_runtime_sensitive_config

        organization = MagicMock()
        with patch(
            "src.tools.assembly.resolve_org_provider_credential",
            return_value="re_org_key",
        ) as resolve_credential:
            sensitive = _resolve_runtime_sensitive_config(
                "Resend_email",
                {"api_key": "re_wrong_agent_key", "other": "value"},
                organization,
            )

        assert sensitive == {"api_key": "re_org_key", "other": "value"}
        resolve_credential.assert_called_once_with(organization, "resend")

    @pytest.mark.asyncio
    async def test_assemble_records_mcp_failures_as_unavailable(self) -> None:
        """MCP discovery failures must be tracked for observability."""
        from src.tools.assembly import assemble_agent_tools

        agent_tool = MagicMock()
        agent_tool.is_enabled = True
        agent_tool.unselected_functions = None
        agent_tool.tool = MagicMock()
        agent_tool.tool.name = "Google_calendar_mcp"
        agent_tool.tool.tool_source = MagicMock()
        # Compare against ToolSource.MCP in assembly via equality on value.
        from shared.voice_agents.tool_models import ToolSource

        agent_tool.tool.tool_source = ToolSource.MCP

        with (
            patch(
                "src.tools.assembly.tool_service.get_agent_tools_with_sensitive_config",
                new=AsyncMock(return_value=([agent_tool], None)),
            ),
            patch(
                "src.tools.assembly.skill_service.get_agent_skill_summaries",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.tools.assembly.build_mcp_pipecat_tools",
                new=AsyncMock(side_effect=ConnectionError("connection refused")),
            ),
            patch(
                "src.tools.assembly.PlatformToolRegistry.register_tools_from_package",
                return_value=None,
            ),
        ):
            assembled = await assemble_agent_tools("agent-id", "org-id")

        assert assembled.schemas == []
        assert assembled.enabled_tool_names == []
        assert any(
            "Google_calendar_mcp" in item for item in assembled.unavailable_tools
        )
