"""Tests for provider-neutral OAuth capability metadata and URL validation."""

import pytest

from shared.voice_agents.tools.base.oauth_support import (
    OAuthRefreshMode,
    extract_oauth_client_secret,
    get_oauth_refresh_metadata,
    sanitize_oauth_config,
    validate_oauth_endpoint_url,
)


class TestOAuthRefreshMetadata:
    """OAuth refresh guidance is derived from metadata and live credentials."""

    @pytest.mark.parametrize(
        "config",
        [
            {"provider": "vendor", "token_url": "https://auth.example/token"},
            {
                "provider": "vendor",
                "token_url": "https://auth.example/token",
                "grant_types_supported": ["authorization_code"],
            },
        ],
    )
    def test_unknown_or_non_refresh_provider_is_not_reported_as_automatic(self, config):
        """A missing declaration must not create a false auto-refresh promise."""
        metadata = get_oauth_refresh_metadata(config)

        expected = (
            OAuthRefreshMode.UNKNOWN
            if "grant_types_supported" not in config
            else OAuthRefreshMode.MANUAL
        )
        assert metadata.mode == expected
        assert "re-authenticate" in metadata.message

    def test_refresh_grant_metadata_reports_automatic_support(self):
        """OAuth metadata advertising refresh_token is shown as automatic."""
        metadata = get_oauth_refresh_metadata(
            {
                "provider": "vendor",
                "token_url": "https://auth.example/token",
                "grant_types_supported": ["authorization_code", "refresh_token"],
            }
        )

        assert metadata.mode is OAuthRefreshMode.AUTOMATIC
        assert metadata.manual_reauth_interval_minutes is None

    def test_explicit_manual_mode_includes_admin_interval(self):
        """Providers without refresh support can declare a useful interval."""
        metadata = get_oauth_refresh_metadata(
            {
                "provider": "vendor",
                "token_url": "https://auth.example/token",
                "auto_refresh_supported": False,
                "manual_reauth_interval_minutes": 45,
            }
        )

        assert metadata.mode is OAuthRefreshMode.MANUAL
        assert metadata.manual_reauth_interval_minutes == 45
        assert "45 minutes" in metadata.message

    def test_actual_refresh_token_overrides_unknown_provider_metadata(self):
        """A connected token's refresh-token presence is the source of truth."""
        metadata = get_oauth_refresh_metadata(
            {"provider": "vendor", "token_url": "https://auth.example/token"},
            has_refresh_token=True,
        )

        assert metadata.mode is OAuthRefreshMode.AUTOMATIC
        assert "refresh" in metadata.message.lower()

    def test_missing_refresh_token_requires_manual_reauthentication(self):
        """A successful authorization without a refresh token cannot persist."""
        metadata = get_oauth_refresh_metadata(
            {
                "provider": "vendor",
                "token_url": "https://auth.example/token",
                "grant_types_supported": ["refresh_token"],
            },
            has_refresh_token=False,
        )

        assert metadata.mode is OAuthRefreshMode.MANUAL
        assert "re-authenticate" in metadata.message

    def test_unsupported_client_auth_method_requires_manual_reauthorization(self):
        """Proprietary token endpoint auth cannot be falsely advertised as automatic."""
        metadata = get_oauth_refresh_metadata(
            {
                "provider": "vendor",
                "token_url": "https://auth.example/token",
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "token_endpoint_auth_method": "private_key_jwt",
            },
            has_refresh_token=True,
        )

        assert metadata.mode is OAuthRefreshMode.MANUAL
        assert "client authentication" in metadata.message.lower()

    def test_supported_auth_method_is_selected_from_discovery_capabilities(self):
        """A server-advertised supported method can drive generic refresh."""
        metadata = get_oauth_refresh_metadata(
            {
                "provider": "vendor",
                "token_url": "https://auth.example/token",
                "grant_types_supported": ["refresh_token"],
                "token_endpoint_auth_methods_supported": [
                    "private_key_jwt",
                    "client_secret_basic",
                ],
            },
            has_refresh_token=True,
        )

        assert metadata.mode is OAuthRefreshMode.AUTOMATIC


class TestOAuthConfigSecurity:
    """Public OAuth metadata never contains client secrets or bearer grants."""

    def test_sanitize_oauth_config_removes_credentials(self):
        """Secret grant material is removed before an API response is built."""
        config = {
            "provider": "vendor",
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "client_id": "public-client",
            "client_secret": "do-not-return",
            "access_token": "do-not-return",
            "refresh_token": "do-not-return",
            "code_verifier": "do-not-return",
            "client_assertion": "do-not-return",
            "client_secret_encrypted": "do-not-return",
            "nested": {
                "clientSecret": "do-not-return",
                "authorization_code": "do-not-return",
                "privateKey": "do-not-return",
                "mcp_server_secret_headers": {"X-Api-Key": "do-not-return"},
            },
        }

        sanitized = sanitize_oauth_config(config)

        assert sanitized == {
            "provider": "vendor",
            "auth_url": "https://auth.example/authorize",
            "token_url": "https://auth.example/token",
            "client_id": "public-client",
        }

    def test_extract_oauth_client_secret_supports_nested_legacy_metadata(self):
        """Legacy nested client metadata can be migrated without exposing it."""
        assert (
            extract_oauth_client_secret({"client": {"clientSecret": "legacy-secret"}})
            == "legacy-secret"
        )

    @pytest.mark.parametrize(
        "url",
        [
            "http://auth.example/token",
            "https://user:password@auth.example/token",
            "https://auth.example/token#fragment",
            "http://169.254.169.254/latest/token",
        ],
    )
    def test_oauth_endpoints_reject_insecure_or_ambiguous_urls(self, url):
        """OAuth endpoints cannot downgrade transport or carry userinfo."""
        valid, reason = validate_oauth_endpoint_url(url)

        assert valid is False
        assert reason

    def test_local_http_is_allowed_only_for_loopback_development(self, monkeypatch):
        """Local test providers remain usable without permitting public HTTP."""
        monkeypatch.setenv("MCP_ALLOW_LOCAL_URLS", "true")

        valid, reason = validate_oauth_endpoint_url("http://127.0.0.1:9000/token")

        assert valid is True
        assert reason == ""

    def test_local_http_flag_is_ignored_in_staging(self, monkeypatch):
        """A deployment environment cannot opt production traffic into HTTP."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("MCP_ALLOW_LOCAL_URLS", "true")

        valid, reason = validate_oauth_endpoint_url("http://127.0.0.1:9000/token")

        assert valid is False
        assert "local" in reason.lower() or "https" in reason.lower()

    def test_loopback_http_redirect_can_be_explicitly_enabled_in_staging(
        self, monkeypatch
    ):
        """A local app may receive a browser callback without opening SSRF."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("MCP_ALLOW_LOCAL_URLS", "true")

        valid, reason = validate_oauth_endpoint_url(
            "http://localhost:8000/api/v1/tools/callback",
            allow_loopback_redirect=True,
        )

        assert valid is True
        assert reason == ""

    def test_dns_aware_endpoint_validation_rejects_private_hostname(self, monkeypatch):
        """OAuth metadata cannot hide a private address behind public DNS."""
        monkeypatch.setattr(
            "shared.voice_agents.tools.base.oauth_support._resolve_oauth_host",
            lambda _host: ["10.20.30.40"],
        )

        valid, reason = validate_oauth_endpoint_url(
            "https://auth.example/token",
            resolve_dns=True,
        )

        assert valid is False
        assert "private" in reason.lower() or "blocked" in reason.lower()
