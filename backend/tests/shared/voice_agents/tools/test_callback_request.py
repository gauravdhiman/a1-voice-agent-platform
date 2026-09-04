"""Contract tests for the human-callback soft-escalation tool."""

import copy
from typing import Any
from unittest.mock import patch

import pytest

from shared.notifications.email_providers import EmailSendResult
from shared.notifications.sms import SmsSendResult, TwilioSmsError
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations import callback_request as tool_module
from shared.voice_agents.tools.implementations.callback_request import (
    CallbackRequestTool,
    normalize_callback_phone,
)


def _tool(**overrides: Any) -> CallbackRequestTool:
    """Build the tool with an owner route and an org API key."""
    config: dict[str, Any] = {
        "from_email": "noreply@example.com",
        "from_name": "Example Business",
        "routes": [
            {
                "route_id": "owner",
                "label": "Owner",
                "recipients": ["owner@example.com"],
            }
        ],
    }
    config.update(overrides.get("config", {}))
    sensitive = {"api_key": "test-key"}
    sensitive.update(overrides.get("sensitive_config", {}))
    return CallbackRequestTool(config=config, sensitive_config=sensitive)


class _FakeProvider:
    """Provider fake recording messages and replaying outcomes."""

    def __init__(self, results: list[Any]) -> None:
        self.results = list(results)
        self.messages: list[Any] = []

    async def send(self, message: Any) -> Any:
        """Record the message and return the next outcome."""
        self.messages.append(copy.deepcopy(message))
        outcome = self.results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _accepted() -> EmailSendResult:
    """Build a successful fake provider response."""
    return EmailSendResult(provider="resend", provider_message_id="email-1")


class TestNormalizeCallbackPhone:
    def test_formatted_numbers_normalize(self) -> None:
        """Common owner-dictated formats collapse to digits."""
        assert normalize_callback_phone("(480) 555-0100") == "4805550100"
        assert normalize_callback_phone("+1 480-555-0100") == "+14805550100"

    def test_garbage_is_rejected(self) -> None:
        """Non-numbers and wrong types never pass validation."""
        assert normalize_callback_phone("call me back soon") is None
        assert normalize_callback_phone("") is None
        assert normalize_callback_phone(None) is None
        assert normalize_callback_phone(12345) is None


class TestRequestHumanCallback:
    @pytest.mark.asyncio
    async def test_valid_request_alerts_owner_route(self) -> None:
        """An accepted request emails the owner with the callback facts."""
        provider = _FakeProvider(results=[_accepted()])
        with patch.object(
            tool_module, "build_resend_email_provider", return_value=provider
        ):
            result = await _tool().request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Water heater is leaking.",
                urgency="urgent",
                caller_name="Sam",
            )

        assert result["status"] == "notified"
        assert result["callback_phone"] == "+14805550100"
        assert result["urgency"] == "urgent"
        assert result["notified"] is True
        assert result["callback_request_id"]
        assert len(provider.messages) == 1
        sent = provider.messages[0]
        assert sent.recipient_email == "owner@example.com"
        assert "+14805550100" in sent.subject
        assert "URGENT" in sent.subject
        assert "Water heater is leaking." in sent.text_content
        assert sent.idempotency_key is not None

    @pytest.mark.asyncio
    async def test_idempotency_key_is_stable_per_session(self) -> None:
        """Retries of the same session reuse the provider key."""
        provider = _FakeProvider(results=[_accepted(), _accepted()])
        tool = _tool()
        with patch.object(
            tool_module, "build_resend_email_provider", return_value=provider
        ):
            first = await tool.request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
            second = await tool.request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert first["status"] == "notified"
        assert second["status"] == "notified"
        assert (
            provider.messages[0].idempotency_key == provider.messages[1].idempotency_key
        )

    @pytest.mark.asyncio
    async def test_bad_phone_never_reaches_provider(self) -> None:
        """Unusable numbers fail closed with spell-back guidance."""
        provider = _FakeProvider(results=[_accepted()])
        with patch.object(
            tool_module, "build_resend_email_provider", return_value=provider
        ):
            result = await _tool().request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="later today",
                reason="Billing question.",
            )
        assert result["status"] == "error"
        assert result["code"] == "invalid_argument"
        assert result["error"]["field"] == "callback_phone"
        assert provider.messages == []

    @pytest.mark.asyncio
    async def test_missing_config_is_unavailable_not_error(self) -> None:
        """Unconfigured agents degrade to manual follow-up, loudly."""
        provider = _FakeProvider(results=[_accepted()])
        tool = _tool(config={"from_email": "noreply@example.com", "routes": []})
        with patch.object(
            tool_module, "build_resend_email_provider", return_value=provider
        ):
            result = await tool.request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert result["status"] == "unavailable"
        assert result["code"] == "owner_route_not_configured"
        assert provider.messages == []

    @pytest.mark.asyncio
    async def test_provider_outage_is_retryable(self) -> None:
        """A dead provider yields retry guidance, not a false promise."""

        class _Outage(Exception):
            code = 503

        provider = _FakeProvider(results=[_Outage("down")])
        with patch.object(
            tool_module, "build_resend_email_provider", return_value=provider
        ):
            result = await _tool().request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert result["status"] == "error"
        assert result["retryable"] is True
        assert result["next_action"] == "retry_later"

    def test_metadata_advertises_callback_contract(self) -> None:
        """The registry entry names the tool and its schema."""
        metadata = _tool().metadata
        assert metadata.name == "Callback_request"
        assert "callback" in metadata.description.lower()


