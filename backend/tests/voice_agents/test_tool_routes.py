"""
Tests for tool_routes permission gating (Task #26 — N1 follow-up #3).

Closes the 4 CRIT permission gaps in `backend/src/voice_agents/tool_routes.py`:
  - PUT   /api/v1/tools/agent/{agent_tool_id}
  - POST  /api/v1/tools/agent/{agent_tool_id}/logout
  - PUT   /api/v1/tools/agent/{agent_tool_id}/api-key
  - DELETE /api/v1/tools/agent/{agent_tool_id}

All four routes previously had no permission check at all — any
authenticated user could rewrite OAuth tokens, third-party API keys,
or permanently delete a tool configuration by guessing the UUID.

Contract:
  - platform_admin → 200 on all 4 (org-agnostic)
  - org_admin on the agent's org → 200 on all 4
  - org_admin on a DIFFERENT org → 403 on all 4
  - regular user (no admin role) → 403 on all 4
  - unauthenticated → 401 (handled by `get_authenticated_user`,
    not exercised here)
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi import HTTPException

from shared.voice_agents.models import VoiceAgent
from shared.voice_agents.tool_models import AgentToolResponse, AuthStatus, ConnectionStatus


# Test fixtures
TEST_AGENT_TOOL_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_AGENT_ID = UUID("00000000-0000-0000-0000-000000000010")
TEST_ORG_ID = UUID("00000000-0000-0000-0000-000000000020")
TEST_OTHER_ORG_ID = UUID("00000000-0000-0000-0000-000000000030")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000040")


def _make_agent(agent_id=TEST_AGENT_ID, org_id=TEST_ORG_ID):
    """Build a minimal VoiceAgent fixture."""
    return VoiceAgent(
        id=agent_id,
        organization_id=org_id,
        name="Test Agent",
        phone_number="+15555550100",
        persona="Test",
        tone="Professional",
        mission="Help",
        custom_instructions="Be polite",
        is_active=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


def _make_user_profile(
    is_platform_admin: bool = False,
    is_org_admin_on: str | None = None,
):
    """Build a UserProfile mock. `is_org_admin_on` is the org_id string
    the user holds `org_admin` on, or None for no org_admin role."""
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )
    return profile


def _make_agent_tool_response(agent_id=TEST_AGENT_ID):
    """Build a minimal AgentToolResponse fixture."""
    return AgentToolResponse(
        id=TEST_AGENT_TOOL_ID,
        agent_id=agent_id,
        tool_id=UUID("00000000-0000-0000-0000-000000000050"),
        config=None,
        unselected_functions=None,
        is_enabled=True,
        auth_status=AuthStatus.AUTHENTICATED,
        connection_status=ConnectionStatus.CONNECTED_AUTH_VALID,
        token_expires_at=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


class TestToolRoutesPermissions:
    """Permission-gating contract for the 4 CRIT endpoints.

    Each test patches both `tool_service` and `voice_agent_service`
    so the route can:
      1. Resolve agent_tool_id → agent_id (new lookup helper, see GREEN)
      2. Resolve agent_id → org_id (existing get_agent_by_id)
      3. Enforce org_admin(org_id) OR platform_admin
    """

    # ---------- PUT /agent/{agent_tool_id} ----------

    @pytest.mark.asyncio
    async def test_update_agent_tool_regular_user_forbidden(self):
        """Regular user (no admin role) cannot rewrite tool config."""
        from src.voice_agents.tool_routes import update_agent_tool
        from shared.voice_agents.tool_models import AgentToolUpdate

        profile = _make_user_profile()  # no roles
        agent = _make_agent()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                # Service-level lookup that the GREEN fix introduces.
                # For RED, we expect the route to refuse BEFORE calling
                # the update method.
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await update_agent_tool(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        update_data=AgentToolUpdate(is_enabled=False),
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403
                # The service update must NOT have been called.
                mock_ts.update_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_agent_tool_org_admin_on_agent_org_allowed(self):
        """Org admin on the agent's own org → 200."""
        from src.voice_agents.tool_routes import update_agent_tool
        from shared.voice_agents.tool_models import AgentToolUpdate

        profile = _make_user_profile(
            is_org_admin_on=str(TEST_ORG_ID)
        )
        agent = _make_agent()
        updated = _make_agent_tool_response()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock(
                    return_value=(updated, None)
                )

                result = await update_agent_tool(
                    agent_tool_id=TEST_AGENT_TOOL_ID,
                    update_data=AgentToolUpdate(is_enabled=False),
                    user_data=(TEST_USER_ID, profile),
                )

                assert result is not None
                mock_ts.update_agent_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_agent_tool_org_admin_on_other_org_forbidden(self):
        """Org admin on a DIFFERENT org → 403 (cross-org IDOR guard)."""
        from src.voice_agents.tool_routes import update_agent_tool
        from shared.voice_agents.tool_models import AgentToolUpdate

        profile = _make_user_profile(
            is_org_admin_on=str(TEST_OTHER_ORG_ID)  # not the agent's org
        )
        agent = _make_agent(org_id=TEST_ORG_ID)

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await update_agent_tool(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        update_data=AgentToolUpdate(is_enabled=False),
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403
                mock_ts.update_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_agent_tool_platform_admin_allowed(self):
        """Platform admin → 200 regardless of org."""
        from src.voice_agents.tool_routes import update_agent_tool
        from shared.voice_agents.tool_models import AgentToolUpdate

        profile = _make_user_profile(is_platform_admin=True)
        agent = _make_agent()
        updated = _make_agent_tool_response()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock(
                    return_value=(updated, None)
                )

                result = await update_agent_tool(
                    agent_tool_id=TEST_AGENT_TOOL_ID,
                    update_data=AgentToolUpdate(is_enabled=False),
                    user_data=(TEST_USER_ID, profile),
                )

                assert result is not None

    # ---------- POST /agent/{agent_tool_id}/logout ----------

    @pytest.mark.asyncio
    async def test_logout_agent_tool_regular_user_forbidden(self):
        """Regular user cannot clear OAuth tokens (logout)."""
        from src.voice_agents.tool_routes import logout_agent_tool

        profile = _make_user_profile()
        agent = _make_agent()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await logout_agent_tool(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403
                mock_ts.update_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_logout_agent_tool_org_admin_on_other_org_forbidden(self):
        """Org admin on a different org → 403 (cannot log out a peer's OAuth tokens)."""
        from src.voice_agents.tool_routes import logout_agent_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        agent = _make_agent(org_id=TEST_ORG_ID)

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await logout_agent_tool(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_logout_agent_tool_org_admin_on_own_org_allowed(self):
        from src.voice_agents.tool_routes import logout_agent_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()
        cleared = _make_agent_tool_response()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock(
                    return_value=(cleared, None)
                )

                result = await logout_agent_tool(
                    agent_tool_id=TEST_AGENT_TOOL_ID,
                    user_data=(TEST_USER_ID, profile),
                )

                assert result is not None

    # ---------- PUT /agent/{agent_tool_id}/api-key ----------

    @pytest.mark.asyncio
    async def test_set_api_key_regular_user_forbidden(self):
        """Regular user cannot overwrite a real user's Google API key."""
        from src.voice_agents.tool_routes import set_api_key

        profile = _make_user_profile()
        agent = _make_agent()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await set_api_key(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        api_key="attacker-controlled-key",
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403
                mock_ts.update_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_api_key_org_admin_on_other_org_forbidden(self):
        from src.voice_agents.tool_routes import set_api_key

        profile = _make_user_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        agent = _make_agent(org_id=TEST_ORG_ID)

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await set_api_key(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        api_key="attacker-controlled-key",
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_set_api_key_org_admin_on_own_org_allowed(self):
        from src.voice_agents.tool_routes import set_api_key

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()
        updated = _make_agent_tool_response()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.update_agent_tool = AsyncMock(
                    return_value=(updated, None)
                )

                result = await set_api_key(
                    agent_tool_id=TEST_AGENT_TOOL_ID,
                    api_key="legitimate-key",
                    user_data=(TEST_USER_ID, profile),
                )

                assert result is not None

    # ---------- DELETE /agent/{agent_tool_id} ----------

    @pytest.mark.asyncio
    async def test_delete_agent_tool_regular_user_forbidden(self):
        """Regular user cannot permanently delete a tool configuration."""
        from src.voice_agents.tool_routes import delete_agent_tool

        profile = _make_user_profile()
        agent = _make_agent()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.delete_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await delete_agent_tool(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403
                mock_ts.delete_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_agent_tool_org_admin_on_other_org_forbidden(self):
        from src.voice_agents.tool_routes import delete_agent_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_OTHER_ORG_ID))
        agent = _make_agent(org_id=TEST_ORG_ID)

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.delete_agent_tool = AsyncMock()

                with pytest.raises(HTTPException) as exc_info:
                    await delete_agent_tool(
                        agent_tool_id=TEST_AGENT_TOOL_ID,
                        user_data=(TEST_USER_ID, profile),
                    )

                assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_agent_tool_org_admin_on_own_org_allowed(self):
        from src.voice_agents.tool_routes import delete_agent_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.delete_agent_tool = AsyncMock(
                    return_value=(True, None)
                )

                result = await delete_agent_tool(
                    agent_tool_id=TEST_AGENT_TOOL_ID,
                    user_data=(TEST_USER_ID, profile),
                )

                assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_agent_tool_platform_admin_allowed(self):
        from src.voice_agents.tool_routes import delete_agent_tool

        profile = _make_user_profile(is_platform_admin=True)
        agent = _make_agent()

        with patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_agent_tool_by_id = AsyncMock(
                    return_value=(_make_agent_tool_response(), None)
                )
                mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
                mock_ts.delete_agent_tool = AsyncMock(
                    return_value=(True, None)
                )

                result = await delete_agent_tool(
                    agent_tool_id=TEST_AGENT_TOOL_ID,
                    user_data=(TEST_USER_ID, profile),
                )

                assert result["deleted"] is True
