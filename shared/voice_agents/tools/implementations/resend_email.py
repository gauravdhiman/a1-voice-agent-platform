"""Native Resend email tool for organization-configured follow-up routes."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any

from pydantic import Field, field_validator, model_validator

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

logger = logging.getLogger(__name__)

_ROUTE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
_MAX_SUBJECT_LENGTH = 200
_MAX_BODY_LENGTH = 20_000
_MAX_EMAIL_LENGTH = 254
_RESEND_TIMEOUT_SECONDS = 8.0


class ResendEmailRoute(BaseConfig):
    """One logical organization route and its private recipient list."""

    route_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Stable lowercase route key passed to send_resend_email, for "
            "example customer_support or front_desk."
        ),
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable route label shown to the agent when listing routes.",
    )
    recipients: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="One to ten destination email addresses for this route.",
    )

    @field_validator("route_id")
    @classmethod
    def normalize_route_id(cls, value: str) -> str:
        """Normalize route keys and reject values unsafe for model selection."""
        normalized = value.strip().lower()
        if not _ROUTE_ID_PATTERN.fullmatch(normalized):
            raise ValueError(
                "route_id must contain only lowercase letters, numbers, "
                "hyphens, and underscores"
            )
        return normalized

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        """Trim route labels and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("label must not be blank")
        return normalized

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, values: list[str]) -> list[str]:
        """Normalize and validate configured destination addresses."""
        normalized = [value.strip().lower() for value in values]
        if any(len(value) > _MAX_EMAIL_LENGTH for value in normalized):
            raise ValueError(
                f"recipients must contain email addresses of at most {_MAX_EMAIL_LENGTH} characters"
            )
        if any(not _EMAIL_PATTERN.fullmatch(value) for value in normalized):
            raise ValueError("recipients must contain valid email addresses")
        if len(set(normalized)) != len(normalized):
            raise ValueError("recipients must not contain duplicate email addresses")
        return normalized


class ResendEmailToolConfig(BaseConfig):
    """Public per-agent sender and route configuration.

    The Resend API key is organization-owned and injected by the voice runtime
    from encrypted provider credentials. Sender details are non-secret and may
    vary by agent, so they live in this attachment configuration.
    """

    from_email: str | None = Field(
        default=None,
        max_length=254,
        description=(
            "Verified sender email address for this agent. The domain must be "
            "verified in the organization's Resend account."
        ),
    )
    from_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional display name shown in the sender field.",
    )

    routes: list[ResendEmailRoute] = Field(
        default_factory=list,
        max_length=50,
        description=(
            "Logical email routes configured by the organization. The agent "
            "selects a route_id; destination addresses stay out of the model contract."
        ),
    )

    @model_validator(mode="after")
    def validate_unique_route_ids(self) -> "ResendEmailToolConfig":
        """Reject ambiguous route maps before a call can use them."""
        route_ids = [route.route_id for route in self.routes]
        if len(set(route_ids)) != len(route_ids):
            raise ValueError("routes must not contain duplicate route_id values")
        return self

    @field_validator("from_email", mode="before")
    @classmethod
    def normalize_from_email(cls, value: str | None) -> str | None:
        """Normalize an optional sender address and reject malformed values."""
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if not normalized:
            return None
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError(
                "from_email must be a valid email address from a verified domain"
            )
        return normalized

    @field_validator("from_name", mode="before")
    @classmethod
    def normalize_from_name(cls, value: str | None) -> str | None:
        """Trim an optional sender name and reject header-injection characters."""
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if "\r" in normalized or "\n" in normalized:
            raise ValueError("from_name must be a single line")
        return normalized


