"""Tests for the MCP-sourced OAuth path in ``tool_routes.py``.

The legacy ``start_oauth`` / ``oauth_callback`` resolved the tool ONLY through
the LiveKit registry (``livekit_tool_registry.get_tool_class``), which 404s for
MCP-sourced platform_tools (they have no in-tree ``BaseTool`` subclass). These
tests pin the new DB-driven resolution: the tool's OAuth config is read from the
``platform_tools.auth_config`` column first, with the legacy registry kept as a
fallback so legacy tools are unaffected (RFC §1.1 coexistence).

Contract:
  - ``start_oauth`` for an MCP tool (DB ``auth_config`` present, NOT in the
    registry) → 200 with an authorize URL built from the DB ``auth_config``
    (scopes / auth_url / access_type / prompt); the registry is NOT consulted.
  - ``start_oauth`` for an unknown tool (not in DB, not in registry) → 404.
  - ``start_oauth`` legacy fallback: a tool whose DB row has no ``auth_config``
    but which IS in the registry → uses the registry config (back-compat).
  - ``oauth_callback`` for an MCP tool → exchanges the code (httpx mocked),
    stores ``access_token`` / ``refresh_token`` / ``expires_at`` in
    ``agent_tools.sensitive_config`` via ``configure_agent_tool``, resolving
    ``tool_id`` from the DB row by name; registry NOT consulted.

These exercise the route handlers directly (same pattern as
``test_tool_routes.py``); ``tool_service`` and the registry are patched so no
DB / network is touched.
"""
import base64
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import quote
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.tool_models import PlatformTool, ToolSource
from shared.voice_agents.tools.base.registry_livekit import livekit_tool_registry

# Test fixtures
TEST_AGENT_ID = UUID("00000000-0000-0000-0000-000000000010")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000040")
MCP_TOOL_ID = UUID("00000000-0000-0000-0000-000000000060")
LEGACY_TOOL_ID = UUID("00000000-0000-0000-0000-000000000061")

# Scopes required by Google's official remote Calendar MCP server
# (https://calendarmcp.googleapis.com/mcp/v1), plus the read-write
# ``calendar.events`` scope (superset of ``calendar.events.readonly``) so the
# write tools (create_event / update_event / delete_event) also work.
_MCP_SCOPES = [
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events.freebusy",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

_MCP_AUTH_CONFIG = {
    "provider": "google",
    "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "scopes": _MCP_SCOPES,
    "access_type": "offline",
    "prompt": "consent",
}


def _mcp_tool() -> PlatformTool:
    """An MCP-sourced platform_tools row for Google Calendar (real remote server)."""
    return PlatformTool(
        id=MCP_TOOL_ID,
        name="Google_calendar_mcp",
        description="Google Calendar via MCP",
        auth_type="oauth2",
        requires_auth=True,
        auth_config=_MCP_AUTH_CONFIG,
        is_active=True,
        tool_source=ToolSource.MCP,
        mcp_server_url="https://calendarmcp.googleapis.com/mcp/v1",
        mcp_server_name="google-calendar",
        tool_functions_schema=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


def _legacy_tool_without_db_auth_config() -> PlatformTool:
    """A legacy tool whose DB row has NO auth_config (forces registry fallback)."""
    return PlatformTool(
        id=LEGACY_TOOL_ID,
        name="Gmail",
        description="Gmail (legacy)",
        auth_type="oauth2",
        requires_auth=True,
        auth_config=None,
        is_active=True,
        tool_source=ToolSource.LEGACY,
        tool_functions_schema=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


class _FakeLegacyToolClass:
    """Stand-in for a legacy BaseTool subclass returned by the registry.

    ``start_oauth``/``oauth_callback`` instantiate the class and read
    ``.metadata.auth_config`` (and ``.metadata.requires_auth``). We surface a
    distinct scope (``legacy-scope``) so tests can prove the registry config —
    not the DB row — was used.
    """

    @property
    def metadata(self):
        m = Mock()
        m.requires_auth = True
        m.auth_config = {
            "provider": "google",
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["legacy-scope"],
            "access_type": "offline",
            "prompt": "consent",
        }
        return m


def _encode_state(tool_name: str) -> str:
    """Build the same self-contained base64 state the route builds."""
    state_data = {
        "agent_id": str(TEST_AGENT_ID),
        "tool_name": tool_name,
        "timestamp": datetime.now().isoformat(),
    }
    return base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()


class TestStartOauthMcp:
    """``GET /api/v1/tools/auth/{tool_name}`` — DB-driven resolution."""

    @pytest.mark.asyncio
    async def test_mcp_tool_builds_authorize_url_from_db_auth_config(
        self, monkeypatch
    ):
        """MCP tool (DB auth_config, not in registry) → 200 with DB-derived URL."""
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", "test-client-id")
        monkeypatch.setenv(
            "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
            "http://localhost:8000/api/v1/tools/callback",
        )
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([_mcp_tool()], None))
            with patch.object(
                livekit_tool_registry, "get_tool_class", return_value=None
            ) as mock_reg:
                result = await start_oauth(
                    tool_name="Google_calendar_mcp",
                    agent_id=TEST_AGENT_ID,
                    user_data=(TEST_USER_ID, Mock()),
                )

        # Registry NOT consulted — DB-first resolution.
        mock_reg.assert_not_called()

        auth_url = result["auth_url"]
        assert auth_url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "client_id=test-client-id" in auth_url
        assert "response_type=code" in auth_url
        assert "redirect_uri=" in auth_url
        assert "state=" in auth_url
        # access_type/prompt carried from DB auth_config (needed for refresh_token).
        assert "access_type=offline" in auth_url
        assert "prompt=consent" in auth_url
        # All four MCP scopes are in the requested scope list. Scopes are
        # space-joined then URL-quoted by the route (``:`` -> ``%3A``), so
        # assert the encoded form (``quote`` leaves ``/`` safe by default,
        # matching the route's encoding).
        for scope in _MCP_SCOPES:
            assert quote(scope) in auth_url

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_404(self, monkeypatch):
        """Tool not in DB and not in registry → 404 (not 500)."""
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", "cid")
        monkeypatch.setenv(
            "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
            "http://localhost:8000/api/v1/tools/callback",
        )
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([], None))
            with patch.object(
                livekit_tool_registry, "get_tool_class", return_value=None
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await start_oauth(
                        tool_name="DoesNotExist",
                        agent_id=TEST_AGENT_ID,
                        user_data=(TEST_USER_ID, Mock()),
                    )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_legacy_fallback_when_db_auth_config_missing(
        self, monkeypatch
    ):
        """DB row has no auth_config but registry has the tool → use registry config."""
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", "cid")
        monkeypatch.setenv(
            "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
            "http://localhost:8000/api/v1/tools/callback",
        )
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_legacy_tool_without_db_auth_config()], None)
            )
            with patch.object(
                livekit_tool_registry,
                "get_tool_class",
                return_value=_FakeLegacyToolClass,
            ) as mock_reg:
                result = await start_oauth(
                    tool_name="Gmail",
                    agent_id=TEST_AGENT_ID,
                    user_data=(TEST_USER_ID, Mock()),
                )

        # Registry WAS consulted (fallback) and its scope is in the URL.
        mock_reg.assert_called_once_with("Gmail")
        assert "legacy-scope" in result["auth_url"]


