"""Tests for MCP OAuth metadata, PKCE state, and authorization URL helpers."""

import base64
from unittest.mock import AsyncMock, Mock, patch

import pytest

from shared.voice_agents.tools.mcp.oauth import (
    build_mcp_authorization_url,
    create_mcp_oauth_state,
    decode_mcp_oauth_state,
    pkce_challenge,
    register_mcp_oauth_client,
)


class TestMcpOAuthHelpers:
    """MCP OAuth uses provider-neutral PKCE and encrypted callback state."""

    @pytest.fixture(autouse=True)
    def allow_test_mcp_host_dns(self, monkeypatch):
        """Keep mocked discovery tests independent of external DNS."""
        monkeypatch.setattr(
            "shared.voice_agents.tools.mcp.security._resolve_host",
            lambda _host: ["93.184.216.34"],
        )

    def test_pkce_challenge_is_base64url_sha256(self):
        verifier = "a" * 43

        challenge = pkce_challenge(verifier)

        assert challenge == "ZtNPunH49FD35FWYhT5Tv8I7vRKQJ8uxMaL0_9eHjNA"

    def test_encrypted_state_round_trips_and_rejects_tampering(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        state = create_mcp_oauth_state(
            {
                "agent_id": "agent-1",
                "tool_name": "calendar",
                "client_id": "client-1",
                "token_url": "https://auth.example/token",
                "resource": "https://calendar.example/mcp",
                "code_verifier": "v" * 43,
            }
        )

        assert decode_mcp_oauth_state(state)["tool_name"] == "calendar"

        tampered = f"{state[:-1]}{'A' if state[-1] != 'A' else 'B'}"
        with pytest.raises(ValueError, match="state"):
            decode_mcp_oauth_state(tampered)

    def test_state_does_not_expose_pkce_verifier_or_payload(self, monkeypatch):
        """The browser-visible state must not reveal the grant verifier."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-state-secret")
        verifier = "v" * 43

        state = create_mcp_oauth_state({"code_verifier": verifier})

        assert verifier not in state
        assert "code_verifier" not in state
        encoded_payload = state.split(".", 1)[0]
        decoded_payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        assert b"code_verifier" not in decoded_payload

    def test_authorization_url_contains_pkce_and_resource_indicators(self):
        url = build_mcp_authorization_url(
            "https://auth.example/authorize",
            client_id="client-1",
            redirect_uri="https://app.example/callback",
            state="signed-state",
            code_challenge="challenge",
            scopes=["calendar.read", "calendar.write"],
            resource="https://calendar.example/mcp",
        )

        assert url.startswith("https://auth.example/authorize?")
        assert "response_type=code" in url
        assert "code_challenge=challenge" in url
        assert "code_challenge_method=S256" in url
        assert "resource=https%3A%2F%2Fcalendar.example%2Fmcp" in url
        assert "scope=calendar.read+calendar.write" in url

    @pytest.mark.asyncio
    async def test_discovery_rejects_private_authorization_server(self):
        """Untrusted MCP metadata must not redirect discovery into private IPs."""
        from shared.voice_agents.tools.mcp import oauth

        protected_response = Mock()
        protected_response.is_success = True
        protected_response.json.return_value = {
            "authorization_servers": ["http://169.254.169.254"]
        }
        client = AsyncMock()
        client.get.return_value = protected_response
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None

        with patch.object(oauth.httpx, "AsyncClient", return_value=client):
            with pytest.raises(ValueError, match="authorization server"):
                await oauth.discover_mcp_oauth_config("https://mcp.example.com/mcp")

        client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discovery_rejects_private_mcp_server_before_metadata_request(
        self, monkeypatch
    ):
        """Discovery itself must enforce the MCP server SSRF boundary."""
        from shared.voice_agents.tools.mcp import oauth

        monkeypatch.setattr(
            "shared.voice_agents.tools.mcp.security._resolve_host",
            lambda _host: ["10.20.30.40"],
        )

        with patch.object(oauth.httpx, "AsyncClient") as async_client:
            with pytest.raises(ValueError, match="blocked"):
                await oauth.discover_mcp_oauth_config("https://mcp.example.com/mcp")

        async_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_discovery_preserves_unsupported_token_auth_method(self, monkeypatch):
        """Unsupported token endpoint auth is surfaced for a manual outcome."""
        from shared.voice_agents.tools.mcp import oauth

        monkeypatch.setattr(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            lambda _host: ["93.184.216.34"],
        )

        protected_response = Mock(is_success=True)
        protected_response.json.return_value = {
            "authorization_servers": ["https://auth.example"],
        }
        metadata_response = Mock(is_success=True)
        metadata_response.json.return_value = {
            "authorization_endpoint": "https://auth.example/authorize",
            "token_endpoint": "https://auth.example/token",
            "token_endpoint_auth_methods_supported": ["private_key_jwt"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
        }
        client = AsyncMock()
        client.get.side_effect = [protected_response, metadata_response]
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None

        with patch.object(oauth.httpx, "AsyncClient", return_value=client):
            config = await oauth.discover_mcp_oauth_config(
                "https://mcp.example.com/mcp"
            )

        assert config["token_endpoint_auth_method"] == "private_key_jwt"
        assert config["token_endpoint_auth_methods_supported"] == ["private_key_jwt"]

    @pytest.mark.asyncio
    async def test_dynamic_registration_rejects_private_endpoint(self, monkeypatch):
        """DCR cannot post a client registration to a private DNS target."""
        from shared.voice_agents.tools.mcp import oauth

        monkeypatch.setattr(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            lambda _host: ["10.20.30.40"],
        )

        with patch.object(oauth.httpx, "AsyncClient") as async_client:
            with pytest.raises(ValueError, match="private"):
                await register_mcp_oauth_client(
                    "https://auth.example/register",
                    redirect_uri="https://app.example/callback",
                )

        async_client.assert_not_called()
