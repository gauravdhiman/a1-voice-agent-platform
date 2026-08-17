"""Tests for the MCP-sourced OAuth path in ``tool_routes.py``.

The legacy ``start_oauth`` / ``oauth_callback`` resolved the tool ONLY through
the platform tool registry (``platform_tool_registry.get_tool_class``), which 404s for
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
import logging
import math
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import quote
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.tool_models import PlatformTool, ToolSource
from shared.voice_agents.tools.base.platform_tool_registry import platform_tool_registry
from shared.voice_agents.tools.mcp.oauth import (
    create_mcp_oauth_state,
    decode_mcp_oauth_state,
)

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


def _generic_mcp_oauth_tool() -> PlatformTool:
    """An MCP tool using the protocol's provider-neutral OAuth metadata."""
    return PlatformTool(
        id=MCP_TOOL_ID,
        name="generic_mcp",
        description="Generic OAuth MCP",
        auth_type="oauth2",
        requires_auth=True,
        auth_config={
            "provider": "mcp",
            "client_id": "mcp-client",
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "scopes": ["tools:read"],
            "resource": "https://mcp.example/mcp",
        },
        is_active=True,
        tool_source=ToolSource.MCP,
        mcp_server_url="https://mcp.example/mcp",
        mcp_server_name="generic-mcp",
        tool_functions_schema=None,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )


def _vendor_labeled_mcp_oauth_tool() -> PlatformTool:
    """An MCP tool whose host metadata names the vendor instead of ``mcp``."""
    tool = _generic_mcp_oauth_tool()
    tool.name = "Linear"
    tool.auth_config = {
        "provider": "linear",
        "client_id": "linear-client",
        "auth_url": "https://mcp.linear.app/oauth/authorize",
        "token_url": "https://mcp.linear.app/oauth/token",
        "resource": "https://mcp.linear.app/mcp",
    }
    tool.mcp_server_url = "https://mcp.linear.app/mcp"
    return tool