def _sms_tool(**overrides: Any) -> CallbackRequestTool:
    """Build the tool with an SMS channel and Twilio credentials."""
    config: dict[str, Any] = {
        "sms_from_number": "+14805550100",
        "sms_recipients": ["+14805550200"],
    }
    config.update(overrides.get("config", {}))
    sensitive = {
        "twilio_account_sid": "AC123",
        "twilio_auth_token": "token",
    }
    sensitive.update(overrides.get("sensitive_config", {}))
    return CallbackRequestTool(config=config, sensitive_config=sensitive)


def _sms_accepted() -> SmsSendResult:
    """Build a successful fake SMS provider response."""
    return SmsSendResult(provider="twilio", provider_message_id="SM1")


class TestRequestHumanCallbackSms:
    @pytest.mark.asyncio
    async def test_sms_only_request_notifies_owner(self) -> None:
        """An SMS-only attachment alerts the owner without any email."""
        sms = _FakeProvider(results=[_sms_accepted()])
        with (
            patch.object(tool_module, "build_twilio_sms_provider", return_value=sms),
            patch.object(tool_module, "build_resend_email_provider") as email_build,
        ):
            result = await _sms_tool().request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert result["status"] == "notified"
        assert result["notified_channels"] == ["sms"]
        assert result["sms_accepted"] == 1
        assert result["accepted_routes"] == 0
        assert email_build.call_count == 0
        assert sms.messages[0].recipient_phone == "+14805550200"

    @pytest.mark.asyncio
    async def test_email_and_sms_channels_combine(self) -> None:
        """Both channels fire and both acceptances are reported."""
        email = _FakeProvider(results=[_accepted()])
        sms = _FakeProvider(results=[_sms_accepted()])
        tool = _sms_tool(
            config={
                "from_email": "noreply@example.com",
                "routes": [
                    {
                        "route_id": "owner",
                        "label": "Owner",
                        "recipients": ["owner@example.com"],
                    }
                ],
            },
            sensitive_config={"api_key": "test-key"},
        )
        with (
            patch.object(tool_module, "build_twilio_sms_provider", return_value=sms),
            patch.object(
                tool_module, "build_resend_email_provider", return_value=email
            ),
        ):
            result = await tool.request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert result["status"] == "notified"
        assert result["notified_channels"] == ["email", "sms"]
        assert result["accepted_routes"] == 1
        assert result["sms_accepted"] == 1

    @pytest.mark.asyncio
    async def test_sms_failure_with_email_success_still_notifies(self) -> None:
        """A dead SMS leg does not sink a delivered email alert."""
        email = _FakeProvider(results=[_accepted()])
        sms = _FakeProvider(
            results=[TwilioSmsError("unsubscribed", code=21610, retryable=False)]
        )
        tool = _sms_tool(
            config={
                "from_email": "noreply@example.com",
                "routes": [
                    {
                        "route_id": "owner",
                        "label": "Owner",
                        "recipients": ["owner@example.com"],
                    }
                ],
            },
            sensitive_config={"api_key": "test-key"},
        )
        with (
            patch.object(tool_module, "build_twilio_sms_provider", return_value=sms),
            patch.object(
                tool_module, "build_resend_email_provider", return_value=email
            ),
        ):
            result = await tool.request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert result["status"] == "notified"
        assert result["notified_channels"] == ["email"]
        assert result["sms_accepted"] == 0

    @pytest.mark.asyncio
    async def test_sms_missing_credentials_is_unavailable(self) -> None:
        """SMS recipients without Twilio credentials degrade loudly."""
        sms = _FakeProvider(results=[_sms_accepted()])
        tool = _sms_tool(sensitive_config={"twilio_account_sid": None})
        with patch.object(tool_module, "build_twilio_sms_provider", return_value=sms):
            result = await tool.request_human_callback(
                ToolContext(session_id="call-123"),
                callback_phone="+14805550100",
                reason="Billing question.",
            )
        assert result["status"] == "unavailable"
        assert result["code"] == "sms_provider_not_configured"
        assert sms.messages == []

    def test_invalid_sms_recipient_rejected_at_save(self) -> None:
        """Undialable SMS recipients fail config validation, not at runtime."""
        with pytest.raises(Exception):
            _sms_tool(config={"sms_recipients": ["not-a-number"]})

    def test_comma_separated_sms_recipients_coerce_to_list(self) -> None:
        """The generic drawer text input saves comma-separated numbers."""
        tool = _sms_tool(config={"sms_recipients": "+14805550200, +14805550300"})
        assert tool.config.sms_recipients == ["+14805550200", "+14805550300"]

    def test_check_configuration_flags_sms_gaps(self) -> None:
        """Partial SMS setup is flagged; email-only stays green."""
        assert (
            "SMS sender number is not set"
            in _sms_tool(config={"sms_from_number": None}).check_configuration()
        )
        assert _tool().check_configuration() == []
        assert _sms_tool().check_configuration() == []
