"""Tests for MCP OAuth metadata, PKCE state, and authorization URL helpers."""

import pytest

from shared.voice_agents.tools.mcp.oauth import (
    build_mcp_authorization_url,
    create_mcp_oauth_state,
    decode_mcp_oauth_state,
    pkce_challenge,
)


class TestMcpOAuthHelpers:
    """MCP OAuth uses provider-neutral PKCE and signed callback state."""

    def test_pkce_challenge_is_base64url_sha256(self):
        verifier = "a" * 43

        challenge = pkce_challenge(verifier)

        assert challenge == "ZtNPunH49FD35FWYhT5Tv8I7vRKQJ8uxMaL0_9eHjNA"

    def test_signed_state_round_trips_and_rejects_tampering(self, monkeypatch):
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

        encoded, signature = state.split(".", 1)
        tampered = f"{encoded[:-1]}{'A' if encoded[-1] != 'A' else 'B'}.{signature}"
        with pytest.raises(ValueError, match="state"):
            decode_mcp_oauth_state(tampered)

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