class TestOauthCallbackMcp:
    """``GET /api/v1/tools/callback`` — DB-driven resolution + token storage."""

    @pytest.mark.asyncio
    async def test_mcp_tool_exchanges_and_stores_tokens(self, monkeypatch):
        """Callback for an MCP tool stores tokens in sensitive_config by (agent,tool)."""
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", "cid")
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_SECRET", "csec")
        monkeypatch.setenv(
            "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
            "http://localhost:8000/api/v1/tools/callback",
        )
        state = _encode_state("Google_calendar_mcp")

        # Mock httpx.AsyncClient so no real token exchange happens.
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={"access_token": "at-123", "refresh_token": "rt-456", "expires_in": 3600}
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([_mcp_tool()], None))
            mock_ts.configure_agent_tool = AsyncMock()
            with patch.object(
                livekit_tool_registry, "get_tool_class", return_value=None
            ) as mock_reg:
                with patch("httpx.AsyncClient", return_value=mock_client):
                    result = await oauth_callback(code="auth-code", state=state)

        assert result == {"message": "Successfully authenticated"}
        # Registry NOT consulted — DB-first.
        mock_reg.assert_not_called()
        # Token storage: configure_agent_tool called with the right agent/tool/tokens.
        mock_ts.configure_agent_tool.assert_called_once()
        create = mock_ts.configure_agent_tool.call_args.args[0]
        assert create.agent_id == TEST_AGENT_ID
        assert create.tool_id == MCP_TOOL_ID
        assert create.sensitive_config["access_token"] == "at-123"
        assert create.sensitive_config["refresh_token"] == "rt-456"
        assert "expires_at" in create.sensitive_config
        assert create.is_enabled is True

    @pytest.mark.asyncio
    async def test_callback_unknown_tool_returns_404(self, monkeypatch):
        """Callback for a tool not in DB or registry → 404 before token exchange."""
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", "cid")
        monkeypatch.setenv("GOOGLE_OAUTH_TOOL_CLIENT_SECRET", "csec")
        monkeypatch.setenv(
            "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
            "http://localhost:8000/api/v1/tools/callback",
        )
        state = _encode_state("DoesNotExist")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([], None))
            mock_ts.configure_agent_tool = AsyncMock()
            with patch.object(
                livekit_tool_registry, "get_tool_class", return_value=None
            ):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    with pytest.raises(HTTPException) as exc_info:
                        await oauth_callback(code="auth-code", state=state)

        assert exc_info.value.status_code == 404
        # No token exchange, no storage.
        mock_client.post.assert_not_called()
        mock_ts.configure_agent_tool.assert_not_called()