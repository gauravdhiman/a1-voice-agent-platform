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
TEST_TOOL_ID = UUID("00000000-0000-0000-0000-000000000050")


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
    """Build a UserProfile mock.

    `is_org_admin_on` is the org_id string the user holds `org_admin` on
    (and, matching the seed, ``agent:update`` / ``agent:read`` on that
    org). Tool writes now gate on ``agent:update`` via
    ``assert_has_permission``, not a bare role ladder.
    """
    profile = Mock()
    profile.has_role = Mock(
        side_effect=lambda role, org_id=None: (
            (role == "platform_admin" and is_platform_admin)
            or (role == "org_admin" and org_id == is_org_admin_on)
        )
    )
    profile.has_permission = Mock(
        side_effect=lambda perm, org_id=None: (
            is_org_admin_on is not None
            and org_id == is_org_admin_on
            and perm in ("agent:update", "agent:read", "agent:create", "agent:delete")
        )
    )
    # current_organization_id is the org the embedded permissions are scoped to;
    # routes use it to force org-scoping on custom-MCP creates.
    profile.current_organization_id = (
        UUID(is_org_admin_on) if is_org_admin_on else None
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


class TestPremiumToolGate:
    """Premium tools are catalog-visible but gated at attach time.

    ``POST /tools/agent`` must 403 when the target ``platform_tools`` row has
    ``is_premium=True`` and the org's plan does not entitle the
    ``premium_tools`` feature. Non-premium tools and entitled orgs pass.
    """

    def _make_platform_tool(self, is_premium: bool = False):
        from shared.voice_agents.tool_models import PlatformTool

        return PlatformTool(
            id=TEST_TOOL_ID,
            name="Premium MCP",
            description="Test",
            is_active=True,
            is_premium=is_premium,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

    @pytest.mark.asyncio
    async def test_premium_tool_denied_without_feature(self):
        from src.voice_agents.tool_routes import configure_agent_tool
        from shared.voice_agents.tool_models import AgentToolCreate

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()
        tool_data = AgentToolCreate(agent_id=TEST_AGENT_ID, tool_id=TEST_TOOL_ID)

        with (
            patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas,
            patch("src.voice_agents.tool_routes.tool_service") as mock_ts,
            patch("src.voice_agents.tool_routes.entitlement_service") as mock_ent,
        ):
            mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_ts.get_platform_tool_by_id = AsyncMock(
                return_value=(self._make_platform_tool(is_premium=True), None)
            )
            mock_ent.check_feature = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await configure_agent_tool(
                    agent_tool_data=tool_data,
                    user_data=(TEST_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            mock_ent.check_feature.assert_awaited_once_with(
                TEST_ORG_ID, "premium_tools"
            )
            mock_ts.configure_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_premium_tool_allowed_with_feature(self):
        from src.voice_agents.tool_routes import configure_agent_tool
        from shared.voice_agents.tool_models import AgentToolCreate

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()
        tool_data = AgentToolCreate(agent_id=TEST_AGENT_ID, tool_id=TEST_TOOL_ID)
        configured = _make_agent_tool_response()

        with (
            patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas,
            patch("src.voice_agents.tool_routes.tool_service") as mock_ts,
            patch("src.voice_agents.tool_routes.entitlement_service") as mock_ent,
        ):
            mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_ts.get_platform_tool_by_id = AsyncMock(
                return_value=(self._make_platform_tool(is_premium=True), None)
            )
            mock_ent.check_feature = AsyncMock(return_value=True)
            mock_ts.configure_agent_tool = AsyncMock(return_value=(configured, None))

            result = await configure_agent_tool(
                agent_tool_data=tool_data,
                user_data=(TEST_USER_ID, profile),
            )

            assert result is configured
            mock_ent.check_feature.assert_awaited_once_with(
                TEST_ORG_ID, "premium_tools"
            )
            mock_ts.configure_agent_tool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_premium_tool_skips_gate(self):
        from src.voice_agents.tool_routes import configure_agent_tool
        from shared.voice_agents.tool_models import AgentToolCreate

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()
        tool_data = AgentToolCreate(agent_id=TEST_AGENT_ID, tool_id=TEST_TOOL_ID)
        configured = _make_agent_tool_response()

        with (
            patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas,
            patch("src.voice_agents.tool_routes.tool_service") as mock_ts,
            patch("src.voice_agents.tool_routes.entitlement_service") as mock_ent,
        ):
            mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_ts.get_platform_tool_by_id = AsyncMock(
                return_value=(self._make_platform_tool(is_premium=False), None)
            )
            mock_ent.check_feature = AsyncMock(return_value=False)
            mock_ts.configure_agent_tool = AsyncMock(return_value=(configured, None))

            result = await configure_agent_tool(
                agent_tool_data=tool_data,
                user_data=(TEST_USER_ID, profile),
            )

            assert result is configured
            mock_ent.check_feature.assert_not_called()
            mock_ts.configure_agent_tool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_tool_skips_gate(self):
        """A tool missing from the catalog is not premium-gated (the service
        layer surfaces the not-found error downstream)."""
        from src.voice_agents.tool_routes import configure_agent_tool
        from shared.voice_agents.tool_models import AgentToolCreate

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        agent = _make_agent()
        tool_data = AgentToolCreate(agent_id=TEST_AGENT_ID, tool_id=TEST_TOOL_ID)
        configured = _make_agent_tool_response()

        with (
            patch("src.voice_agents.tool_routes.voice_agent_service") as mock_vas,
            patch("src.voice_agents.tool_routes.tool_service") as mock_ts,
            patch("src.voice_agents.tool_routes.entitlement_service") as mock_ent,
        ):
            mock_vas.get_agent_by_id = AsyncMock(return_value=(agent, None))
            mock_ts.get_platform_tool_by_id = AsyncMock(
                return_value=(None, "Platform tool not found")
            )
            mock_ent.check_feature = AsyncMock(return_value=False)
            mock_ts.configure_agent_tool = AsyncMock(return_value=(configured, None))

            result = await configure_agent_tool(
                agent_tool_data=tool_data,
                user_data=(TEST_USER_ID, profile),
            )

            assert result is configured
            mock_ent.check_feature.assert_not_called()


class TestMcpDiscoverAndCreate:
    """Platform-admin authoring endpoints (RFC §6.6 publish lifecycle).

    Covers:
      - POST /api/v1/tools/mcp/discover  — platform-admin only; validate URL,
        call McpClient.list_tools, return sanitized tool list (in-memory).
      - POST /api/v1/tools/mcp/parse    — platform-admin only; parse mcpServers JSON.
      - POST /api/v1/tools/platform      — platform-admin only; author a draft or
        publish-on-create. MCP rows are global (org ignored). URL validated.

    Org admins and regular users are rejected (403) on all three — authoring is
    a platform-admin action. Org admins ATTACH published servers via
    ``POST /tools/agent`` (gated on ``agent:update``), tested in
    :class:`TestToolRoutesPermissions`.
    """

    @pytest.mark.asyncio
    async def test_discover_returns_sanitized_tools_for_platform_admin(self):
        from src.voice_agents.tool_routes import discover_mcp_tools, McpDiscoverRequest
        from shared.voice_agents.tools.mcp.models import McpToolDef

        profile = _make_user_profile(is_platform_admin=True)
        tool_def = McpToolDef(
            name="add", description="add two numbers", input_schema={"type": "object"}
        )

        with patch("src.voice_agents.tool_routes.validate_mcp_server_url", return_value=(True, "")):
            with patch(
                "src.voice_agents.tool_routes.list_tools_json_http",
                new_callable=AsyncMock,
                return_value=[tool_def],
            ) as mock_discover:
                result = await discover_mcp_tools(
                    request=McpDiscoverRequest(url="https://example.com/mcp", headers={}),
                    user_data=(TEST_USER_ID, profile),
                )

                assert "tools" in result
                assert result["tools"][0]["name"] == "add"
                assert result["tools"][0]["description"] == "add two numbers"
                mock_discover.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discover_merges_stored_secret_headers_when_tool_id_set(self):
        """Edit re-test: blank secret field still uses encrypted stored headers."""
        from src.voice_agents.tool_routes import discover_mcp_tools, McpDiscoverRequest
        from shared.voice_agents.tools.mcp.models import McpToolDef

        profile = _make_user_profile(is_platform_admin=True)
        tool_def = McpToolDef(
            name="list", description="list", input_schema={"type": "object"}
        )
        tool_id = TEST_TOOL_ID

        with (
            patch(
                "src.voice_agents.tool_routes.validate_mcp_server_url",
                return_value=(True, ""),
            ),
            patch(
                "src.voice_agents.tool_routes.tool_service.merge_stored_mcp_secret_headers",
                new_callable=AsyncMock,
                return_value=(
                    {"Authorization": "Bearer stored-secret", "X-Client": "ui"},
                    None,
                ),
            ) as mock_merge,
            patch(
                "src.voice_agents.tool_routes.list_tools_json_http",
                new_callable=AsyncMock,
                return_value=[tool_def],
            ) as mock_discover,
        ):
            result = await discover_mcp_tools(
                request=McpDiscoverRequest(
                    url="https://example.com/mcp",
                    headers={"X-Client": "ui"},
                    tool_id=tool_id,
                ),
                user_data=(TEST_USER_ID, profile),
            )

            assert result["tools"][0]["name"] == "list"
            mock_merge.assert_awaited_once_with(
                tool_id,
                {"X-Client": "ui"},
                test_api_key=None,
            )
            config = mock_discover.await_args.args[0]
            assert config.headers["Authorization"] == "Bearer stored-secret"
            assert config.headers["X-Client"] == "ui"

    @pytest.mark.asyncio
    async def test_discover_requires_test_key_when_stored_template_needs_it(self):
        """Stored {{KEY}} templates need a transient test key on re-probe."""
        from src.voice_agents.tool_routes import discover_mcp_tools, McpDiscoverRequest

        profile = _make_user_profile(is_platform_admin=True)

        with (
            patch(
                "src.voice_agents.tool_routes.validate_mcp_server_url",
                return_value=(True, ""),
            ),
            patch(
                "src.voice_agents.tool_routes.tool_service.merge_stored_mcp_secret_headers",
                new_callable=AsyncMock,
                return_value=(
                    {},
                    "Stored secret headers use {{KEY}}. Enter a Test API key "
                    "to substitute it for this probe (it is never saved).",
                ),
            ),
            patch(
                "src.voice_agents.tool_routes.list_tools_json_http",
                new_callable=AsyncMock,
            ) as mock_discover,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await discover_mcp_tools(
                    request=McpDiscoverRequest(
                        url="https://example.com/mcp",
                        headers={},
                        tool_id=TEST_TOOL_ID,
                    ),
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 400
            assert "{{KEY}}" in str(exc_info.value.detail)
            mock_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_rejects_ssrf_url_without_calling_client(self):
        from src.voice_agents.tool_routes import discover_mcp_tools, McpDiscoverRequest

        profile = _make_user_profile(is_platform_admin=True)

        with patch(
            "src.voice_agents.tool_routes.validate_mcp_server_url",
            return_value=(False, "URL resolves to a blocked address (169.254.169.254)"),
        ):
            with patch("src.voice_agents.tool_routes.list_tools_json_http", new_callable=AsyncMock) as mock_discover:
                with pytest.raises(HTTPException) as exc_info:
                    await discover_mcp_tools(
                        request=McpDiscoverRequest(url="https://169.254.169.254/", headers={}),
                        user_data=(TEST_USER_ID, profile),
                    )
                assert exc_info.value.status_code == 400
                mock_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_forbidden_for_org_admin(self):
        """Org admins cannot author — discover is platform-admin only."""
        from src.voice_agents.tool_routes import discover_mcp_tools, McpDiscoverRequest

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.validate_mcp_server_url") as mock_val:
            with patch("src.voice_agents.tool_routes.list_tools_json_http", new_callable=AsyncMock) as mock_discover:
                with pytest.raises(HTTPException) as exc_info:
                    await discover_mcp_tools(
                        request=McpDiscoverRequest(url="https://example.com/mcp", headers={}),
                        user_data=(TEST_USER_ID, profile),
                    )
                assert exc_info.value.status_code == 403
                mock_val.assert_not_called()
                mock_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_forbidden_for_regular_user(self):
        from src.voice_agents.tool_routes import discover_mcp_tools, McpDiscoverRequest

        profile = _make_user_profile()  # no roles

        with patch("src.voice_agents.tool_routes.validate_mcp_server_url") as mock_val:
            with patch("src.voice_agents.tool_routes.list_tools_json_http", new_callable=AsyncMock) as mock_discover:
                with pytest.raises(HTTPException) as exc_info:
                    await discover_mcp_tools(
                        request=McpDiscoverRequest(url="https://example.com/mcp", headers={}),
                        user_data=(TEST_USER_ID, profile),
                    )
                assert exc_info.value.status_code == 403
                mock_val.assert_not_called()
                mock_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_returns_servers_and_errors_for_platform_admin(self):
        from src.voice_agents.tool_routes import parse_mcp_servers, McpParseRequest

        profile = _make_user_profile(is_platform_admin=True)
        raw = (
            '{"mcpServers": {'
            '"cal": {"url": "https://cal.example.com/mcp"},'
            '"fs": {"command": "npx"}'
            "}}"
        )

        result = await parse_mcp_servers(
            request=McpParseRequest(raw=raw), user_data=(TEST_USER_ID, profile)
        )

        assert len(result["servers"]) == 1
        assert result["servers"][0]["name"] == "cal"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["name"] == "fs"

    @pytest.mark.asyncio
    async def test_parse_forbidden_for_org_admin(self):
        from src.voice_agents.tool_routes import parse_mcp_servers, McpParseRequest

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with pytest.raises(HTTPException) as exc_info:
            await parse_mcp_servers(
                request=McpParseRequest(raw="{}"), user_data=(TEST_USER_ID, profile)
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_mcp_platform_admin_creates_draft_by_default(self):
        """A platform admin authors an MCP server as a draft (is_published
        defaults False); the route forwards the payload to upsert. MCP rows are
        global — the payload organization_id is ignored (the service forces it
        off)."""
        from src.voice_agents.tool_routes import create_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_platform_admin=True)
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
            mcp_server_name="custom",
            # organization_id is intentionally NOT set — MCP rows are global.
        )

        with patch(
            "src.voice_agents.tool_routes.validate_mcp_server_url", return_value=(True, "")
        ):
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.upsert_platform_tool = AsyncMock(
                    return_value=(Mock(name="created", mcp_secret_headers_configured=False), None)
                )

                await create_platform_tool(
                    tool_data=tool_data,
                    user_data=(TEST_USER_ID, profile),
                )

                upserted = mock_ts.upsert_platform_tool.await_args[0][0]
                assert upserted.mcp_server_url == "https://example.com/mcp"
                assert upserted.is_published is False  # draft by default

    @pytest.mark.asyncio
    async def test_create_mcp_platform_admin_can_publish_on_create(self):
        """A platform admin may set is_published=True to publish immediately."""
        from src.voice_agents.tool_routes import create_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_platform_admin=True)
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
            is_published=True,
        )

        with patch(
            "src.voice_agents.tool_routes.validate_mcp_server_url", return_value=(True, "")
        ):
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.upsert_platform_tool = AsyncMock(
                    return_value=(Mock(name="created"), None)
                )

                await create_platform_tool(
                    tool_data=tool_data,
                    user_data=(TEST_USER_ID, profile),
                )

                upserted = mock_ts.upsert_platform_tool.await_args[0][0]
                assert upserted.is_published is True

    @pytest.mark.asyncio
    async def test_create_mcp_forbidden_for_org_admin(self):
        """Org admins cannot author MCP servers — 403 before any upsert."""
        from src.voice_agents.tool_routes import create_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
        )

        with patch(
            "src.voice_agents.tool_routes.validate_mcp_server_url", return_value=(True, "")
        ):
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                with pytest.raises(HTTPException) as exc_info:
                    await create_platform_tool(
                        tool_data=tool_data,
                        user_data=(TEST_USER_ID, profile),
                    )
                assert exc_info.value.status_code == 403
                mock_ts.upsert_platform_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_mcp_rejects_bad_url(self):
        from src.voice_agents.tool_routes import create_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_platform_admin=True)
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://169.254.169.254/",
        )

        with patch(
            "src.voice_agents.tool_routes.validate_mcp_server_url",
            return_value=(False, "blocked"),
        ):
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                with pytest.raises(HTTPException) as exc_info:
                    await create_platform_tool(
                        tool_data=tool_data,
                        user_data=(TEST_USER_ID, profile),
                    )
                assert exc_info.value.status_code == 400
                mock_ts.upsert_platform_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_mcp_rejects_missing_url(self):
        from src.voice_agents.tool_routes import create_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_platform_admin=True)
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url=None,
        )

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            with pytest.raises(HTTPException) as exc_info:
                await create_platform_tool(
                    tool_data=tool_data,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 400
            mock_ts.upsert_platform_tool.assert_not_called()


class TestPlatformToolPublishLifecycle:
    """publish / unpublish / PUT edit / DELETE — platform-admin only (RFC §6.6)."""

    @pytest.mark.asyncio
    async def test_publish_platform_admin_allowed(self):
        from src.voice_agents.tool_routes import publish_platform_tool

        profile = _make_user_profile(is_platform_admin=True)
        published = Mock(name="published", is_published=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.publish_platform_tool = AsyncMock(return_value=(published, None))

            result = await publish_platform_tool(
                tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
            )

            mock_ts.publish_platform_tool.assert_awaited_once_with(TEST_TOOL_ID, True)
            assert result is published

    @pytest.mark.asyncio
    async def test_publish_forbidden_for_org_admin(self):
        from src.voice_agents.tool_routes import publish_platform_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            with pytest.raises(HTTPException) as exc_info:
                await publish_platform_tool(
                    tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_ts.publish_platform_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_unknown_returns_404(self):
        from src.voice_agents.tool_routes import publish_platform_tool

        profile = _make_user_profile(is_platform_admin=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.publish_platform_tool = AsyncMock(
                return_value=(None, "Platform tool not found")
            )
            with pytest.raises(HTTPException) as exc_info:
                await publish_platform_tool(
                    tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unpublish_platform_admin_allowed(self):
        from src.voice_agents.tool_routes import unpublish_platform_tool

        profile = _make_user_profile(is_platform_admin=True)
        draft = Mock(name="draft", is_published=False)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.publish_platform_tool = AsyncMock(return_value=(draft, None))

            result = await unpublish_platform_tool(
                tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
            )

            mock_ts.publish_platform_tool.assert_awaited_once_with(TEST_TOOL_ID, False)
            assert result is draft

    @pytest.mark.asyncio
    async def test_unpublish_forbidden_for_org_admin(self):
        from src.voice_agents.tool_routes import unpublish_platform_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            with pytest.raises(HTTPException) as exc_info:
                await unpublish_platform_tool(
                    tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_ts.publish_platform_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_platform_tool_platform_admin_allowed(self):
        from src.voice_agents.tool_routes import update_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_platform_admin=True)
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
        )
        updated = Mock(name="updated")

        with patch(
            "src.voice_agents.tool_routes.validate_mcp_server_url", return_value=(True, "")
        ):
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.update_platform_tool = AsyncMock(return_value=(updated, None))

                result = await update_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    tool_data=tool_data,
                    user_data=(TEST_USER_ID, profile),
                )

                mock_ts.update_platform_tool.assert_awaited_once()
                assert result is updated

    @pytest.mark.asyncio
    async def test_update_platform_tool_forbidden_for_org_admin(self):
        from src.voice_agents.tool_routes import update_platform_tool
        from shared.voice_agents.tool_models import PlatformToolCreate, ToolSource

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))
        tool_data = PlatformToolCreate(
            name="custom-mcp",
            tool_source=ToolSource.MCP,
            mcp_server_url="https://example.com/mcp",
        )

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            with pytest.raises(HTTPException) as exc_info:
                await update_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    tool_data=tool_data,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_ts.update_platform_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_platform_tool_platform_admin_allowed(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_platform_admin=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.delete_platform_tool = AsyncMock(return_value=(True, None))

            result = await delete_platform_tool(
                tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
            )

            mock_ts.delete_platform_tool.assert_awaited_once_with(
                TEST_TOOL_ID, force=False
            )
            assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_platform_tool_forbidden_for_org_admin(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_tool(
                    tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 403
            mock_ts.delete_platform_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_platform_tool_not_found(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_platform_admin=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.delete_platform_tool = AsyncMock(return_value=(None, None))
            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_tool(
                    tool_id=TEST_TOOL_ID, user_data=(TEST_USER_ID, profile)
                )
            assert exc_info.value.status_code == 404


class TestGetPlatformToolsVisibility:
    """GET /platform publish-lifecycle visibility (RFC §6.6).

    Org users see published-only (default). Platform admins pass
    ``include_drafts=true`` to see drafts. A non-platform-admin requesting
    drafts is rejected (403). The org-scoped per-org filter is retired.
    """

    @pytest.mark.asyncio
    async def test_org_user_gets_published_only_by_default(self):
        from src.voice_agents.tool_routes import get_platform_tools

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([], None))

            await get_platform_tools(
                only_active=True,
                include_drafts=False,
                user_data=(TEST_USER_ID, profile),
            )

            # only_active is forwarded positionally; include_drafts as kwarg.
            call = mock_ts.get_platform_tools.await_args
            assert call.args == (True,)
            assert call.kwargs == {"include_drafts": False}

    @pytest.mark.asyncio
    async def test_regular_user_gets_published_only_by_default(self):
        from src.voice_agents.tool_routes import get_platform_tools

        profile = _make_user_profile()  # no roles

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([], None))

            # include_drafts must be passed explicitly — calling the route
            # function directly leaves the FastAPI Query() default sentinel in
            # place, which is truthy and would trip the 403 guard.
            await get_platform_tools(
                only_active=True,
                include_drafts=False,
                user_data=(TEST_USER_ID, profile),
            )

            call = mock_ts.get_platform_tools.await_args
            assert call.args == (True,)
            assert call.kwargs == {"include_drafts": False}

    @pytest.mark.asyncio
    async def test_platform_admin_include_drafts_sees_all(self):
        from src.voice_agents.tool_routes import get_platform_tools

        profile = _make_user_profile(is_platform_admin=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([], None))

            await get_platform_tools(
                only_active=False,
                include_drafts=True,
                user_data=(TEST_USER_ID, profile),
            )

            call = mock_ts.get_platform_tools.await_args
            assert call.args == (False,)
            assert call.kwargs == {"include_drafts": True}

    @pytest.mark.asyncio
    async def test_non_platform_admin_include_drafts_forbidden(self):
        """An org admin (or regular user) requesting drafts is rejected (403)
        — drafts are platform-admin-only."""
        from src.voice_agents.tool_routes import get_platform_tools

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            with pytest.raises(HTTPException) as exc_info:
                await get_platform_tools(
                    only_active=True,
                    include_drafts=True,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_ts.get_platform_tools.assert_not_called()


class TestPlatformToolDeleteGuardrails:
    """Delete-guardrail + usage contract for platform tools (RFC §6.6).

    Contract:
      - GET /platform/{tool_id}/usage → 200 {count, agents} for platform_admin;
        403 for anyone else.
      - DELETE /platform/{tool_id} with an in-use MCP tool → 409 {error: in_use,
        count, agents} (the admin must confirm + force).
      - DELETE ?force=true on an in-use tool → 200 and an audit log entry
        naming the detached agents.
      - DELETE of a native (code-backed) tool → 400 (steer to unpublish).
      - DELETE of a missing tool → 404.
      - Non-platform-admin → 403 before any service call.
    """

    @pytest.mark.asyncio
    async def test_get_usage_returns_agents_for_platform_admin(self):
        from src.voice_agents.tool_routes import get_platform_tool_usage

        profile = _make_user_profile(is_platform_admin=True)
        agents = [
            {"agent_id": str(TEST_AGENT_ID), "agent_name": "Alex",
             "organization_id": str(TEST_ORG_ID)},
        ]
        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tool_usage = AsyncMock(return_value=(agents, None))

            result = await get_platform_tool_usage(
                tool_id=TEST_TOOL_ID,
                user_data=(TEST_USER_ID, profile),
            )

        assert result == {"count": 1, "agents": agents}

    @pytest.mark.asyncio
    async def test_get_usage_forbidden_for_non_platform_admin(self):
        from src.voice_agents.tool_routes import get_platform_tool_usage

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tool_usage = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_platform_tool_usage(
                    tool_id=TEST_TOOL_ID,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_ts.get_platform_tool_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_in_use_returns_409_with_agents(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_platform_admin=True)
        agents = [
            {"agent_id": str(TEST_AGENT_ID), "agent_name": "Alex",
             "organization_id": str(TEST_ORG_ID)},
        ]
        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tool_usage = AsyncMock(return_value=(agents, None))
            mock_ts.delete_platform_tool = AsyncMock(return_value=(None, "in_use"))

            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    force=False,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["error"] == "in_use"
            assert exc_info.value.detail["count"] == 1
            assert exc_info.value.detail["agents"] == agents
            # The tool row was NOT deleted.
            mock_ts.delete_platform_tool.assert_awaited_once_with(
                TEST_TOOL_ID, force=False
            )

    @pytest.mark.asyncio
    async def test_delete_force_succeeds_and_audits(self, caplog):
        import logging

        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_platform_admin=True)
        agents = [
            {"agent_id": str(TEST_AGENT_ID), "agent_name": "Alex",
             "organization_id": str(TEST_ORG_ID)},
        ]
        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tool_usage = AsyncMock(return_value=(agents, None))
            mock_ts.delete_platform_tool = AsyncMock(return_value=(True, None))

            with caplog.at_level(logging.INFO, logger="src.voice_agents.tool_routes"):
                result = await delete_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    force=True,
                    user_data=(TEST_USER_ID, profile),
                )

        assert result == {"id": str(TEST_TOOL_ID), "deleted": True}
        # Usage was fetched up front so the audit can name the detached agents.
        mock_ts.get_platform_tool_usage.assert_awaited_once()
        mock_ts.delete_platform_tool.assert_awaited_once_with(
            TEST_TOOL_ID, force=True
        )
        # An audit log entry recording the force-delete + detached agent.
        audit = [r for r in caplog.records if "force" in r.getMessage().lower()]
        assert audit, "expected a force-delete audit log entry"
        assert any("Alex" in r.getMessage() or str(TEST_AGENT_ID) in r.getMessage()
                   for r in audit)

    @pytest.mark.asyncio
    async def test_delete_legacy_tool_returns_400(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_platform_admin=True)
        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tool_usage = AsyncMock()
            mock_ts.delete_platform_tool = AsyncMock(
                return_value=(None, "legacy_tools_cannot_be_deleted")
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    force=False,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 400
            # No usage fetch is needed for the legacy refusal (not force, not in_use).
            mock_ts.get_platform_tool_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_unknown_tool_returns_404(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_platform_admin=True)
        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tool_usage = AsyncMock()
            mock_ts.delete_platform_tool = AsyncMock(
                return_value=(None, "Platform tool not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    force=False,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 404
            mock_ts.get_platform_tool_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_forbidden_for_non_platform_admin(self):
        from src.voice_agents.tool_routes import delete_platform_tool

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.delete_platform_tool = AsyncMock()
            mock_ts.get_platform_tool_usage = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await delete_platform_tool(
                    tool_id=TEST_TOOL_ID,
                    force=False,
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_ts.delete_platform_tool.assert_not_called()
            mock_ts.get_platform_tool_usage.assert_not_called()


class TestPlatformToolPremiumToggle:
    """Premium flag management for platform tools (platform-admin only).

    ``POST /platform/{tool_id}/premium`` flips ``is_premium`` so a platform
    admin can gate a catalog tool behind the ``premium_tools`` plan feature
    without resubmitting the full create payload (the PUT route requires a
    complete ``PlatformToolCreate``). Contract:
      - platform_admin → 200 with the updated tool (flag persisted)
      - non-platform-admin → 403 before any service call
      - unknown tool id → 404
    """

    def _make_premium_update(self, is_premium: bool):
        from src.voice_agents.tool_routes import PlatformToolPremiumUpdate

        return PlatformToolPremiumUpdate(is_premium=is_premium)

    def _make_updated_tool(self, is_premium: bool):
        from shared.voice_agents.tool_models import PlatformTool

        return PlatformTool(
            id=TEST_TOOL_ID,
            name="Premium MCP",
            description="Test",
            is_active=True,
            is_premium=is_premium,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

    @pytest.mark.asyncio
    async def test_platform_admin_sets_premium_true(self):
        from src.voice_agents.tool_routes import set_platform_tool_premium

        profile = _make_user_profile(is_platform_admin=True)
        updated = self._make_updated_tool(is_premium=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.set_platform_tool_premium = AsyncMock(return_value=(updated, None))

            result = await set_platform_tool_premium(
                tool_id=TEST_TOOL_ID,
                premium_update=self._make_premium_update(is_premium=True),
                user_data=(TEST_USER_ID, profile),
            )

        assert result.is_premium is True
        mock_ts.set_platform_tool_premium.assert_awaited_once_with(
            TEST_TOOL_ID, True
        )

    @pytest.mark.asyncio
    async def test_platform_admin_sets_premium_false(self):
        from src.voice_agents.tool_routes import set_platform_tool_premium

        profile = _make_user_profile(is_platform_admin=True)
        updated = self._make_updated_tool(is_premium=False)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.set_platform_tool_premium = AsyncMock(return_value=(updated, None))

            result = await set_platform_tool_premium(
                tool_id=TEST_TOOL_ID,
                premium_update=self._make_premium_update(is_premium=False),
                user_data=(TEST_USER_ID, profile),
            )

        assert result.is_premium is False
        mock_ts.set_platform_tool_premium.assert_awaited_once_with(
            TEST_TOOL_ID, False
        )

    @pytest.mark.asyncio
    async def test_premium_toggle_forbidden_for_non_platform_admin(self):
        from src.voice_agents.tool_routes import set_platform_tool_premium

        profile = _make_user_profile(is_org_admin_on=str(TEST_ORG_ID))

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.set_platform_tool_premium = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await set_platform_tool_premium(
                    tool_id=TEST_TOOL_ID,
                    premium_update=self._make_premium_update(is_premium=True),
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 403
            mock_ts.set_platform_tool_premium.assert_not_called()

    @pytest.mark.asyncio
    async def test_premium_toggle_unknown_tool_returns_404(self):
        from src.voice_agents.tool_routes import set_platform_tool_premium

        profile = _make_user_profile(is_platform_admin=True)

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.set_platform_tool_premium = AsyncMock(
                return_value=(None, "Platform tool not found")
            )

            with pytest.raises(HTTPException) as exc_info:
                await set_platform_tool_premium(
                    tool_id=TEST_TOOL_ID,
                    premium_update=self._make_premium_update(is_premium=True),
                    user_data=(TEST_USER_ID, profile),
                )
            assert exc_info.value.status_code == 404
            mock_ts.set_platform_tool_premium.assert_awaited_once_with(
                TEST_TOOL_ID, True
            )
