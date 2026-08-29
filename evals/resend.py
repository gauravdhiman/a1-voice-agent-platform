"""Deterministic Resend email tool evaluation suite."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from typing import Any, Iterable
from unittest.mock import patch

from shared.notifications.email_providers import EmailSendResult
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations import resend_email as tool_module
from shared.voice_agents.tools.implementations.resend_email import ResendEmailTool

from .core import EvalAdapter, EvalScenario, EvalStep, SuiteResult, run_suite


@dataclass
class _FakeResendProvider:
    """Stateful provider fake that counts only confirmed external writes."""

    outcomes: list[object]
    messages: list[object]
    write_count: int = 0

    async def send(self, message: object) -> EmailSendResult:
        """Return the next provider outcome and record the normalized message."""
        self.messages.append(copy.deepcopy(message))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        self.write_count += 1
        return outcome  # type: ignore[return-value]


class _RateLimitError(Exception):
    """Provider-shaped temporary failure used by the retry scenario."""

    code = 429


class ResendEvalAdapter:
    """Expose the native Resend tool through the generic eval protocol."""

    def __init__(
        self,
        *,
        routes: Iterable[dict[str, Any]] = (),
        outcomes: Iterable[object] = (),
        provider_configured: bool = True,
        timeout_seconds: float | None = None,
    ) -> None:
        self.provider = _FakeResendProvider(
            outcomes=list(outcomes),
            messages=[],
        )
        self.provider_configured = provider_configured
        self.timeout_seconds = timeout_seconds
        self.tool = ResendEmailTool(
            config={
                "from_email": "noreply@example.com",
                "from_name": "Example Business",
                "routes": list(routes),
            },
            sensitive_config={
                "api_key": "eval-key" if provider_configured else None,
            },
        )

    @property
    def provider_write_count(self) -> int:
        """Return confirmed fake-provider writes."""
        return self.provider.write_count

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one public tool function with a trusted session context."""
        function = getattr(self.tool, tool_name)
        with patch.object(
            tool_module, "build_resend_email_provider", return_value=self.provider
        ):
            timeout_patch = (
                patch.object(
                    tool_module,
                    "_RESEND_TIMEOUT_SECONDS",
                    self.timeout_seconds,
                )
                if self.timeout_seconds is not None
                else patch.object(tool_module, "_RESEND_TIMEOUT_SECONDS", 8.0)
            )
            with timeout_patch:
                result = await function(
                    context=ToolContext(session_id="eval-session"),
                    **arguments,
                )
        return result


def _accepted(message_id: str) -> EmailSendResult:
    """Build a successful fake provider response."""
    return EmailSendResult(provider="resend", provider_message_id=message_id)


def _routes() -> list[dict[str, Any]]:
    """Return the organization route fixture used by send scenarios."""
    return [
        {
            "route_id": "customer_support",
            "label": "Customer Support",
            "recipients": ["support@example.com", "manager@example.com"],
        }
    ]


