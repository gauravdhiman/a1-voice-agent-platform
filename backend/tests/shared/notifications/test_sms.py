"""Tests for the shared Twilio SMS provider (no SDK, plain HTTPS)."""

from unittest.mock import patch

import httpx
import pytest

import shared.notifications.sms as sms_module
from shared.notifications.sms import (
    SmsMessage,
    TwilioSmsError,
    TwilioSmsProvider,
    build_twilio_sms_provider,
    is_valid_sms_phone,
)


def _provider(**overrides) -> TwilioSmsProvider:
    params = {
        "account_sid": "AC123",
        "auth_token": "token",
        "default_from_phone": "+14805550100",
    }
    params.update(overrides)
    return build_twilio_sms_provider(**params)


def _ok_response(sid: str = "SM123") -> httpx.Response:
    request = httpx.Request("POST", "https://api.twilio.com/x")
    return httpx.Response(201, json={"sid": sid}, request=request)


def _error_response(status: int, code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://api.twilio.com/x")
    return httpx.Response(
        status, json={"code": code, "message": "provider says no"}, request=request
    )


class TestIsValidSmsPhone:
    def test_accepts_e164_only(self) -> None:
        """Twilio-safe numbers carry a leading + and 7-15 digits."""
        assert is_valid_sms_phone("+14805550100") is True
        assert is_valid_sms_phone("4805550100") is False
        assert is_valid_sms_phone("+1") is False
        assert is_valid_sms_phone(None) is False
        assert is_valid_sms_phone("+14805550100000000") is False


class TestTwilioSmsProvider:
    @pytest.mark.asyncio
    async def test_send_posts_form_with_basic_auth(self) -> None:
        """One SMS is one form POST; the sid is returned."""
        seen: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization", "")
            seen["body"] = request.read().decode()
            return _ok_response("SM999")

        real_client = httpx.AsyncClient

        def fake_client(*args, **kwargs):
            return real_client(transport=httpx.MockTransport(handler))

        with patch.object(sms_module.httpx, "AsyncClient", fake_client):
            result = await _provider().send(
                SmsMessage(recipient_phone="+14805550200", body="Call back soon")
            )

        assert result.provider == "twilio"
        assert result.provider_message_id == "SM999"
        assert "/Accounts/AC123/Messages.json" in seen["url"]
        assert seen["auth"].startswith("Basic ")
        assert "To=%2B14805550200" in seen["body"]
        assert "From=%2B14805550100" in seen["body"]

    @pytest.mark.asyncio
    async def test_missing_credentials_fail_closed(self) -> None:
        """No silent sends without an account, token, and sender."""
        provider = _provider(account_sid="", auth_token=None)
        with pytest.raises(ValueError, match="credentials"):
            await provider.send(SmsMessage(recipient_phone="+14805550200", body="hi"))

    @pytest.mark.asyncio
    async def test_bad_numbers_and_body_fail_closed(self) -> None:
        """Validation happens before any HTTP leaves the process."""
        provider = _provider()
        with pytest.raises(ValueError, match="recipient"):
            await provider.send(SmsMessage(recipient_phone="nope", body="hi"))
        with pytest.raises(ValueError, match="empty"):
            await provider.send(SmsMessage(recipient_phone="+14805550200", body="  "))
        with pytest.raises(ValueError, match="too long"):
            await provider.send(
                SmsMessage(recipient_phone="+14805550200", body="x" * 1601)
            )

    @pytest.mark.asyncio
    async def test_provider_rejections_carry_retry_guidance(self) -> None:
        """Twilio codes map to stable retry decisions without raw payloads."""

        async def run_with_status(status: int, code: int) -> TwilioSmsError:
            async def handler(request: httpx.Request) -> httpx.Response:
                return _error_response(status, code)

            real_client = httpx.AsyncClient

            def fake_client(*args, **kwargs):
                return real_client(transport=httpx.MockTransport(handler))

            with patch.object(sms_module.httpx, "AsyncClient", fake_client):
                with pytest.raises(TwilioSmsError) as exc_info:
                    await _provider().send(
                        SmsMessage(recipient_phone="+14805550200", body="hi")
                    )
                return exc_info.value

        unsubscribed = await run_with_status(400, 21610)
        assert unsubscribed.retryable is False
        assert unsubscribed.code == 21610

        rate_limited = await run_with_status(429, 20429)
        assert rate_limited.retryable is True

        auth_failed = await run_with_status(401, 20003)
        assert auth_failed.retryable is False
