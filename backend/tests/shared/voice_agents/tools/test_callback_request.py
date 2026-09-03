"""Contract tests for the human-callback soft-escalation tool."""

import copy
from typing import Any
from unittest.mock import patch

import pytest

from shared.notifications.email_providers import EmailSendResult
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