def _unknown_native_oauth_tool() -> PlatformTool:
    """A legacy OAuth tool with complete provider metadata in the DB row."""
    return PlatformTool(
        id=LEGACY_TOOL_ID,
        name="Salesforce",
        description="Salesforce OAuth",
        auth_type="oauth2",
        requires_auth=True,
        auth_config={
            "provider": "salesforce",
            "client_id": "salesforce-client",
            "client_secret": "salesforce-secret",
            "redirect_uri": "https://app.example.test/oauth/callback",
            "auth_url": "https://login.salesforce.com/services/oauth2/authorize",
            "token_url": "https://login.salesforce.com/services/oauth2/token",
            "scopes": ["api"],
        },
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
    """Build a signed native OAuth state for callback tests."""
    state_data = {
        "oauth_flow": "native",
        "agent_id": str(TEST_AGENT_ID),
        "tool_name": tool_name,
    }
    return create_mcp_oauth_state(state_data)


def _encode_unsigned_legacy_state(tool_name: str) -> str:
    """Build the pre-hardening unsigned state used by the rejection test."""
    return base64.urlsafe_b64encode(
        json.dumps(
            {
                "agent_id": str(TEST_AGENT_ID),
                "tool_name": tool_name,
            },
            separators=(",", ":"),
        ).encode()
    ).decode()


class TestStartOauthMcp:
    """``GET /api/v1/tools/auth/{tool_name}`` — DB-driven resolution."""

    @pytest.fixture(autouse=True)
    def _agent_permission_context(self, monkeypatch):
        """Keep route unit tests focused on OAuth after the permission guard."""
        from src.voice_agents import tool_routes

        monkeypatch.setenv("MCP_ALLOW_LOCAL_URLS", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        monkeypatch.setattr(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            lambda _host: ["93.184.216.34"],
        )
        monkeypatch.setattr(
            "shared.voice_agents.tools.mcp.security._resolve_host",
            lambda _host: ["93.184.216.34"],
        )
        monkeypatch.setattr(
            tool_routes,
            "validate_mcp_server_url",
            Mock(return_value=(True, "")),
        )
        agent = Mock(organization_id=UUID("00000000-0000-0000-0000-000000000099"))
        monkeypatch.setattr(
            tool_routes.voice_agent_service,
            "get_agent_by_id",
            AsyncMock(return_value=(agent, None)),
        )
        monkeypatch.setattr(tool_routes, "assert_has_permission", Mock())

    @pytest.mark.asyncio
    async def test_native_oauth_uses_signed_state_pkce_and_agent_permission(
        self, monkeypatch
    ):
        """Native and MCP OAuth starts share the same CSRF/PKCE boundary."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        monkeypatch.setenv(
            "SALESFORCE_OAUTH_TOOL_REDIRECT_URI",
            "https://app.example.test/oauth/callback",
        )
        from src.voice_agents.tool_routes import start_oauth

        agent = Mock(organization_id=UUID("00000000-0000-0000-0000-000000000099"))
        with patch(
            "src.voice_agents.tool_routes.voice_agent_service.get_agent_by_id",
            new_callable=AsyncMock,
            return_value=(agent, None),
        ), patch(
            "src.voice_agents.tool_routes.assert_has_permission"
        ) as assert_permission, patch(
            "src.voice_agents.tool_routes.tool_service"
        ) as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_unknown_native_oauth_tool()], None)
            )
            result = await start_oauth(
                tool_name="Salesforce",
                agent_id=TEST_AGENT_ID,
                user_data=(TEST_USER_ID, Mock()),
            )

        assert_permission.assert_called_once()
        assert "code_challenge_method=S256" in result["auth_url"]
        state = result["auth_url"].split("state=", 1)[1].split("&", 1)[0]
        decoded = decode_mcp_oauth_state(state)
        assert decoded["oauth_flow"] == "native"
        assert decoded["provider"] == "salesforce"
        assert decoded["code_verifier"]

    @pytest.mark.asyncio
    async def test_mcp_tool_builds_authorize_url_from_db_auth_config(self, monkeypatch):
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
                platform_tool_registry, "get_tool_class", return_value=None
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
            assert quote(scope, safe="") in auth_url

    @pytest.mark.asyncio
    async def test_mcp_discovery_persists_refresh_metadata_for_future_runs(self):
        """Discovered endpoints/capabilities are saved for the refresh worker."""
        from src.voice_agents import tool_routes

        tool = _generic_mcp_oauth_tool()
        tool.auth_config = {"provider": "mcp"}
        discovered = {
            "provider": "mcp",
            "client_id": "discovered-client",
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "scopes": ["tools:read"],
            "resource": "https://mcp.example/mcp",
            "token_endpoint_auth_method": "none",
            "grant_types_supported": ["authorization_code", "refresh_token"],
        }
        with patch.object(
            tool_routes,
            "discover_mcp_oauth_config",
            new=AsyncMock(return_value=discovered),
        ), patch.object(
            tool_routes.tool_service,
            "get_platform_tools",
            new=AsyncMock(return_value=([tool], None)),
        ) as get_tools, patch.object(
            tool_routes.tool_service,
            "update_platform_tool_oauth_metadata",
            new=AsyncMock(return_value=(True, None)),
        ) as persist_metadata:
            result = await tool_routes._start_mcp_oauth(
                tool.name,
                TEST_AGENT_ID,
                tool.auth_config,
            )

        assert result["auth_url"].startswith("https://auth.example/authorize?")
        get_tools.assert_awaited_once()
        persist_metadata.assert_awaited_once()
        persisted_tool_id, persisted_config = persist_metadata.await_args.args
        assert persisted_tool_id == tool.id
        assert persisted_config["client_id"] == "discovered-client"
        assert persisted_config["oauth_mode"] == "generic"
        assert "client_secret" not in persisted_config

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
                platform_tool_registry, "get_tool_class", return_value=None
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await start_oauth(
                        tool_name="DoesNotExist",
                        agent_id=TEST_AGENT_ID,
                        user_data=(TEST_USER_ID, Mock()),
                    )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_legacy_fallback_when_db_auth_config_missing(self, monkeypatch):
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
                platform_tool_registry,
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

    @pytest.mark.asyncio
    async def test_unknown_native_provider_uses_db_oauth_client_metadata(
        self, monkeypatch
    ):
        """A new native provider need not be added to the central registry."""
        monkeypatch.delenv("GOOGLE_OAUTH_TOOL_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_OAUTH_TOOL_REDIRECT_URI", raising=False)
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_unknown_native_oauth_tool()], None)
            )
            result = await start_oauth(
                tool_name="Salesforce",
                agent_id=TEST_AGENT_ID,
                user_data=(TEST_USER_ID, Mock()),
            )

        assert result["auth_url"].startswith(
            "https://login.salesforce.com/services/oauth2/authorize?"
        )
        assert "client_id=salesforce-client" in result["auth_url"]
        assert (
            "redirect_uri=https%3A%2F%2Fapp.example.test%2Foauth%2Fcallback"
            in result["auth_url"]
        )

    @pytest.mark.asyncio
    async def test_generic_mcp_oauth_uses_pkce_and_resource_indicator(
        self, monkeypatch
    ):
        """Provider-neutral MCP OAuth does not depend on Google env vars."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            result = await start_oauth(
                tool_name="generic_mcp",
                agent_id=TEST_AGENT_ID,
                user_data=(TEST_USER_ID, Mock()),
            )

        assert "code_challenge_method=S256" in result["auth_url"]
        assert "resource=https%3A%2F%2Fmcp.example%2Fmcp" in result["auth_url"]
        state = result["auth_url"].split("state=", 1)[1].split("&", 1)[0]
        decoded = decode_mcp_oauth_state(state)
        assert decoded["tool_name"] == "generic_mcp"
        assert decoded["code_verifier"]

    @pytest.mark.asyncio
    async def test_mcp_oauth_rejects_unsupported_client_auth_before_redirect(self):
        """Admins learn about proprietary client auth before authorizing."""
        from src.voice_agents import tool_routes

        discovered = {
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "client_id": "mcp-client",
            "token_endpoint_auth_method": "private_key_jwt",
            "scopes": [],
        }
        with patch.object(
            tool_routes,
            "discover_mcp_oauth_config",
            new=AsyncMock(return_value=discovered),
        ), patch.object(
            tool_routes.tool_service,
            "get_platform_tools",
            new=AsyncMock(return_value=([_generic_mcp_oauth_tool()], None)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await tool_routes._start_mcp_oauth(
                    "generic_mcp",
                    TEST_AGENT_ID,
                    {"provider": "mcp"},
                )

        assert exc_info.value.status_code == 400
        assert "unsupported" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_mcp_discovery_errors_do_not_return_provider_details(self):
        """OAuth setup errors must not echo provider response data to admins."""
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            with patch(
                "src.voice_agents.tool_routes.discover_mcp_oauth_config",
                new_callable=AsyncMock,
                side_effect=ValueError(
                    "provider response included access_token=should-not-leak"
                ),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await start_oauth(
                        tool_name="generic_mcp",
                        agent_id=TEST_AGENT_ID,
                        user_data=(TEST_USER_ID, Mock()),
                    )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "Could not discover MCP OAuth metadata"
        assert "should-not-leak" not in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_vendor_labeled_mcp_oauth_uses_pkce_without_native_provider_config(
        self, monkeypatch
    ):
        """MCP OAuth does not depend on Linear/Notion being native providers."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        from src.voice_agents.tool_routes import start_oauth

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_vendor_labeled_mcp_oauth_tool()], None)
            )
            result = await start_oauth(
                tool_name="Linear",
                agent_id=TEST_AGENT_ID,
                user_data=(TEST_USER_ID, Mock()),
            )

        assert "code_challenge_method=S256" in result["auth_url"]
        assert "resource=https%3A%2F%2Fmcp.linear.app%2Fmcp" in result["auth_url"]

    @pytest.mark.asyncio
    async def test_platform_mcp_oauth_starts_discovery_only_flow(self, monkeypatch):
        """Platform discovery OAuth state has a tool id but no agent id."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        from src.voice_agents.tool_routes import start_platform_mcp_oauth

        resolved_config = {
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "client_id": "mcp-client",
            "scopes": ["tools:read"],
            "resource": "https://mcp.example/mcp",
        }
        with patch("src.voice_agents.tool_routes.assert_platform_role") as assert_role:
            with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
                mock_ts.get_platform_tools = AsyncMock(
                    return_value=([_generic_mcp_oauth_tool()], None)
                )
                with patch(
                    "src.voice_agents.tool_routes.discover_mcp_oauth_config",
                    new_callable=AsyncMock,
                    return_value=resolved_config,
                ):
                    result = await start_platform_mcp_oauth(
                        tool_id=MCP_TOOL_ID,
                        user_data=(TEST_USER_ID, Mock()),
                    )

        assert_role.assert_called_once()
        assert result["auth_url"].startswith("https://auth.example/authorize?")
        state = result["auth_url"].split("state=", 1)[1].split("&", 1)[0]
        decoded = decode_mcp_oauth_state(state)
        assert decoded["oauth_flow"] == "mcp_platform"
        assert decoded["tool_id"] == str(MCP_TOOL_ID)
        assert "agent_id" not in decoded


class TestOauthCallbackMcp:
    """``GET /api/v1/tools/callback`` — DB-driven resolution + token storage."""

    @pytest.fixture(autouse=True)
    def _oauth_security_context(self, monkeypatch):
        """Configure signed state and local callback URLs for route unit tests."""
        from src.voice_agents import tool_routes

        monkeypatch.setenv("MCP_ALLOW_LOCAL_URLS", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        monkeypatch.setattr(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            lambda _host: ["93.184.216.34"],
        )
        monkeypatch.setattr(
            tool_routes,
            "validate_mcp_server_url",
            Mock(return_value=(True, "")),
        )

    def test_oauth_expiry_falls_back_for_non_finite_provider_values(self):
        """Malformed expiry metadata cannot disable future refresh checks."""
        from src.voice_agents.tool_routes import _oauth_expires_at

        expires_at = _oauth_expires_at("nan")

        assert math.isfinite(expires_at)
        assert expires_at > datetime.now().timestamp()

    @pytest.mark.asyncio
    async def test_callback_rejects_unsigned_legacy_state(self, monkeypatch):
        """Unsigned state must never be accepted as an OAuth grant target."""
        state = _encode_unsigned_legacy_state("generic_mcp")
        from src.voice_agents.tool_routes import oauth_callback

        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(code="auth-code", state=state)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_rejects_unsupported_token_endpoint_auth_method(self):
        """Callbacks never send a client secret using an unsupported scheme."""
        state = create_mcp_oauth_state(
            {
                "oauth_flow": "mcp",
                "agent_id": str(TEST_AGENT_ID),
                "tool_name": "generic_mcp",
                "client_id": "mcp-client",
                "redirect_uri": "http://localhost:8000/api/v1/tools/callback",
                "token_url": "https://auth.example/token",
                "token_endpoint_auth_method": "private_key_jwt",
                "code_verifier": "v" * 43,
            }
        )

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            with patch("httpx.AsyncClient") as mock_client:
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_callback(code="auth-code", state=state)

        assert exc_info.value.status_code == 400
        assert "unsupported" in str(exc_info.value.detail).lower()
        mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_rejects_private_dns_token_endpoint(self, monkeypatch):
        """Authorization-code exchange rechecks token endpoint DNS before POST."""
        monkeypatch.setattr(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            lambda _host: ["10.20.30.40"],
        )
        state = create_mcp_oauth_state(
            {
                "oauth_flow": "mcp",
                "agent_id": str(TEST_AGENT_ID),
                "tool_name": "generic_mcp",
                "client_id": "mcp-client",
                "redirect_uri": "http://localhost:8000/api/v1/tools/callback",
                "token_url": "https://auth.example/token",
                "code_verifier": "v" * 43,
            }
        )

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            with patch("httpx.AsyncClient") as mock_client:
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_callback(code="auth-code", state=state)

        assert exc_info.value.status_code == 400
        assert "private" in str(exc_info.value.detail).lower()
        mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_denial_does_not_log_provider_error_details(self, caplog):
        """Provider-controlled OAuth errors must not become credential-bearing logs."""
        from src.voice_agents.tool_routes import oauth_callback

        caplog.set_level(logging.INFO, logger="src.voice_agents.tool_routes")
        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(
                state="opaque-state",
                error="access_denied&error_description=secret-grant-detail",
            )

        assert exc_info.value.status_code == 400
        assert "secret-grant-detail" not in caplog.text

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
            return_value={
                "access_token": "at-123",
                "refresh_token": "rt-456",
                "expires_in": 3600,
            }
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(return_value=([_mcp_tool()], None))
            mock_ts.configure_agent_tool = AsyncMock(return_value=(None, None))
            with patch.object(
                platform_tool_registry, "get_tool_class", return_value=None
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
    async def test_callback_storage_errors_do_not_log_provider_credentials(
        self, caplog
    ):
        """Persistence failures cannot echo token-bearing database errors."""
        state = create_mcp_oauth_state(
            {
                "oauth_flow": "mcp",
                "agent_id": str(TEST_AGENT_ID),
                "tool_name": "generic_mcp",
                "client_id": "mcp-client",
                "redirect_uri": "http://localhost:8000/api/v1/tools/callback",
                "token_url": "https://auth.example/token",
                "resource": "https://mcp.example/mcp",
                "code_verifier": "v" * 43,
            }
        )
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "access_token": "mcp-at",
                "refresh_token": "mcp-rt",
                "expires_in": 3600,
            }
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        caplog.set_level(logging.ERROR, logger="src.voice_agents.tool_routes")
        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            mock_ts.configure_agent_tool = AsyncMock(
                return_value=(None, "refresh_token=should-not-log")
            )
            with patch(
                "src.voice_agents.tool_routes._discover_and_persist_mcp_tool_catalog",
                new_callable=AsyncMock,
                return_value=0,
            ), patch("httpx.AsyncClient", return_value=mock_client):
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_callback(code="mcp-code", state=state)

        assert exc_info.value.status_code == 500
        assert "should-not-log" not in caplog.text

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
            mock_ts.configure_agent_tool = AsyncMock(return_value=(None, None))
            with patch.object(
                platform_tool_registry, "get_tool_class", return_value=None
            ):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    with pytest.raises(HTTPException) as exc_info:
                        await oauth_callback(code="auth-code", state=state)

        assert exc_info.value.status_code == 404
        # No token exchange, no storage.
        mock_client.post.assert_not_called()
        mock_ts.configure_agent_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_native_callback_uses_db_metadata_for_unknown_provider(
        self, monkeypatch
    ):
        """Authorization-code exchange supports native providers outside the registry."""
        monkeypatch.delenv("SALESFORCE_OAUTH_TOOL_CLIENT_ID", raising=False)
        monkeypatch.setenv("SALESFORCE_OAUTH_TOOL_CLIENT_SECRET", "salesforce-secret")
        monkeypatch.delenv("SALESFORCE_OAUTH_TOOL_REDIRECT_URI", raising=False)
        state = _encode_state("Salesforce")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "access_token": "salesforce-at",
                "refresh_token": "salesforce-rt",
                "expires_in": 3600,
            }
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_unknown_native_oauth_tool()], None)
            )
            mock_ts.configure_agent_tool = AsyncMock(return_value=(None, None))
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await oauth_callback(code="auth-code", state=state)

        assert result == {"message": "Successfully authenticated"}
        request = mock_client.post.await_args
        assert request.kwargs["data"] == {
            "code": "auth-code",
            "redirect_uri": "https://app.example.test/oauth/callback",
            "grant_type": "authorization_code",
            "client_id": "salesforce-client",
            "client_secret": "salesforce-secret",
        }
        create = mock_ts.configure_agent_tool.call_args.args[0]
        assert create.sensitive_config["refresh_token"] == "salesforce-rt"

    @pytest.mark.asyncio
    async def test_native_callback_prefers_per_tool_encrypted_client_secret(
        self, monkeypatch
    ):
        """A shared env secret cannot override a tool-specific confidential client."""
        monkeypatch.setenv("SALESFORCE_OAUTH_TOOL_CLIENT_SECRET", "env-secret")
        state = _encode_state("Salesforce")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "access_token": "salesforce-at",
                "refresh_token": "salesforce-rt",
                "expires_in": 3600,
            }
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_unknown_native_oauth_tool()], None)
            )
            mock_ts.get_platform_tool_oauth_client_secret = AsyncMock(
                return_value=("stored-tool-secret", None)
            )
            mock_ts.configure_agent_tool = AsyncMock(return_value=(None, None))
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await oauth_callback(code="auth-code", state=state)

        assert result == {"message": "Successfully authenticated"}
        assert mock_client.post.await_args.kwargs["data"]["client_secret"] == (
            "stored-tool-secret"
        )

    @pytest.mark.asyncio
    async def test_generic_mcp_oauth_callback_exchanges_pkce_code(self, monkeypatch):
        """MCP OAuth callback stores a token without a provider-specific manager."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        state = create_mcp_oauth_state(
            {
                "oauth_flow": "mcp",
                "agent_id": str(TEST_AGENT_ID),
                "tool_name": "generic_mcp",
                "client_id": "mcp-client",
                "redirect_uri": "http://localhost:8000/api/v1/tools/callback",
                "token_url": "https://auth.example/token",
                "resource": "https://mcp.example/mcp",
                "code_verifier": "v" * 43,
            }
        )
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "access_token": "mcp-at",
                "refresh_token": "mcp-rt",
                "expires_in": "3600",
            }
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            mock_ts.configure_agent_tool = AsyncMock(return_value=(None, None))
            with patch(
                "src.voice_agents.tool_routes._discover_and_persist_mcp_tool_catalog",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_catalog:
                with patch("httpx.AsyncClient", return_value=mock_client):
                    result = await oauth_callback(code="mcp-code", state=state)

        assert result == {"message": "Successfully authenticated"}
        mock_catalog.assert_awaited_once_with("generic_mcp", "mcp-at")

        posted = mock_client.post.await_args.kwargs
        assert posted["data"]["code_verifier"] == "v" * 43
        assert posted["data"]["resource"] == "https://mcp.example/mcp"
        create = mock_ts.configure_agent_tool.call_args.args[0]
        assert create.sensitive_config["access_token"] == "mcp-at"

    @pytest.mark.asyncio
    async def test_platform_oauth_callback_discovers_catalog_without_agent_token_storage(
        self, monkeypatch
    ):
        """Platform OAuth is discovery-only and never creates agent_tools."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        state = create_mcp_oauth_state(
            {
                "oauth_flow": "mcp_platform",
                "tool_name": "generic_mcp",
                "tool_id": str(MCP_TOOL_ID),
                "client_id": "mcp-client",
                "redirect_uri": "http://localhost:8120/api/v1/tools/callback",
                "token_url": "https://auth.example/token",
                "resource": "https://mcp.example/mcp",
                "code_verifier": "v" * 43,
            }
        )
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={"access_token": "platform-at", "expires_in": 3600}
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        from src.voice_agents.tool_routes import oauth_callback

        with patch("src.voice_agents.tool_routes.tool_service") as mock_ts:
            mock_ts.get_platform_tools = AsyncMock(
                return_value=([_generic_mcp_oauth_tool()], None)
            )
            mock_ts.configure_agent_tool = AsyncMock(return_value=(None, None))
            with patch(
                "src.voice_agents.tool_routes._discover_and_persist_mcp_tool_catalog",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_catalog:
                with patch("httpx.AsyncClient", return_value=mock_client):
                    result = await oauth_callback(code="mcp-code", state=state)

        assert result["message"] == "MCP tool catalog discovered"
        assert result["tool_count"] == 0
        mock_catalog.assert_awaited_once_with("generic_mcp", "platform-at")
        mock_ts.configure_agent_tool.assert_not_called()
