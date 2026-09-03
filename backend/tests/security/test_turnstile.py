"""Tests for Cloudflare Turnstile verification (Epic E hardening)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.security.turnstile import is_turnstile_configured, verify_turnstile_token


def _settings_with(secret):
    mock_settings = MagicMock()
    mock_settings.turnstile_secret_key = secret
    return mock_settings


class TestIsTurnstileConfigured:
    def test_requires_a_secret(self):
        """Empty secrets keep verification disabled (local/dev)."""
        with patch("src.security.turnstile.settings", _settings_with(None)):
            assert is_turnstile_configured() is False
        with patch("src.security.turnstile.settings", _settings_with("")):
            assert is_turnstile_configured() is False
        with patch("src.security.turnstile.settings", _settings_with("sx-test")):
            assert is_turnstile_configured() is True


class TestVerifyTurnstileToken:
    @pytest.mark.asyncio
    async def test_unconfigured_always_passes(self):
        """Dev never needs a Cloudflare account; no HTTP is attempted."""
        with patch("src.security.turnstile.settings", _settings_with(None)), patch(
            "src.security.turnstile.httpx"
        ) as mock_httpx:
            assert await verify_turnstile_token(None) is True
            mock_httpx.AsyncClient.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_token_fails_when_configured(self):
        """Bots posting without a token are rejected without HTTP."""
        with patch("src.security.turnstile.settings", _settings_with("sx-test")), patch(
            "src.security.turnstile.httpx"
        ) as mock_httpx:
            assert await verify_turnstile_token(None) is False
            mock_httpx.AsyncClient.assert_not_called()

    @pytest.mark.asyncio
    async def test_cloudflare_success_and_rejection(self):
        """The siteverify verdict decides, including the caller IP."""
        for verdict, expected in ((True, True), (False, False)):
            response = MagicMock()
            response.json = MagicMock(return_value={"success": verdict})
            client = AsyncMock()
            client.post = AsyncMock(return_value=response)
            context = MagicMock()
            context.__aenter__ = AsyncMock(return_value=client)
            context.__aexit__ = AsyncMock(return_value=False)
            with patch(
                "src.security.turnstile.settings", _settings_with("sx-test")
            ), patch(
                "src.security.turnstile.httpx.AsyncClient",
                return_value=context,
            ):
                assert await verify_turnstile_token("tok", "127.0.0.1") is expected
            _, kwargs = client.post.call_args
            assert kwargs["data"]["remoteip"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_transport_failure_fails_closed(self):
        """Timeouts and bad payloads reject rather than admit."""
        with patch("src.security.turnstile.settings", _settings_with("sx-test")), patch(
            "src.security.turnstile.httpx.AsyncClient",
            side_effect=RuntimeError("down"),
        ):
            assert await verify_turnstile_token("tok") is False