def build_resend_scenarios() -> list[EvalScenario]:
    """Return critical route, delivery, validation, and failure workflows."""
    return [
        EvalScenario(
            scenario_id="resend.route_catalog_hides_recipients",
            description="The model can discover routes without recipient PII.",
            tags=("routing", "privacy"),
            steps=(
                EvalStep(
                    step_id="list_routes",
                    tool_name="list_resend_email_routes",
                    expected_status="ok",
                    expected_fields={
                        "routes": [
                            {
                                "route_id": "customer_support",
                                "label": "Customer Support",
                            }
                        ],
                        "count": 1,
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="resend.send_configured_route",
            description="A route selection sends to every configured recipient.",
            tags=("routing", "mutation", "idempotency"),
            steps=(
                EvalStep(
                    step_id="send",
                    tool_name="send_resend_email",
                    arguments={
                        "route_id": "customer_support",
                        "subject": "Callback requested",
                        "body": "Please call the customer.",
                    },
                    expected_status="accepted",
                    expected_fields={
                        "route_id": "customer_support",
                        "accepted_count": 2,
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="resend.raw_recipient_is_rejected",
            description="The model cannot bypass configured routes with a raw address.",
            tags=("safety", "routing", "validation"),
            steps=(
                EvalStep(
                    step_id="send",
                    tool_name="send_resend_email",
                    arguments={
                        "route_id": "support@example.com",
                        "subject": "Callback requested",
                        "body": "Please call the customer.",
                    },
                    expected_status="error",
                    expected_code="route_not_configured",
                    expected_fields={
                        "error.field": "route_id",
                        "error.next_action": "list_routes_or_contact_organization_admin",
                        "error.retryable": False,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="resend.provider_configuration_is_explicit",
            description="A missing server key is unavailable, never a false success.",
            tags=("reliability", "configuration"),
            steps=(
                EvalStep(
                    step_id="send",
                    tool_name="send_resend_email",
                    arguments={
                        "route_id": "customer_support",
                        "subject": "Callback requested",
                        "body": "Please call the customer.",
                    },
                    expected_status="unavailable",
                    expected_code="organization_provider_not_configured",
                    expected_fields={
                        "next_action": "ask_organization_admin_to_configure_resend",
                        "retryable": False,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="resend.partial_delivery_is_explicit",
            description="A fan-out failure reports partial progress and retry guidance.",
            tags=("reliability", "partial-delivery", "idempotency"),
            steps=(
                EvalStep(
                    step_id="send",
                    tool_name="send_resend_email",
                    arguments={
                        "route_id": "customer_support",
                        "subject": "Callback requested",
                        "body": "Please call the customer.",
                    },
                    expected_status="partial",
                    expected_code="partial_delivery",
                    expected_fields={
                        "accepted_count": 1,
                        "failed_count": 1,
                        "error.next_action": "retry_later",
                        "error.retryable": True,
                    },
                ),
            ),
        ),
        EvalScenario(
            scenario_id="resend.invalid_subject_is_rejected",
            description="Invalid model arguments are rejected before provider access.",
            tags=("validation", "safety"),
            steps=(
                EvalStep(
                    step_id="send",
                    tool_name="send_resend_email",
                    arguments={
                        "route_id": "customer_support",
                        "subject": "line one\nline two",
                        "body": "Please call the customer.",
                    },
                    expected_status="error",
                    expected_code="invalid_argument",
                    expected_fields={
                        "error.field": "subject",
                        "error.next_action": "retry_with_corrected_arguments",
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
        EvalScenario(
            scenario_id="resend.timeout_is_retryable",
            description="An unknown provider outcome is safe to retry with idempotency.",
            tags=("reliability", "timeout", "idempotency"),
            steps=(
                EvalStep(
                    step_id="send",
                    tool_name="send_resend_email",
                    arguments={
                        "route_id": "customer_support",
                        "subject": "Callback requested",
                        "body": "Please call the customer.",
                    },
                    expected_status="error",
                    expected_code="provider_timeout",
                    expected_fields={
                        "next_action": "retry_later",
                        "retryable": True,
                    },
                    assert_no_provider_write=True,
                ),
            ),
        ),
    ]


def _scenario_adapter(scenario: EvalScenario) -> ResendEvalAdapter:
    """Build isolated fake provider state for one named scenario."""
    scenario_id = scenario.scenario_id
    if scenario_id == "resend.provider_configuration_is_explicit":
        return ResendEvalAdapter(routes=_routes(), provider_configured=False)
    if scenario_id == "resend.partial_delivery_is_explicit":
        return ResendEvalAdapter(
            routes=_routes(),
            outcomes=[_accepted("email-1"), _RateLimitError("rate limited")],
        )
    if scenario_id == "resend.timeout_is_retryable":

        class SlowProvider(_FakeResendProvider):
            async def send(self, message: object) -> EmailSendResult:
                del message
                await asyncio.sleep(0.05)
                return _accepted("late")

        adapter = ResendEvalAdapter(
            routes=_routes(),
            timeout_seconds=0.001,
        )
        adapter.provider = SlowProvider(outcomes=[], messages=[])
        return adapter
    return ResendEvalAdapter(
        routes=_routes(),
        outcomes=[_accepted("email-1"), _accepted("email-2")],
    )


async def run_resend_suite(
    scenarios: list[EvalScenario] | None = None,
) -> SuiteResult:
    """Run the Resend tool suite with isolated fake provider state."""
    selected = scenarios or build_resend_scenarios()
    return await run_suite(selected, _scenario_adapter)
