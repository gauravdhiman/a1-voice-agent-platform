"""Native human-callback tool for soft escalation during live calls."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any
from uuid import uuid4

from pydantic import Field

from shared.notifications.email_providers import (
    EmailMessage,
    build_resend_email_provider,
)
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations.resend_email import (
    ResendEmailRoute,
)

logger = logging.getLogger(__name__)

_PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")
_MAX_REASON_LENGTH = 500
_MAX_NAME_LENGTH = 100
_RESEND_TIMEOUT_SECONDS = 8.0


def normalize_callback_phone(value: Any) -> str | None:
    """Normalize a caller-supplied callback number to E.164-ish digits.

    Args:
        value: Raw model-supplied phone value.

    Returns:
        Digits with an optional leading ``+``, or None when unusable.
    """
    if not isinstance(value, str):
        return None
    digits = re.sub(r"[\s\-().]", "", value.strip())
    if not _PHONE_PATTERN.fullmatch(digits):
        return None
    return digits


class CallbackRequestToolConfig(BaseConfig):
    """Owner notification destinations for this agent's callback requests.

    The Resend API key is organization-owned and injected by the voice
    runtime from encrypted provider credentials. Owner destinations live
    in this attachment configuration so the model never sees raw
    addresses; it only supplies the caller's callback number and reason.
    """

    from_email: str | None = Field(
        default=None,
        max_length=254,
        description=(
            "Verified sender email address for callback alerts. The domain "
            "must be verified in the organization's Resend account."
        ),
    )
    from_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional display name shown in the sender field.",
    )
    routes: list[ResendEmailRoute] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Owner routes alerted on callback requests (for example an "
            "owner or front-desk route). The agent does not select a route; "
            "every accepted request notifies all configured routes."
        ),
    )


class CallbackRequestTool(BaseTool):
    """Offer a human callback and alert the owner by email.

    This tool owns exactly one side effect: notifying the configured owner
    routes through Resend using the shared provider library directly. It
    never invokes another registered tool (in particular it never calls
    ``Resend_email``). Dashboard persistence is a separate deterministic
    step: the voice runtime records accepted results through
    ``shared.voice_agents.callback_service.record_callback_tool_outcome``.
    """

    Config = CallbackRequestToolConfig

    class SensitiveConfig(BaseSensitiveConfig):
        """Runtime-only organization credential injected by voice-ws."""

        api_key: str | None = Field(default=None, repr=False)

    @property
    def metadata(self) -> ToolMetadata:
        """Return the native tool catalog metadata and configuration schema."""
        return ToolMetadata(
            name="Callback_request",
            description=(
                "Offer a human callback when the caller needs a person, then "
                "alert the business owner by email. Use after collecting a "
                "callback number and a short reason."
            ),
            requires_auth=False,
            config_schema=self.Config.model_json_schema(),
        )

    def check_configuration(self) -> list[str]:
        """Flag missing sender identity or routes before any call runs."""
        issues: list[str] = []
        if not (self.config.from_email or "").strip():
            issues.append("sender email is not set")
        if not self.config.routes:
            issues.append("no owner routes are configured")
        return issues

    async def request_human_callback(
        self,
        context: ToolContext,
        callback_phone: str,
        reason: str,
        urgency: str = "normal",
        caller_name: str | None = None,
    ) -> dict[str, Any]:
        """Record a callback request and alert the owner by email.

        Description:
            Call this when the caller asks for a person, or when the
            request is beyond what the agent can resolve on the call.
            First offer the callback ("Would you like the owner to call
            you back?"), collect the callback number, and read it back
            digit by digit before calling. Never invent a phone number.

        Instructions:
            Validate the number with the caller before calling: ask them
            to confirm it slowly, and spell back any uncertain digit. Pass
            ``urgency='urgent'`` only when the caller describes harm,
            safety, or time-critical loss (flooding, no heat in freezing
            weather, medical concern); otherwise use ``normal``. Keep
            ``reason`` to one factual sentence. After ``status=notified``,
            tell the caller the owner will call back and end that thread;
            do not keep offering. On ``error`` or ``unavailable``, follow
            ``error.next_action`` and apologize once.

        Args:
            context: Trusted runtime context injected by voice-ws.
            callback_phone: Caller callback number, digits with optional
                leading ``+`` (for example ``+14805550100``).
            reason: One factual sentence: what the callback is about.
            urgency: ``normal`` or ``urgent``.
            caller_name: Caller name when known.

        Returns:
            ``status=notified`` with ``callback_request_id`` when the
            owner routes accepted the alert. Recoverable failures carry a
            stable ``code``, ``error.next_action``, and ``retryable``.
        """
        normalized_phone = normalize_callback_phone(callback_phone)
        if normalized_phone is None:
            return self._error(
                code="invalid_argument",
                message="The callback number is not a callable phone number.",
                next_action="ask_caller_to_repeat_number_slowly",
                retryable=False,
                field="callback_phone",
                expected_format=(
                    "Digits with optional leading +, 7-15 digits "
                    "(for example +14805550100)"
                ),
            )

        normalized_reason = reason.strip() if isinstance(reason, str) else ""
        if not normalized_reason:
            return self._error(
                code="invalid_argument",
                message="A callback reason is required.",
                next_action="ask_caller_what_the_callback_is_about",
                retryable=False,
                field="reason",
                expected_format="One factual sentence, up to 500 characters",
            )
        if len(normalized_reason) > _MAX_REASON_LENGTH:
            return self._error(
                code="invalid_argument",
                message="The callback reason is too long.",
                next_action="summarize_reason_in_one_sentence",
                retryable=False,
                field="reason",
                expected_format="One factual sentence, up to 500 characters",
            )

        normalized_urgency = urgency.strip().lower() if isinstance(urgency, str) else ""
        if normalized_urgency not in ("normal", "urgent"):
            return self._error(
                code="invalid_argument",
                message="Urgency must be normal or urgent.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="urgency",
                expected_format="normal or urgent",
            )

        normalized_name: str | None = None
        if caller_name is not None:
            if not isinstance(caller_name, str) or not caller_name.strip():
                return self._error(
                    code="invalid_argument",
                    message="Caller name must be text when provided.",
                    next_action="retry_with_corrected_arguments",
                    retryable=False,
                    field="caller_name",
                    expected_format=(
                        "Caller name up to 100 characters, or omit the field"
                    ),
                )
            normalized_name = caller_name.strip()[:_MAX_NAME_LENGTH]

        if not self.config.routes:
            return self._error(
                code="owner_route_not_configured",
                message="No owner alert route is configured for callbacks.",
                next_action="apologize_and_take_a_message_manually",
                retryable=False,
                hint=(
                    "An organization administrator must configure "
                    "callback routes for this agent."
                ),
                status="unavailable",
            )

        api_key = getattr(self.sensitive_config, "api_key", None)
        if not isinstance(api_key, str) or not api_key.strip():
            return self._error(
                code="organization_provider_not_configured",
                message="This organization has not configured a Resend API key.",
                next_action="apologize_and_take_a_message_manually",
                retryable=False,
                hint="An organization administrator must add the Resend API key.",
                status="unavailable",
            )

        from_email = self.config.from_email
        if not from_email:
            return self._error(
                code="sender_not_configured",
                message="No sender email is configured for callback alerts.",
                next_action="apologize_and_take_a_message_manually",
                retryable=False,
                status="unavailable",
            )

        subject = (
            f"[URGENT] Callback requested: {normalized_phone}"
            if normalized_urgency == "urgent"
            else f"Callback requested: {normalized_phone}"
        )
        lines = [
            f"Callback number: {normalized_phone}",
            f"Reason: {normalized_reason}",
            f"Urgency: {normalized_urgency}",
        ]
        if normalized_name:
            lines.append(f"Caller name: {normalized_name}")
        if context.session_id:
            lines.append(f"Call session: {context.session_id}")
        body = "\n".join(lines)

        try:
            provider = build_resend_email_provider(
                api_key=api_key.strip(),
                default_from_email=from_email,
                default_from_name=self.config.from_name or "",
            )
        except Exception:
            logger.warning("Unable to build Resend provider for callback alert")
            return self._error(
                code="provider_not_configured",
                message="The email provider is not available.",
                next_action="apologize_and_take_a_message_manually",
                retryable=False,
                status="unavailable",
            )

        failures: list[str] = []
        accepted = 0
        for route in self.config.routes:
            for index, recipient in enumerate(route.recipients):
                message = EmailMessage(
                    recipient_email=recipient,
                    recipient_name=None,
                    subject=subject,
                    html_content="",
                    text_content=body,
                    from_email=from_email,
                    from_name=self.config.from_name,
                    idempotency_key=self._idempotency_key(
                        context, normalized_phone, normalized_reason, index
                    ),
                )
                try:
                    await asyncio.wait_for(
                        provider.send(message),
                        timeout=_RESEND_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.warning("Callback alert timed out route=%s", route.route_id)
                    failures.append("provider_timeout")
                except Exception as exc:  # noqa: BLE001 - provider exceptions vary
                    logger.warning(
                        "Callback alert failed route=%s error_type=%s",
                        route.route_id,
                        type(exc).__name__,
                    )
                    failures.append("provider_rejected")
                else:
                    accepted += 1

        callback_request_id = str(uuid4())
        if not accepted:
            return self._error(
                code=failures[0] if failures else "provider_rejected",
                message="The owner could not be alerted by email.",
                next_action="retry_later",
                retryable=True,
                hint=(
                    "Retry once with the same arguments; if it fails again, "
                    "promise a manual follow-up."
                ),
            )

        return {
            "status": "notified",
            "code": "callback_notified",
            "message": "The owner has been alerted and will call back.",
            "callback_request_id": callback_request_id,
            "callback_phone": normalized_phone,
            "reason": normalized_reason,
            "urgency": normalized_urgency,
            "notified": True,
            "accepted_routes": accepted,
        }

    @staticmethod
    def _error(
        *,
        code: str,
        message: str,
        next_action: str,
        retryable: bool,
        field: str | None = None,
        expected_format: str | None = None,
        hint: str | None = None,
        status: str = "error",
    ) -> dict[str, Any]:
        """Build the stable, actionable error shape supplied to the model."""
        error: dict[str, Any] = {
            "code": code,
            "message": message,
            "next_action": next_action,
            "retryable": retryable,
        }
        if field:
            error["field"] = field
        if expected_format:
            error["expected_format"] = expected_format
        if hint:
            error["hint"] = hint
        return {
            "status": status,
            "code": code,
            "message": message,
            "next_action": next_action,
            "retryable": retryable,
            "error": error,
        }

    @staticmethod
    def _idempotency_key(
        context: ToolContext,
        phone: str,
        reason: str,
        index: int,
    ) -> str | None:
        """Build a stable per-session key for safe provider retries."""
        if not context.session_id:
            return None
        payload = "\x1f".join((context.session_id, phone, reason, str(index)))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"voice-callback-{digest}"


__all__ = [
    "CallbackRequestTool",
    "CallbackRequestToolConfig",
    "normalize_callback_phone",
]
