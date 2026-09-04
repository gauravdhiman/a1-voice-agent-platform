"""Native human-callback tool for soft escalation during live calls."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any
from uuid import uuid4

from pydantic import Field, field_validator

from shared.notifications.email_providers import (
    EmailMessage,
    build_resend_email_provider,
)
from shared.notifications.sms import (
    SmsMessage,
    TwilioSmsError,
    build_twilio_sms_provider,
    is_valid_sms_phone,
)
from shared.voice_agents.tools.base.base_tool import (
    BaseConfig,
    BaseSensitiveConfig,
    BaseTool,
    ToolMetadata,
)
from shared.voice_agents.tools.base.tool_context import ToolContext
from shared.voice_agents.tools.implementations.resend_email import ResendEmailRoute

logger = logging.getLogger(__name__)

_PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")
_MAX_REASON_LENGTH = 500
_MAX_NAME_LENGTH = 100
_RESEND_TIMEOUT_SECONDS = 8.0
_SMS_TIMEOUT_SECONDS = 8.0


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
    sms_from_number: str | None = Field(
        default=None,
        max_length=32,
        description=(
            "E.164 sender number for owner SMS alerts (for example "
            "+14805550100). Empty disables the SMS channel."
        ),
    )
    sms_recipients: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Owner mobile numbers alerted by SMS on callback requests, as a "
            "list or comma-separated E.164 text (for example "
            "+14805550200, +14805550300). Empty disables the SMS channel."
        ),
    )

    @field_validator("sms_from_number", mode="before")
    @classmethod
    def normalize_sms_from_number(cls, value: str | None) -> str | None:
        """Normalize the SMS sender, keeping empty as disabled."""
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if not is_valid_sms_phone(normalized):
            raise ValueError(
                "sms_from_number must be an E.164 number like +14805550100"
            )
        return normalized

    @field_validator("sms_recipients", mode="before")
    @classmethod
    def validate_sms_recipients(cls, values: Any) -> list[str]:
        """Normalize SMS recipients and reject undialable entries at save.

        Accepts a list or comma-separated text so the generic dashboard
        text input can save this field without a structured editor.
        """
        if isinstance(values, str):
            items = [item.strip() for item in values.split(",")]
        elif isinstance(values, (list, tuple)):
            items = [str(value).strip() for value in values]
        else:
            raise ValueError("sms_recipients must be a list or comma-separated text")
        normalized = [item for item in items if item]
        for value in normalized:
            if not is_valid_sms_phone(value):
                raise ValueError(
                    f"sms_recipients must contain E.164 numbers: {value!r} is invalid"
                )
        if len(set(normalized)) != len(normalized):
            raise ValueError("sms_recipients must not contain duplicates")
        return normalized


class CallbackRequestTool(BaseTool):
    """Offer a human callback and alert the owner by email and SMS.

    This tool owns exactly one side effect: notifying the configured owner
    destinations through Resend (email) and Twilio (SMS) using the shared
    provider libraries directly. It never invokes another registered tool
    (in particular it never calls ``Resend_email``). Dashboard persistence
    is a separate deterministic step: the voice runtime records accepted
    results through
    ``shared.voice_agents.callback_service.record_callback_tool_outcome``.
    """

    Config = CallbackRequestToolConfig

    class SensitiveConfig(BaseSensitiveConfig):
        """Runtime-only organization credentials injected by voice-ws."""

        api_key: str | None = Field(default=None, repr=False)
        twilio_account_sid: str | None = Field(default=None, repr=False)
        twilio_auth_token: str | None = Field(default=None, repr=False)

    @property
    def metadata(self) -> ToolMetadata:
        """Return the native tool catalog metadata and configuration schema."""
        return ToolMetadata(
            name="Callback_request",
            description=(
                "Offer a human callback when the caller needs a person, then "
                "alert the business owner by email and SMS. Use after "
                "collecting a callback number and a short reason."
            ),
            requires_auth=False,
            config_schema=self.Config.model_json_schema(),
        )

    def check_configuration(self) -> list[str]:
        """Flag missing destinations before any call runs.

        Email gaps are always reported (email is the default channel); SMS
        gaps are reported only when the SMS channel is partially configured
        or malformed, so an email-only attachment stays green.
        """
        issues: list[str] = []
        email_present = bool(self.config.routes) or bool(
            (self.config.from_email or "").strip()
        )
        sms_present = bool(self.config.sms_recipients) or bool(
            (self.config.sms_from_number or "").strip()
        )
        if email_present or not sms_present:
            if not (self.config.from_email or "").strip():
                issues.append("sender email is not set")
            if not self.config.routes:
                issues.append("no owner routes are configured")
        if sms_present:
            if not (self.config.sms_from_number or "").strip():
                issues.append("SMS sender number is not set")
            if not self.config.sms_recipients:
                issues.append("no SMS recipients are configured")
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

        email_channel = bool(self.config.routes)
        sms_channel = bool(self.config.sms_recipients)
        if not email_channel and not sms_channel:
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

        failures: list[str] = []
        accepted_email = 0
        if email_channel:
            accepted_email = await self._notify_email(
                context=context,
                subject=subject,
                body=body,
                normalized_phone=normalized_phone,
                normalized_reason=normalized_reason,
                failures=failures,
            )
            if accepted_email < 0:
                return self._email_unavailable_error(failures)

        accepted_sms = 0
        if sms_channel:
            accepted_sms = await self._notify_sms(
                normalized_phone=normalized_phone,
                normalized_reason=normalized_reason,
                normalized_urgency=normalized_urgency,
                normalized_name=normalized_name,
                failures=failures,
            )
            if accepted_sms < 0:
                return self._error(
                    code="sms_provider_not_configured",
                    message="The SMS provider is not configured for callbacks.",
                    next_action="apologize_and_take_a_message_manually",
                    retryable=False,
                    hint=(
                        "An organization administrator must add the Twilio "
                        "credentials and sender number."
                    ),
                    status="unavailable",
                )

        callback_request_id = str(uuid4())
        if not accepted_email and not accepted_sms:
            return self._error(
                code=failures[0] if failures else "provider_rejected",
                message="The owner could not be alerted.",
                next_action="retry_later",
                retryable=True,
                hint=(
                    "Retry once with the same arguments; if it fails again, "
                    "promise a manual follow-up."
                ),
            )

        notified_channels = [
            channel
            for channel, accepted in (("email", accepted_email), ("sms", accepted_sms))
            if accepted > 0
        ]
        return {
            "status": "notified",
            "code": "callback_notified",
            "message": "The owner has been alerted and will call back.",
            "callback_request_id": callback_request_id,
            "callback_phone": normalized_phone,
            "reason": normalized_reason,
            "urgency": normalized_urgency,
            "notified": True,
            "notified_channels": notified_channels,
            "accepted_routes": accepted_email,
            "sms_accepted": accepted_sms,
        }

    async def _notify_email(
        self,
        *,
        context: ToolContext,
        subject: str,
        body: str,
        normalized_phone: str,
        normalized_reason: str,
        failures: list[str],
    ) -> int:
        """Fan out the email alert; return sends, or -1 when unavailable.

        The -1 sentinel preserves the legacy unavailable errors (missing
        Resend key, sender, or provider build failure) exactly as before.
        """
        api_key = getattr(self.sensitive_config, "api_key", None)
        from_email = self.config.from_email
        if not isinstance(api_key, str) or not api_key.strip():
            failures.append("organization_provider_not_configured")
            return -1
        if not from_email:
            failures.append("sender_not_configured")
            return -1

        try:
            provider = build_resend_email_provider(
                api_key=api_key.strip(),
                default_from_email=from_email,
                default_from_name=self.config.from_name or "",
            )
        except Exception:
            logger.warning("Unable to build Resend provider for callback alert")
            failures.append("provider_not_configured")
            return -1

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
        return accepted

    def _email_unavailable_error(self, failures: list[str]) -> dict[str, Any]:
        """Map the recorded email unavailability to the legacy error shape."""
        reason = failures[-1] if failures else "provider_not_configured"
        if reason == "organization_provider_not_configured":
            return self._error(
                code="organization_provider_not_configured",
                message="This organization has not configured a Resend API key.",
                next_action="apologize_and_take_a_message_manually",
                retryable=False,
                hint="An organization administrator must add the Resend API key.",
                status="unavailable",
            )
        if reason == "sender_not_configured":
            return self._error(
                code="sender_not_configured",
                message="No sender email is configured for callback alerts.",
                next_action="apologize_and_take_a_message_manually",
                retryable=False,
                status="unavailable",
            )
        return self._error(
            code="provider_not_configured",
            message="The email provider is not available.",
            next_action="apologize_and_take_a_message_manually",
            retryable=False,
            status="unavailable",
        )

    async def _notify_sms(
        self,
        *,
        normalized_phone: str,
        normalized_reason: str,
        normalized_urgency: str,
        normalized_name: str | None,
        failures: list[str],
    ) -> int:
        """Fan out the SMS alert; return sends, or -1 when unavailable."""
        account_sid = getattr(self.sensitive_config, "twilio_account_sid", None)
        auth_token = getattr(self.sensitive_config, "twilio_auth_token", None)
        from_number = (self.config.sms_from_number or "").strip()
        if (
            not isinstance(account_sid, str)
            or not account_sid.strip()
            or not isinstance(auth_token, str)
            or not auth_token.strip()
            or not from_number
        ):
            failures.append("sms_provider_not_configured")
            return -1

        try:
            provider = build_twilio_sms_provider(
                account_sid=account_sid.strip(),
                auth_token=auth_token,
                default_from_phone=from_number,
            )
        except Exception:
            logger.warning("Unable to build Twilio provider for callback alert")
            failures.append("sms_provider_not_configured")
            return -1

        prefix = "[URGENT] " if normalized_urgency == "urgent" else ""
        text = f"{prefix}Callback requested: {normalized_phone} — {normalized_reason}"
        if normalized_name:
            text += f" (caller: {normalized_name})"

        accepted = 0
        for recipient in self.config.sms_recipients:
            try:
                await asyncio.wait_for(
                    provider.send(SmsMessage(recipient_phone=recipient, body=text)),
                    timeout=_SMS_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning("Callback SMS timed out recipient redacted")
                failures.append("provider_timeout")
            except TwilioSmsError as exc:
                logger.warning(
                    "Callback SMS rejected code=%s retryable=%s",
                    exc.code,
                    exc.retryable,
                )
                failures.append(
                    "provider_timeout" if exc.retryable else "provider_rejected"
                )
            except Exception as exc:  # noqa: BLE001 - transport errors vary
                logger.warning("Callback SMS failed error_type=%s", type(exc).__name__)
                failures.append("provider_rejected")
            else:
                accepted += 1
        return accepted

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
