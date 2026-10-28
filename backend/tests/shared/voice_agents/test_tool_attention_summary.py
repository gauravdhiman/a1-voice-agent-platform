"""Tests for the privacy-safe, batched agent tool attention summary."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from shared.voice_agents.tool_models import AuthStatus
from shared.voice_agents.tool_service import ToolService

AGENT_WITH_AUTH_ISSUE = UUID("00000000-0000-0000-0000-000000000001")
AGENT_WITH_CONFIG_ISSUE = UUID("00000000-0000-0000-0000-000000000002")
AGENT_WITH_HEALTHY_TOOL = UUID("00000000-0000-0000-0000-000000000003")
AGENT_WITHOUT_TOOLS = UUID("00000000-0000-0000-0000-000000000004")


@pytest.mark.asyncio
async def test_summary_batches_tools_and_returns_only_attention_flags():
    """Summarize auth/config issues in one query without returning tool data."""
    supabase = MagicMock()
    query = MagicMock()
    supabase.table.return_value = query
    query.select.return_value = query
    query.in_.return_value = query
    query.execute.return_value = SimpleNamespace(
        data=[
            {
                "agent_id": str(AGENT_WITH_AUTH_ISSUE),
                "sensitive_config": "encrypted-oauth",
                "config": {},
                "tool": {
                    "name": "google_calendar",
                    "auth_type": "oauth2",
                    "requires_auth": True,
                },
            },
            {
                "agent_id": str(AGENT_WITH_CONFIG_ISSUE),
                "sensitive_config": None,
                "config": {"from_email": ""},
                "tool": {
                    "name": "Resend_email",
                    "auth_type": None,
                    "requires_auth": False,
                },
            },
            {
                "agent_id": str(AGENT_WITH_HEALTHY_TOOL),
                "sensitive_config": None,
                "config": {},
                "tool": {
                    "name": "google_calendar",
                    "auth_type": None,
                    "requires_auth": False,
                },
            },
        ]
    )
    service = ToolService()
    service.supabase_config = SimpleNamespace(client=supabase)

    with (
        patch(
            "shared.voice_agents.tool_service.validate_token_status",
            side_effect=[
                AuthStatus.EXPIRED,
                AuthStatus.NOT_AUTHENTICATED,
                AuthStatus.NOT_AUTHENTICATED,
            ],
        ),
        patch(
            "shared.voice_agents.tool_service.check_tool_configuration",
            side_effect=[[], ["sender email is missing"], []],
        ),
    ):
        summaries, error = await service.get_agent_tool_attention_summaries(
            [
                AGENT_WITH_AUTH_ISSUE,
                AGENT_WITH_CONFIG_ISSUE,
                AGENT_WITH_HEALTHY_TOOL,
                AGENT_WITHOUT_TOOLS,
            ]
        )

    assert error is None
    assert [summary.agent_id for summary in summaries] == [
        AGENT_WITH_AUTH_ISSUE,
        AGENT_WITH_CONFIG_ISSUE,
        AGENT_WITH_HEALTHY_TOOL,
        AGENT_WITHOUT_TOOLS,
    ]
    assert summaries[0].needs_attention is True
    assert summaries[0].has_resend_email_tool is False
    assert summaries[1].needs_attention is True
    assert summaries[1].has_resend_email_tool is True
    assert summaries[2].needs_attention is False
    assert summaries[2].has_resend_email_tool is False
    assert summaries[3].needs_attention is False
    assert summaries[3].has_resend_email_tool is False
    assert not hasattr(summaries[1], "config")
    query.execute.assert_called_once()
    query.in_.assert_called_once_with(
        "agent_id",
        [
            str(AGENT_WITH_AUTH_ISSUE),
            str(AGENT_WITH_CONFIG_ISSUE),
            str(AGENT_WITH_HEALTHY_TOOL),
            str(AGENT_WITHOUT_TOOLS),
        ],
    )


@pytest.mark.asyncio
async def test_summary_returns_empty_list_without_query_for_no_agents():
    """Empty scopes should not issue an unnecessary database request."""
    service = ToolService()
    service.supabase_config = SimpleNamespace(client=MagicMock())

    summaries, error = await service.get_agent_tool_attention_summaries([])

    assert summaries == []
    assert error is None
    service.supabase.table.assert_not_called()
