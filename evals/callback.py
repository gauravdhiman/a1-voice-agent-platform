"""Deterministic human-callback tool evaluation suite."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Iterable
from unittest.mock import patch

from shared.notifications.email_providers import EmailSendResult
from shared.notifications.sms import SmsSendResult
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations import callback_request as tool_module
from shared.voice_agents.tools.implementations.callback_request import (
    CallbackRequestTool,
)

from .core import EvalScenario, EvalStep, SuiteResult, run_suite


@dataclass
class _FakeCallbackProvider:
    """Stateful provider fake that counts only confirmed external writes."""

    outcomes: list[object] = field(default_factory=list)
    messages: list[object] = field(default_factory=list)
    write_count: int = 0

    async def send(self, message: object) -> EmailSendResult:
        """Return the next provider outcome and record the message."""
        self.messages.append(copy.deepcopy(message))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        self.write_count += 1
        return outcome  # type: ignore[return-value]


class _ProviderOutage(Exception):
    """Provider-shaped temporary failure used by the retry scenario."""

    code = 500


class CallbackEvalAdapter:
    """Expose the native callback tool through the generic eval protocol."""

    def __init__(
        self,
        *,
        routes: Iterable[dict[str, Any]] | None = None,
        outcomes: Iterable[object] = (),
        provider_configured: bool = True,
        sms_recipients: Iterable[str] | None = None,
        sms_outcomes: Iterable[object] = (),
        twilio_configured: bool = True,
    ) -> None:
        self.provider = _FakeCallbackProvider(outcomes=list(outcomes))
        self.sms_provider = _FakeCallbackProvider(outcomes=list(sms_outcomes))
        self.provider_configured = provider_configured
        config: dict[str, Any] = {
            "from_email": "noreply@example.com",
            "from_name": "Example Business",
            "routes": (
                list(routes)
                if routes is not None
                else [
                    {
                        "route_id": "owner",
                        "label": "Owner",
                        "recipients": ["owner@example.com"],
                    }
                ]
            ),
        }
        sensitive: dict[str, Any] = {
            "api_key": "eval-key" if provider_configured else None,
        }
        if sms_recipients is not None:
            config["sms_from_number"] = "+14805550100"
            config["sms_recipients"] = list(sms_recipients)
            sensitive["twilio_account_sid"] = "AC123" if twilio_configured else None
            sensitive["twilio_auth_token"] = "eval-token" if twilio_configured else None
        self.tool = CallbackRequestTool(config=config, sensitive_config=sensitive)

    @property
    def provider_write_count(self) -> int:
        """Return confirmed fake-provider writes."""
        return self.provider.write_count

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke the callback function with a trusted session context."""
        function = getattr(self.tool, tool_name)
        with (
            patch.object(
                tool_module, "build_resend_email_provider", return_value=self.provider
            ),
            patch.object(
                tool_module,
                "build_twilio_sms_provider",
                return_value=self.sms_provider,
            ),
        ):
            result = await function(
                context=ToolContext(session_id="eval-session"),
                **arguments,
            )
        return result


def _sms_accepted(message_id: str) -> SmsSendResult:
    """Build a successful fake SMS provider response."""
    return SmsSendResult(provider="twilio", provider_message_id=message_id)


def _accepted(message_id: str) -> EmailSendResult:
    """Build a successful fake provider response."""
    return EmailSendResult(provider="resend", provider_message_id=message_id)


