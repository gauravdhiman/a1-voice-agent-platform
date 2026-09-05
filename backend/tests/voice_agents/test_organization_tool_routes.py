"""Tests for organization-level platform-tool visibility controls."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.models import VoiceAgent
from shared.voice_agents.tool_models import (
    AgentToolCreate,
    AgentToolResponse,
    AuthStatus,
    ConnectionStatus,
    PlatformTool,
)

ORG_ID = UUID("00000000-0000-0000-0000-000000000020")
AGENT_ID = UUID("00000000-0000-0000-0000-000000000010")
TOOL_ID = UUID("00000000-0000-0000-0000-000000000050")
USER_ID = UUID("00000000-0000-0000-0000-000000000040")


def _profile(*, is_org_admin: bool = False, is_platform_admin: bool = False):
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            is_platform_admin and role == "platform_admin"
        )
    )
    profile.has_permission = Mock(
        side_effect=lambda permission, org_id=None: (
            org_id == str(ORG_ID)
            and (
                permission == "agent:read"
                or (
                    is_org_admin
                    and permission in ("agent:update", "organization:update")
                )
            )
        )
    )
    return profile


def _agent() -> VoiceAgent:
    return VoiceAgent(
        id=AGENT_ID,
        organization_id=ORG_ID,
        name="Test Agent",
        phone_number="+15555550100",
        persona="Test",
        tone="Professional",
        mission="Help",
        custom_instructions="Be helpful",
        is_active=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


def _tool(*, is_visible: bool = True, is_published: bool = True) -> PlatformTool:
    return PlatformTool(
        id=TOOL_ID,
        name="Calendar",
        description="Calendar access",
        is_active=True,
        is_visible=is_visible,
        is_published=is_published,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


def _agent_tool() -> AgentToolResponse:
    return AgentToolResponse(
        id=UUID("00000000-0000-0000-0000-000000000060"),
        agent_id=AGENT_ID,
        tool_id=TOOL_ID,
        config=None,
        is_enabled=True,
        auth_status=AuthStatus.NOT_AUTHENTICATED,
        connection_status=ConnectionStatus.CONNECTED_NO_AUTH,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


@pytest.mark.asyncio
async def test_organization_tools_list_applies_org_catalog_permission():
    from src.voice_agents.tool_routes import get_organization_tools

    profile = _profile()
    with patch("src.voice_agents.tool_routes.tool_service") as mock_service:
        mock_service.get_organization_tools = AsyncMock(return_value=([_tool()], None))

        result = await get_organization_tools(
            org_id=ORG_ID,
            user_data=(USER_ID, profile),
        )

    assert result[0].id == TOOL_ID
    mock_service.get_organization_tools.assert_awaited_once_with(
        ORG_ID, only_active=True, include_hidden=False
    )


@pytest.mark.asyncio
async def test_organization_admin_can_hide_published_tool():
    from src.voice_agents.tool_routes import (
        OrganizationToolVisibilityUpdate,
        set_organization_tool_visibility,
    )

    profile = _profile(is_org_admin=True)
    hidden_tool = _tool(is_visible=False)
    with patch("src.voice_agents.tool_routes.tool_service") as mock_service:
        mock_service.set_organization_tool_visibility = AsyncMock(
            return_value=(hidden_tool, None)
        )

        result = await set_organization_tool_visibility(
            org_id=ORG_ID,
            tool_id=TOOL_ID,
            visibility_data=OrganizationToolVisibilityUpdate(is_visible=False),
            user_data=(USER_ID, profile),
        )

    assert result.is_visible is False
    mock_service.set_organization_tool_visibility.assert_awaited_once_with(
        ORG_ID, TOOL_ID, False
    )


@pytest.mark.asyncio
async def test_include_hidden_catalog_requires_organization_update_permission():
    from src.voice_agents.tool_routes import get_organization_tools

    with patch("src.voice_agents.tool_routes.tool_service") as mock_service:
        mock_service.get_organization_tools = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_organization_tools(
                org_id=ORG_ID,
                include_hidden=True,
                user_data=(USER_ID, _profile()),
            )

    assert exc_info.value.status_code == 403
    mock_service.get_organization_tools.assert_not_awaited()


@pytest.mark.asyncio
async def test_regular_member_cannot_change_organization_tool_visibility():
    from src.voice_agents.tool_routes import (
        OrganizationToolVisibilityUpdate,
        set_organization_tool_visibility,
    )

    with patch("src.voice_agents.tool_routes.tool_service") as mock_service:
        mock_service.set_organization_tool_visibility = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await set_organization_tool_visibility(
                org_id=ORG_ID,
                tool_id=TOOL_ID,
                visibility_data=OrganizationToolVisibilityUpdate(is_visible=False),
                user_data=(USER_ID, _profile()),
            )

    assert exc_info.value.status_code == 403
    mock_service.set_organization_tool_visibility.assert_not_awaited()


@pytest.mark.asyncio
async def test_hidden_tool_cannot_be_attached_to_new_agent():
    from src.voice_agents.tool_routes import configure_agent_tool

    profile = _profile(is_org_admin=True)
    tool_data = AgentToolCreate(agent_id=AGENT_ID, tool_id=TOOL_ID)
    with (
        patch("src.voice_agents.tool_routes.voice_agent_service") as mock_agents,
        patch("src.voice_agents.tool_routes.tool_service") as mock_service,
    ):
        mock_agents.get_agent_by_id = AsyncMock(return_value=(_agent(), None))
        mock_service.get_platform_tool_by_id = AsyncMock(
            return_value=(_tool(is_visible=False), None)
        )
        mock_service.get_agent_tools = AsyncMock(return_value=([], None))
        mock_service.configure_agent_tool = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await configure_agent_tool(
                agent_tool_data=tool_data,
                user_data=(USER_ID, profile),
            )

    assert exc_info.value.status_code == 403
    assert "hidden from your organization" in str(exc_info.value.detail)
    mock_service.configure_agent_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_hidden_tool_remains_editable_when_already_attached():
    from src.voice_agents.tool_routes import configure_agent_tool

    profile = _profile(is_org_admin=True)
    tool_data = AgentToolCreate(agent_id=AGENT_ID, tool_id=TOOL_ID)
    configured = _agent_tool()
    with (
        patch("src.voice_agents.tool_routes.voice_agent_service") as mock_agents,
        patch("src.voice_agents.tool_routes.tool_service") as mock_service,
    ):
        mock_agents.get_agent_by_id = AsyncMock(return_value=(_agent(), None))
        mock_service.get_platform_tool_by_id = AsyncMock(
            return_value=(_tool(is_visible=False), None)
        )
        mock_service.get_agent_tools = AsyncMock(return_value=([configured], None))
        mock_service.configure_agent_tool = AsyncMock(return_value=(configured, None))

        result = await configure_agent_tool(
            agent_tool_data=tool_data,
            user_data=(USER_ID, profile),
        )

    assert result is configured
    mock_service.configure_agent_tool.assert_awaited_once_with(tool_data)
