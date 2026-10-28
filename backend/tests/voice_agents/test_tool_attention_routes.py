"""Authorization tests for the batched agent tool attention endpoint."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.tool_models import AgentToolAttentionSummary

AGENT_ID = UUID("00000000-0000-0000-0000-000000000001")
ORG_ID = UUID("00000000-0000-0000-0000-000000000002")
OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000003")
USER_ID = UUID("00000000-0000-0000-0000-000000000004")


def _profile(*, platform_admin: bool = False, readable_org: UUID | None = None):
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: role == "platform_admin"
        and platform_admin
    )
    profile.has_permission = Mock(
        side_effect=lambda permission, org_id=None: (
            permission == "agent:read" and org_id == str(readable_org)
        )
    )
    return profile


def _agent_query_mock(agent_ids: list[UUID]):
    supabase = MagicMock()
    query = MagicMock()
    supabase.table.return_value.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value = SimpleNamespace(
        data=[{"id": str(agent_id)} for agent_id in agent_ids]
    )
    return supabase, query


@pytest.mark.asyncio
async def test_org_reader_gets_attention_summary_for_only_the_selected_org():
    from src.voice_agents.tool_routes import get_agent_tool_attention

    supabase, query = _agent_query_mock([AGENT_ID])
    expected = [
        AgentToolAttentionSummary(
            agent_id=AGENT_ID,
            needs_attention=True,
            has_resend_email_tool=False,
        )
    ]

    with (
        patch("src.voice_agents.tool_routes.voice_agent_service") as agents,
        patch("src.voice_agents.tool_routes.tool_service") as tools,
    ):
        agents.supabase = supabase
        tools.get_agent_tool_attention_summaries = AsyncMock(
            return_value=(expected, None)
        )

        result = await get_agent_tool_attention(
            organization_id=ORG_ID,
            user_data=(USER_ID, _profile(readable_org=ORG_ID)),
        )

    assert result == expected
    query.eq.assert_called_once_with("organization_id", str(ORG_ID))
    tools.get_agent_tool_attention_summaries.assert_awaited_once_with([AGENT_ID])


@pytest.mark.asyncio
async def test_org_reader_cannot_request_another_organizations_summary():
    from src.voice_agents.tool_routes import get_agent_tool_attention

    supabase, _ = _agent_query_mock([AGENT_ID])
    with (
        patch("src.voice_agents.tool_routes.voice_agent_service") as agents,
        patch("src.voice_agents.tool_routes.tool_service") as tools,
    ):
        agents.supabase = supabase
        tools.get_agent_tool_attention_summaries = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_tool_attention(
                organization_id=OTHER_ORG_ID,
                user_data=(USER_ID, _profile(readable_org=ORG_ID)),
            )

    assert exc_info.value.status_code == 403
    supabase.table.assert_not_called()
    tools.get_agent_tool_attention_summaries.assert_not_awaited()


@pytest.mark.asyncio
async def test_only_platform_admin_can_omit_organization_scope():
    from src.voice_agents.tool_routes import get_agent_tool_attention

    with patch("src.voice_agents.tool_routes.voice_agent_service") as agents:
        with pytest.raises(HTTPException) as exc_info:
            await get_agent_tool_attention(
                organization_id=None,
                user_data=(USER_ID, _profile()),
            )

    assert exc_info.value.status_code == 403
    agents.supabase.table.assert_not_called()


@pytest.mark.asyncio
async def test_platform_admin_can_get_cross_organization_summary():
    from src.voice_agents.tool_routes import get_agent_tool_attention

    supabase, query = _agent_query_mock([AGENT_ID])
    expected = [
        AgentToolAttentionSummary(
            agent_id=AGENT_ID,
            needs_attention=False,
            has_resend_email_tool=False,
        )
    ]

    with (
        patch("src.voice_agents.tool_routes.voice_agent_service") as agents,
        patch("src.voice_agents.tool_routes.tool_service") as tools,
    ):
        agents.supabase = supabase
        tools.get_agent_tool_attention_summaries = AsyncMock(
            return_value=(expected, None)
        )

        result = await get_agent_tool_attention(
            organization_id=None,
            user_data=(USER_ID, _profile(platform_admin=True)),
        )

    assert result == expected
    query.eq.assert_not_called()
    tools.get_agent_tool_attention_summaries.assert_awaited_once_with([AGENT_ID])
