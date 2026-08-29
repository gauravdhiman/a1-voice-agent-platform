"""Contract tests for the native Resend email tool."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from shared.notifications.email_providers import EmailSendResult
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations import resend_email as tool_module
from shared.voice_agents.tools.implementations.resend_email import (
    ResendEmailTool,
    ResendEmailToolConfig,
)


@dataclass
class _FakeProvider:
    """Capture normalized provider calls without contacting Resend."""

    results: list[EmailSendResult | Exception]
    messages: list[object]

    async def send(self, message: object) -> EmailSendResult:
        """Return the next configured result and retain the message."""
        self.messages.append(message)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _ProviderClientError(Exception):
    """Provider-shaped client rejection used by error classification tests."""

    code = 400


def _tool(api_key: str | None = "re_test") -> ResendEmailTool:
    """Build a tool with two recipients on one logical route."""
    return ResendEmailTool(
        config={
            "from_email": "noreply@example.com",
            "from_name": "Example Business",
            "routes": [
                {
                    "route_id": " Customer_Support ",
                    "label": "Customer Support",
                    "recipients": [
                        "support@example.com",
                        "manager@example.com",
                    ],
                }
            ],
        },
        sensitive_config={"api_key": api_key},
    )


class TestResendEmailTool:
    """Verify routing, validation, idempotency, and safe error results."""

    def test_config_normalizes_route_and_recipient_values(self) -> None:
        """Configuration is canonical before it reaches runtime dispatch."""
        config = ResendEmailToolConfig(
            routes=[
                {
                    "route_id": " Support ",
                    "label": " Support Desk ",
                    "recipients": [" SUPPORT@EXAMPLE.COM "],
                }
            ]
        )

        assert config.routes[0].route_id == "support"
        assert config.routes[0].label == "Support Desk"
        assert config.routes[0].recipients == ["support@example.com"]

    def test_config_normalizes_and_validates_sender_identity(self) -> None:
        """Sender details are validated before an attachment can be saved."""
        config = ResendEmailToolConfig(
            from_email=" NOREPLY@EXAMPLE.COM ",
            from_name=" Example Business ",
        )

        assert config.from_email == "noreply@example.com"
        assert config.from_name == "Example Business"

        with pytest.raises(ValueError, match="from_email"):
            ResendEmailToolConfig(from_email="not-an-email")

    def test_config_rejects_duplicate_route_ids_and_invalid_addresses(self) -> None:
        """Ambiguous or invalid destinations cannot be persisted in a tool config."""
        with pytest.raises(ValueError, match="duplicate route_id"):
            ResendEmailToolConfig(
                routes=[
                    {
                        "route_id": "support",
                        "label": "Support",
                        "recipients": ["support@example.com"],
                    },
                    {
                        "route_id": " SUPPORT ",
                        "label": "Support duplicate",
                        "recipients": ["other@example.com"],
                    },
                ]
            )

        with pytest.raises(ValueError, match="valid email addresses"):
            ResendEmailToolConfig(
                routes=[
                    {
                        "route_id": "support",
                        "label": "Support",
                        "recipients": ["not-an-email"],
                    }
                ]
            )

    @pytest.mark.asyncio
    async def test_list_routes_hides_raw_recipient_addresses(self) -> None:
        """The model can choose a route without learning business addresses."""
        result = await _tool().list_resend_email_routes(ToolContext())

        assert result == {
            "status": "ok",
            "routes": [{"route_id": "customer_support", "label": "Customer Support"}],
            "count": 1,
            "message": "Use one of these route IDs with send_resend_email.",
        }
        assert "support@example.com" not in str(result)

    @pytest.mark.asyncio
    async def test_send_fans_out_to_configured_recipients_with_idempotency_keys(
        self, monkeypatch
    ) -> None:
        """One model request reaches every configured recipient safely."""
        provider = _FakeProvider(
            results=[
                EmailSendResult(provider="resend", provider_message_id="email-1"),
                EmailSendResult(provider="resend", provider_message_id="email-2"),
            ],
            messages=[],
        )
        monkeypatch.setattr(
            tool_module, "build_resend_email_provider", lambda **_: provider
        )
        context = ToolContext(session_id="call-123")

        result = await _tool().send_resend_email(
            context,
            route_id="customer_support",
            subject="Callback requested",
            body="Please call Jane about the estimate.",
        )

        assert result["status"] == "accepted"
        assert result["accepted_count"] == 2
        assert result["provider_message_ids"] == ["email-1", "email-2"]
        assert len(provider.messages) == 2
        assert provider.messages[0].recipient_email == "support@example.com"
        assert provider.messages[1].recipient_email == "manager@example.com"
        assert (
            provider.messages[0].idempotency_key != provider.messages[1].idempotency_key
        )
        assert provider.messages[0].subject == "Callback requested"
        assert provider.messages[0].from_email == "noreply@example.com"
        assert provider.messages[0].from_name == "Example Business"
        assert (
            provider.messages[0].text_content == "Please call Jane about the estimate."
        )

    @pytest.mark.asyncio
    async def test_repeated_request_in_one_session_reuses_idempotency_key(
        self, monkeypatch
    ) -> None:
        """A model retry produces the same provider key for the same operation."""
        provider = _FakeProvider(
            results=[
                EmailSendResult(provider="resend", provider_message_id="email-1"),
                EmailSendResult(provider="resend", provider_message_id="email-2"),
                EmailSendResult(provider="resend", provider_message_id="email-1"),
                EmailSendResult(provider="resend", provider_message_id="email-2"),
            ],
            messages=[],
        )
        monkeypatch.setattr(
            tool_module, "build_resend_email_provider", lambda **_: provider
        )
        context = ToolContext(session_id="call-123")
        tool = _tool()

        await tool.send_resend_email(
            context, "customer_support", "Callback requested", "Please call Jane."
        )
        await tool.send_resend_email(
            context, "customer_support", "Callback requested", "Please call Jane."
        )

        assert (
            provider.messages[0].idempotency_key == provider.messages[2].idempotency_key
        )
        assert (
            provider.messages[1].idempotency_key == provider.messages[3].idempotency_key
        )

    @pytest.mark.asyncio
    async def test_unknown_route_returns_actionable_error_without_provider_call(
        self, monkeypatch
    ) -> None:
        """A raw or misspelled destination is rejected before any send."""
        provider = _FakeProvider(results=[], messages=[])
        monkeypatch.setattr(
            tool_module, "build_resend_email_provider", lambda **_: provider
        )

        result = await _tool().send_resend_email(
            ToolContext(session_id="call-123"),
            route_id="support@example.com",
            subject="Callback",
            body="Please call.",
        )

        assert result["status"] == "error"
        assert result["code"] == "route_not_configured"
        assert result["error"]["field"] == "route_id"
        assert result["error"]["next_action"] == (
            "list_routes_or_contact_organization_admin"
        )
        assert provider.messages == []

    @pytest.mark.asyncio
    async def test_non_text_model_arguments_return_actionable_errors(self) -> None:
        """Malformed model arguments do not escape as generic exceptions."""
        result = await _tool().send_resend_email(
            ToolContext(),
            route_id=None,
            subject="Callback",
            body="Please call.",
        )

        assert result["status"] == "error"
        assert result["code"] == "invalid_argument"
        assert result["error"]["field"] == "route_id"

    @pytest.mark.asyncio
    async def test_missing_provider_configuration_is_explicit(
        self, monkeypatch
    ) -> None:
        """The model receives a safe setup instruction instead of a false success."""
        result = await _tool(api_key=None).send_resend_email(
            ToolContext(), "customer_support", "Callback", "Please call."
        )

        assert result["status"] == "unavailable"
        assert result["code"] == "organization_provider_not_configured"
        assert result["next_action"] == "ask_organization_admin_to_configure_resend"
        assert result["retryable"] is False

    @pytest.mark.asyncio
    async def test_missing_sender_configuration_is_explicit(self) -> None:
        """The tool refuses to send until an agent sender is configured."""
        tool = ResendEmailTool(
            config={
                "routes": [
                    {
                        "route_id": "customer_support",
                        "label": "Customer Support",
                        "recipients": ["support@example.com"],
                    }
                ]
            },
            sensitive_config={"api_key": "re_org_key"},
        )

        result = await tool.send_resend_email(
            ToolContext(), "customer_support", "Callback", "Please call."
        )

        assert result["status"] == "unavailable"
        assert result["code"] == "sender_not_configured"
        assert result["error"]["field"] == "from_email"
        assert result["next_action"] == "ask_organization_admin_to_configure_sender"

    @pytest.mark.asyncio
    async def test_provider_timeout_is_retryable_and_does_not_claim_acceptance(
        self, monkeypatch
    ) -> None:
        """An unknown provider outcome is reported as retryable, not accepted."""

        class SlowProvider:
            async def send(self, message: object) -> EmailSendResult:
                del message
                await asyncio.sleep(0.05)
                return EmailSendResult(provider="resend", provider_message_id="late")

        monkeypatch.setattr(
            tool_module,
            "build_resend_email_provider",
            lambda **_: SlowProvider(),
        )
        monkeypatch.setattr(tool_module, "_RESEND_TIMEOUT_SECONDS", 0.001)

        result = await _tool().send_resend_email(
            ToolContext(session_id="call-123"),
            "customer_support",
            "Callback",
            "Please call.",
        )

        assert result["status"] == "error"
        assert result["code"] == "provider_timeout"
        assert result["retryable"] is True
        assert result["next_action"] == "retry_later"

    @pytest.mark.asyncio
    async def test_partial_result_counts_acceptance_without_provider_message_id(
        self, monkeypatch
    ) -> None:
        """A provider acceptance remains accepted even when its ID is absent."""
        provider = _FakeProvider(
            results=[
                EmailSendResult(provider="resend"),
                RuntimeError("temporary provider failure"),
            ],
            messages=[],
        )
        monkeypatch.setattr(
            tool_module, "build_resend_email_provider", lambda **_: provider
        )

        result = await _tool().send_resend_email(
            ToolContext(session_id="call-123"),
            "customer_support",
            "Callback",
            "Please call.",
        )

        assert result["status"] == "partial"
        assert result["accepted_count"] == 1
        assert result["failed_count"] == 1

    @pytest.mark.asyncio
    async def test_fanout_attempts_other_recipients_after_one_failure(
        self, monkeypatch
    ) -> None:
        """One recipient failure does not suppress independent route recipients."""
        provider = _FakeProvider(
            results=[
                RuntimeError("temporary provider failure"),
                EmailSendResult(provider="resend", provider_message_id="email-2"),
            ],
            messages=[],
        )
        monkeypatch.setattr(
            tool_module, "build_resend_email_provider", lambda **_: provider
        )

        result = await _tool().send_resend_email(
            ToolContext(session_id="call-123"),
            "customer_support",
            "Callback",
            "Please call.",
        )

        assert result["status"] == "partial"
        assert result["accepted_count"] == 1
        assert result["failed_count"] == 1
        assert len(provider.messages) == 2

    def test_provider_client_rejection_is_not_retryable(self) -> None:
        """Provider-side 4xx errors need admin correction, not blind retries."""
        result = ResendEmailTool._provider_failure(_ProviderClientError())

        assert result["code"] == "provider_rejected"
        assert result["retryable"] is False
        assert result["next_action"] == "ask_organization_admin_to_check_resend"