class ResendEmailTool(BaseTool):
    """Send internal business follow-up emails through configured Resend routes.

    The organization owns the Resend API key. Each agent attachment owns its
    sender identity and route map containing business destinations. This keeps
    credentials and raw recipient addresses out of model-supplied arguments.
    """

    Config = ResendEmailToolConfig

    class SensitiveConfig(BaseSensitiveConfig):
        """Runtime-only organization credential injected by voice-ws."""

        api_key: str | None = Field(default=None, repr=False)

    @property
    def metadata(self) -> ToolMetadata:
        """Return the native tool catalog metadata and configuration schema."""
        return ToolMetadata(
            name="Resend_email",
            description=(
                "Send transactional follow-up emails through organization-configured "
                "Resend routes. The model selects a route, never a raw destination."
            ),
            requires_auth=False,
            config_schema=self.Config.model_json_schema(),
        )

    def _routes(self) -> dict[str, ResendEmailRoute]:
        """Return configured routes indexed for constant-time lookup."""
        return {route.route_id: route for route in self.config.routes}

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

    async def list_resend_email_routes(self, context: ToolContext) -> dict[str, Any]:
        """List configured logical email routes without exposing addresses.

        Description:
            Return the route IDs and labels that this agent may use with
            ``send_resend_email``. Destination email addresses are intentionally
            hidden from the model.

        Args:
            context: Trusted runtime context injected by voice-ws.

        Returns:
            ``status=ok`` with ``routes`` containing ``route_id`` and ``label``.
            An empty list means an administrator must configure this attachment.
        """
        del context
        routes = [
            {"route_id": route.route_id, "label": route.label}
            for route in self.config.routes
        ]
        return {
            "status": "ok",
            "routes": routes,
            "count": len(routes),
            "message": (
                "No email routes are configured for this agent."
                if not routes
                else "Use one of these route IDs with send_resend_email."
            ),
        }

    async def send_resend_email(
        self,
        context: ToolContext,
        route_id: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Send a follow-up email to an administrator-configured route.

        Description:
            Send a plain-text transactional email through Resend to the
            configured recipients for one logical route, such as
            ``customer_support`` or ``front_desk``. The provider's accepted
            result is returned; accepted does not mean the email was delivered
            or read.

        Instructions:
            Call ``list_resend_email_routes`` first when the valid route ID is
            not already known. Pass the exact returned ``route_id`` and never
            invent an address or route. Use this for an organization follow-up
            workflow after collecting the details required by the agent's
            instructions. Do not use Gmail or this tool interchangeably: this
            tool sends to configured business destinations and does not send to
            arbitrary caller-supplied recipients. Do not claim delivery unless
            the result has ``status=accepted``; on ``error`` or ``partial``,
            follow ``error.next_action``.

        Args:
            context: Trusted runtime context containing the call session ID.
            route_id: Exact configured logical route ID, lowercase with hyphens
                or underscores; not an email address.
            subject: Short email subject, one line, maximum 200 characters.
            body: Plain-text email body, maximum 20,000 characters.

        Returns:
            ``status=accepted`` with provider message IDs when all configured
            recipients accepted the email. Recoverable failures include stable
            ``code``, ``error.next_action``, ``retryable``, and the bad field
            when applicable. ``partial`` means some recipients accepted while
            another result is unresolved or rejected.
        """
        if not isinstance(route_id, str):
            return self._error(
                code="invalid_argument",
                message="Email route_id must be text, not an email address object or number.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="route_id",
                expected_format="One of the route_id values returned by list_resend_email_routes",
            )
        if not isinstance(subject, str):
            return self._error(
                code="invalid_argument",
                message="Email subject must be text.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="subject",
                expected_format="Non-empty single-line text up to 200 characters",
            )
        if not isinstance(body, str):
            return self._error(
                code="invalid_argument",
                message="Email body must be text.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="body",
                expected_format="Plain-text body up to 20,000 characters",
            )

        normalized_route_id = route_id.strip().lower()
        route = self._routes().get(normalized_route_id)
        if route is None:
            return self._error(
                code="route_not_configured",
                message="The requested email route is not configured.",
                next_action="list_routes_or_contact_organization_admin",
                retryable=False,
                field="route_id",
                expected_format="One of the route_id values returned by list_resend_email_routes",
                hint="Do not pass a raw email address; select a configured route.",
            )

        normalized_subject = subject.strip()
        if (
            not normalized_subject
            or "\r" in normalized_subject
            or "\n" in normalized_subject
        ):
            return self._error(
                code="invalid_argument",
                message="Email subject must be a non-empty single line.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="subject",
                expected_format="Non-empty single-line text up to 200 characters",
            )
        if len(normalized_subject) > _MAX_SUBJECT_LENGTH:
            return self._error(
                code="invalid_argument",
                message="Email subject is too long.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="subject",
                expected_format="Single-line text up to 200 characters",
            )

        normalized_body = body.strip()
        if not normalized_body:
            return self._error(
                code="invalid_argument",
                message="Email body must not be empty.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="body",
                expected_format="Plain-text body up to 20,000 characters",
            )
        if len(normalized_body) > _MAX_BODY_LENGTH:
            return self._error(
                code="invalid_argument",
                message="Email body is too long.",
                next_action="retry_with_corrected_arguments",
                retryable=False,
                field="body",
                expected_format="Plain-text body up to 20,000 characters",
            )

        api_key = getattr(self.sensitive_config, "api_key", None)
        if not isinstance(api_key, str) or not api_key.strip():
            return self._error(
                code="organization_provider_not_configured",
                message="This organization has not configured a Resend API key.",
                next_action="ask_organization_admin_to_configure_resend",
                retryable=False,
                hint=(
                    "An organization administrator must add the Resend API key "
                    "under Organization credentials."
                ),
                status="unavailable",
            )

        from_email = self.config.from_email
        if not from_email:
            return self._error(
                code="sender_not_configured",
                message="No Resend sender email is configured for this agent.",
                next_action="ask_organization_admin_to_configure_sender",
                retryable=False,
                field="from_email",
                expected_format=(
                    "A verified email address from the organization's Resend domain"
                ),
                status="unavailable",
            )

        try:
            provider = build_resend_email_provider(
                api_key=api_key.strip(),
                default_from_email=from_email,
                default_from_name=self.config.from_name or "",
            )
        except Exception as exc:
            logger.warning(
                "Unable to build Resend provider for route=%s error_type=%s",
                route.route_id,
                type(exc).__name__,
            )
            return self._error(
                code="provider_not_configured",
                message="The Resend email provider is not available.",
                next_action="ask_organization_admin_to_check_resend",
                retryable=False,
                hint="Check the organization API key and verified sender configuration.",
                status="unavailable",
            )

        messages = [
            EmailMessage(
                recipient_email=recipient,
                recipient_name=None,
                subject=normalized_subject,
                html_content="",
                text_content=normalized_body,
                from_email=from_email,
                from_name=self.config.from_name,
                idempotency_key=self._idempotency_key(
                    context,
                    route.route_id,
                    recipient,
                    normalized_subject,
                    normalized_body,
                    index,
                ),
            )
            for index, recipient in enumerate(route.recipients)
        ]
        outcomes = await asyncio.gather(
            *(
                self._send_one_recipient(
                    provider,
                    message,
                    route_id=route.route_id,
                    recipient_index=index,
                )
                for index, message in enumerate(messages)
            )
        )

        provider_message_ids: list[str] = []
        accepted_count = 0
        failures: list[dict[str, Any]] = []
        for result, failure in outcomes:
            if failure is not None:
                failures.append(failure)
                continue
            accepted_count += 1
            provider_message_id = getattr(result, "provider_message_id", None)
            if provider_message_id:
                provider_message_ids.append(provider_message_id)

        if failures:
            status = "partial" if accepted_count else "error"
            failure = failures[0]
            message = (
                "Resend accepted the email for some recipients, but the route "
                "was not fully processed."
                if status == "partial"
                else "Resend did not confirm acceptance of the email."
            )
            return {
                "status": status,
                "code": "partial_delivery" if status == "partial" else failure["code"],
                "message": message,
                "route_id": route.route_id,
                "next_action": failure["next_action"],
                "retryable": failure["retryable"],
                "accepted_count": accepted_count,
                "failed_count": len(route.recipients) - accepted_count,
                "provider_message_ids": provider_message_ids,
                "error": {
                    **failure,
                    "accepted_count": accepted_count,
                    "failed_count": len(route.recipients) - accepted_count,
                },
            }

        return {
            "status": "accepted",
            "code": "email_accepted",
            "message": f"Email accepted by Resend for the {route.label} route.",
            "route_id": route.route_id,
            "accepted_count": len(route.recipients),
            "provider_message_ids": provider_message_ids,
        }

    async def _send_one_recipient(
        self,
        provider: Any,
        message: EmailMessage,
        *,
        route_id: str,
        recipient_index: int,
    ) -> tuple[Any | None, dict[str, Any] | None]:
        """Attempt one recipient without allowing a slow peer to block others."""
        try:
            result = await asyncio.wait_for(
                provider.send(message), timeout=_RESEND_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Resend timed out for route=%s recipient_index=%d",
                route_id,
                recipient_index,
            )
            return None, {
                "code": "provider_timeout",
                "message": "Resend did not respond before the delivery timeout.",
                "retryable": True,
                "next_action": "retry_later",
            }
        except Exception as exc:  # noqa: BLE001 - provider-specific exceptions vary
            logger.warning(
                "Resend failed for route=%s recipient_index=%d error_type=%s",
                route_id,
                recipient_index,
                type(exc).__name__,
            )
            return None, self._provider_failure(exc)
        return result, None

    @staticmethod
    def _idempotency_key(
        context: ToolContext,
        route_id: str,
        recipient: str,
        subject: str,
        body: str,
        index: int,
    ) -> str | None:
        """Build a stable per-session key for safe provider retries."""
        if not context.session_id:
            return None
        payload = "\x1f".join(
            (context.session_id, route_id, recipient, subject, body, str(index))
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"voice-resend-{digest}"

    @staticmethod
    def _provider_failure(exc: Exception) -> dict[str, Any]:
        """Map provider exceptions to safe retry guidance without leaking details."""
        status_code = getattr(exc, "code", getattr(exc, "status_code", None))
        try:
            numeric_code = int(status_code)
        except (TypeError, ValueError):
            numeric_code = None
        if numeric_code in {429} or (numeric_code is not None and numeric_code >= 500):
            return {
                "code": "provider_temporary_failure",
                "message": "Resend temporarily rejected the request.",
                "retryable": True,
                "next_action": "retry_later",
                "hint": "Retry with the same request after a short delay.",
            }
        if numeric_code in {401, 403}:
            return {
                "code": "provider_authentication_failed",
                "message": "Resend rejected the organization email credentials or sender.",
                "retryable": False,
                "next_action": "ask_organization_admin_to_check_resend",
                "hint": "Verify the organization Resend API key and sender domain.",
            }
        if numeric_code is not None and 400 <= numeric_code < 500:
            return {
                "code": "provider_rejected",
                "message": "Resend rejected the email request.",
                "retryable": False,
                "next_action": "ask_organization_admin_to_check_resend",
                "hint": "An organization administrator should inspect the request and sender domain.",
            }
        return {
            "code": "provider_rejected",
            "message": "Resend did not accept the email request.",
            "retryable": not isinstance(exc, (ValueError, TypeError)),
            "next_action": (
                "retry_later"
                if not isinstance(exc, (ValueError, TypeError))
                else "ask_organization_admin_to_check_resend"
            ),
            "hint": (
                "Retry with the same request after a short delay."
                if not isinstance(exc, (ValueError, TypeError))
                else "An organization administrator should inspect the Resend configuration and sender domain."
            ),
        }