def build_callback_scenarios() -> list[EvalScenario]:
    """Return validation, notification, and failure workflows."""
    return [
        EvalScenario(
            scenario_id="callback.valid_request_notifies_owner",
            description="A confirmed number and reason alerts the owner route.",
            tags=("escalation", "mutation", "idempotency"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Water heater is leaking.",
                        "urgency": "urgent",
                        "caller_name": "Sam",
                    },
                    expected_status="notified",
                    expected_code="callback_notified",
                    expected_fields={
                        "callback_phone": "+14805550100",
                        "urgency": "urgent",
                        "notified": True,
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.invented_number_is_rejected",
            description="Unusable numbers are rejected before provider access.",
            tags=("safety", "validation"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "call me back soon",
                        "reason": "Billing question.",
                    },
                    expected_status="error",
                    expected_code="invalid_argument",
                    expected_fields={
                        "error.field": "callback_phone",
                        "error.next_action": "ask_caller_to_repeat_number_slowly",
                        "error.retryable": False,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.missing_reason_is_rejected",
            description="A callback without a reason cannot alert usefully.",
            tags=("validation", "safety"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={"callback_phone": "+14805550100", "reason": "  "},
                    expected_status="error",
                    expected_code="invalid_argument",
                    expected_fields={
                        "error.field": "reason",
                        "error.next_action": "ask_caller_what_the_callback_is_about",
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.bad_urgency_is_rejected",
            description="Urgency outside the allowlist is rejected explicitly.",
            tags=("validation",),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Pilot light is out.",
                        "urgency": "asap",
                    },
                    expected_status="error",
                    expected_code="invalid_argument",
                    expected_fields={
                        "error.field": "urgency",
                        "error.next_action": "retry_with_corrected_arguments",
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.unconfigured_routes_are_unavailable",
            description="Missing owner routes never produce a false success.",
            tags=("reliability", "configuration"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Billing question.",
                    },
                    expected_status="unavailable",
                    expected_code="owner_route_not_configured",
                    expected_fields={
                        "next_action": "apologize_and_take_a_message_manually",
                        "retryable": False,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.missing_provider_key_is_unavailable",
            description="A missing server key is unavailable, never a false success.",
            tags=("reliability", "configuration"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Billing question.",
                    },
                    expected_status="unavailable",
                    expected_code="organization_provider_not_configured",
                    expected_fields={
                        "next_action": "apologize_and_take_a_message_manually",
                        "retryable": False,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.provider_outage_is_retryable",
            description="A provider outage is safe to retry with idempotency.",
            tags=("reliability", "idempotency"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Billing question.",
                    },
                    expected_status="error",
                    expected_code="provider_rejected",
                    expected_fields={
                        "next_action": "retry_later",
                        "retryable": True,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="callback.sms_only_request_notifies_owner",
            description="An SMS-only attachment alerts the owner with no email.",
            tags=("escalation", "mutation", "sms"),
            steps=(
                EvalStep(
                    step_id="request",
                    tool_name="request_human_callback",
                    arguments={
                        "callback_phone": "+14805550100",
                        "reason": "Water heater is leaking.",
                    },
                    expected_status="notified",
                    expected_code="callback_notified",
                    expected_fields={
                        "notified": True,
                        "notified_channels": ["sms"],
                        "sms_accepted": 1,
                        "accepted_routes": 0,
                    },
                ),
            ),
        ),
    ]


def _scenario_adapter(scenario: EvalScenario) -> CallbackEvalAdapter:
    """Build isolated fake provider state for one named scenario."""
    scenario_id = scenario.scenario_id
    if scenario_id == "callback.unconfigured_routes_are_unavailable":
        return CallbackEvalAdapter(
            routes=[], outcomes=[_accepted("email-1") for _ in range(4)]
        )
    if scenario_id == "callback.missing_provider_key_is_unavailable":
        return CallbackEvalAdapter(
            outcomes=[_accepted("email-1")], provider_configured=False
        )
    if scenario_id == "callback.provider_outage_is_retryable":
        return CallbackEvalAdapter(outcomes=[_ProviderOutage("outage")])
    if scenario_id == "callback.sms_only_request_notifies_owner":
        return CallbackEvalAdapter(
            routes=[],
            provider_configured=False,
            sms_recipients=["+14805550200"],
            sms_outcomes=[_sms_accepted("SM1")],
        )
    return CallbackEvalAdapter(outcomes=[_accepted("email-1")])


async def run_callback_suite(
    scenarios: list[EvalScenario] | None = None,
) -> SuiteResult:
    """Run the callback tool suite with isolated fake provider state."""
    selected = scenarios or build_callback_scenarios()
    return await run_suite(selected, _scenario_adapter)
