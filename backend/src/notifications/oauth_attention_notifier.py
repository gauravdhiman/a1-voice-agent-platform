"""Notifications for OAuth connections that require administrator action.

The token refresh worker owns the decision that a connection cannot be renewed
automatically. This module owns the delivery concern: resolve the organization
admins, construct a safe message, and hand it to the existing durable
notification service. Credential values are intentionally never copied into a
notification request.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional
from uuid import UUID

from src.notifications.models import SendNotificationRequest
from src.notifications.oauth_attention_outbox import oauth_attention_outbox
from src.notifications.platform_settings_service import (
    platform_notification_settings_service,
)
from src.notifications.service import notification_service
from src.rbac.user_roles.service import user_role_service as default_user_role_service

from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)

OAUTH_ATTENTION_EVENT_KEY = "tools.oauth_reauthorization_required"


class OAuthAttentionNotificationPhase(str, Enum):
    """Stable notification phases used for idempotent OAuth reminders."""

    EXPIRING = "expiring"
    EXPIRED = "expired"
    ACTION_REQUIRED = "action_required"


@dataclass
class OAuthAttentionNotificationResult:
    """Delivery counters returned after notifying organization administrators."""

    sent: int = 0
    failed: int = 0
    skipped: int = 0


class OAuthAttentionNotifier:
    """Deliver safe OAuth renewal reminders to organization administrators.

    The notifier deliberately reuses :class:`NotificationService` rather than
    sending email directly. That gives OAuth reminders the existing event
    enable/disable switch, notification log, stable idempotency key, provider
    adapter, and retry scheduler.

    Recipient policy:
        Every organization administrator receives an email. The configured
        platform administrator receives email plus the platform Telegram chat
        and optional SMS destination. Tenant details are included only in the
        explicit platform alert so support can diagnose the connection.

    Security:
        Access tokens, refresh tokens, client secrets, endpoint URLs, and
        provider error responses are never included in template variables or
        idempotency keys. Only display metadata needed to reconnect the tool is
        sent.
    """

    def __init__(
        self,
        notification_sender: Any = None,
        user_role_service: Any = None,
        organization_name_resolver: Optional[Callable[[UUID], Awaitable[str]]] = None,
        platform_settings_service: Any = None,
        platform_channel_outbox: Any = None,
    ) -> None:
        """Initialize the notifier with replaceable delivery dependencies.

        Args:
            notification_sender: Object exposing ``send_notification``. Defaults
                to the process-wide durable notification service.
            user_role_service: Object exposing
                ``get_users_by_organization``. Defaults to the shared RBAC
                service.
            organization_name_resolver: Optional async resolver used to label
                the email. The production default reads the organization name
                through the service-role Supabase client.
        """
        self.notification_sender = notification_sender or notification_service
        self.user_role_service = user_role_service or default_user_role_service
        self.organization_name_resolver = (
            organization_name_resolver or self._get_organization_name
        )
        self.platform_settings_service = (
            platform_settings_service or platform_notification_settings_service
        )
        self.platform_channel_outbox = platform_channel_outbox or oauth_attention_outbox
        self._organization_name_cache: Dict[UUID, str] = {}

    async def notify(
        self,
        agent_tool: Any,
        *,
        phase: OAuthAttentionNotificationPhase,
        minutes_until_expiry: Optional[float],
        reason: str,
        immediate: bool = False,
    ) -> OAuthAttentionNotificationResult:
        """Notify organization admins and configured platform channels.

        Args:
            agent_tool: Internal agent-tool context containing the agent,
                organization, tool name, and encrypted-state-derived expiry.
                The encrypted state itself is never sent.
            phase: ``EXPIRING`` for the configured warning window or ``EXPIRED``
                after the access token expiry time has passed.
            minutes_until_expiry: Approximate minutes remaining; negative values
                represent minutes since expiry.
            reason: Safe, platform-generated explanation of why automatic
                renewal is unavailable or has failed.

            immediate: Whether the stored connection state is unusable or its
                refresh outcome is ambiguous and needs prompt remediation.

        Returns:
            Counters describing successful, failed, and skipped deliveries.

        Raises:
            No delivery exception is propagated for an individual recipient.
                The existing notification retry scheduler can retry failures
                recorded by ``NotificationService``.
        """
        result = OAuthAttentionNotificationResult()
        organization_id = getattr(agent_tool, "organization_id", None)
        organization_name = "your organization"
        if organization_id:
            try:
                organization_name = await self.organization_name_resolver(
                    organization_id
                )
            except Exception:
                logger.warning(
                    "Could not resolve organization name for OAuth attention notice",
                    exc_info=True,
                )
        sensitive_config = getattr(agent_tool, "sensitive_config", None) or {}
        expires_at = self._safe_expiry(sensitive_config.get("expires_at"))
        expiry_key = str(int(expires_at)) if expires_at is not None else "unknown"
        phase_key = phase.value if isinstance(phase, Enum) else str(phase)
        status_text = (
            "requires immediate administrator action"
            if immediate
            else self._status_text(phase, minutes_until_expiry)
        )
        expires_text = self._expires_text(expires_at)
        tool_name = self._tool_name(agent_tool)
        agent_name = getattr(agent_tool, "agent_name", None) or str(
            getattr(agent_tool, "agent_id", "the agent")
        )
        action_url = (
            f"{settings.app_base_url.rstrip('/')}/agents/"
            f"{getattr(agent_tool, 'agent_id', '')}?tab=tools"
        )
        credential_version = int(getattr(agent_tool, "oauth_credential_version", 0))
        event_code = str(
            getattr(agent_tool, "oauth_refresh_error_code", None)
            or ("action_required" if immediate else phase_key)
        )
        event_key = (
            f"oauth-attention:{agent_tool.id}:v{credential_version}:"
            f"{event_code}:{expiry_key}"
        )
        template_variables = {
            "user_name": "there",
            "tool_name": tool_name,
            "agent_name": agent_name,
            "organization_name": organization_name,
            "status_text": status_text,
            "expires_at": expires_text,
            "reason": reason,
            "action_url": action_url,
            "app_name": settings.app_name,
        }

        if organization_id:
            try:
                members, _ = await self.user_role_service.get_users_by_organization(
                    organization_id
                )
            except Exception:
                logger.exception(
                    "Could not resolve organization admins for OAuth attention notice"
                )
                members = []

            admins = [
                member
                for member in members or []
                if any(
                    getattr(role, "name", None) == "org_admin"
                    for role in getattr(member, "roles", [])
                )
            ]
            if not admins:
                result.skipped += 1
            for member in admins:
                recipient_name = self._member_name(member)
                try:
                    request = SendNotificationRequest(
                        event_key=OAUTH_ATTENTION_EVENT_KEY,
                        recipient_email=member.email,
                        recipient_name=recipient_name,
                        organization_id=organization_id,
                        user_id=member.id,
                        template_variables={
                            **template_variables,
                            "user_name": recipient_name or "there",
                        },
                        idempotency_key=f"{event_key}:org:{member.id}",
                    )
                    delivery = await self.notification_sender.send_notification(request)
                    if delivery and delivery.success:
                        result.sent += 1
                    else:
                        result.failed += 1
                except Exception:
                    result.failed += 1
                    logger.exception(
                        "Failed to send OAuth attention notice to an organization admin"
                    )
        else:
            result.skipped += 1

        try:
            platform_email = (
                await self.platform_settings_service.get_platform_admin_email()
            )
        except Exception:
            platform_email = None
            result.failed += 1
            logger.exception("Could not load the platform OAuth alert email")
        if platform_email:
            try:
                delivery = await self.notification_sender.send_notification(
                    SendNotificationRequest(
                        event_key=OAUTH_ATTENTION_EVENT_KEY,
                        recipient_email=platform_email,
                        recipient_name="Platform administrator",
                        organization_id=organization_id,
                        template_variables=template_variables,
                        idempotency_key=f"{event_key}:platform-email:{platform_email}",
                    )
                )
                if delivery and delivery.success:
                    result.sent += 1
                else:
                    result.failed += 1
            except Exception:
                result.failed += 1
                logger.exception(
                    "Failed to send OAuth attention notice to platform admin"
                )
        else:
            result.skipped += 1

        if organization_id:
            try:
                await self.platform_channel_outbox.enqueue(
                    event_key=event_key,
                    agent_tool_id=str(agent_tool.id),
                    organization_id=str(organization_id),
                    payload={
                        "organization_name": organization_name,
                        "agent_name": agent_name,
                        "tool_name": tool_name,
                        "status_text": status_text,
                        "expires_at": expires_text,
                        "reason": reason,
                        "action_url": action_url,
                    },
                )
            except Exception:
                result.failed += 1
                logger.exception("Could not enqueue OAuth platform-channel alert")

        return result

    async def _get_organization_name(self, organization_id: UUID) -> str:
        """Read and cache a safe display name for an organization."""
        cached = self._organization_name_cache.get(organization_id)
        if cached:
            return cached

        client = supabase_config.service_client
        if client is None:
            return "your organization"
        response = (
            client.table("organizations")
            .select("name")
            .eq("id", str(organization_id))
            .limit(1)
            .execute()
        )
        rows = response.data if isinstance(response.data, list) else []
        name = (
            str(rows[0].get("name") or "your organization")
            if rows
            else "your organization"
        )
        self._organization_name_cache[organization_id] = name
        return name

    @staticmethod
    def _tool_name(agent_tool: Any) -> str:
        """Return a safe display name for an internal tool context."""
        tool = getattr(agent_tool, "tool", None)
        return str(getattr(tool, "name", None) or "Connected tool")

    @staticmethod
    def _member_name(member: Any) -> str:
        """Build a recipient display name without requiring profile fields."""
        return " ".join(
            part
            for part in (
                getattr(member, "first_name", ""),
                getattr(member, "last_name", ""),
            )
            if part
        ).strip()

    @staticmethod
    def _safe_expiry(value: Any) -> Optional[float]:
        """Parse finite expiry metadata without exposing malformed values."""
        try:
            parsed = float(value)
            return parsed if math.isfinite(parsed) else None
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _expires_text(expires_at: Optional[float]) -> str:
        """Format expiry metadata for people rather than machines."""
        if expires_at is None:
            return "Unknown"
        try:
            return datetime.fromtimestamp(expires_at, timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        except (OverflowError, OSError, ValueError):
            return "Unknown"

    @staticmethod
    def _status_text(
        phase: OAuthAttentionNotificationPhase,
        minutes_until_expiry: Optional[float],
    ) -> str:
        """Return the human-readable status sentence fragment."""
        if phase == OAuthAttentionNotificationPhase.EXPIRED:
            return "has expired"
        if minutes_until_expiry is None:
            return "has an unknown expiry and requires attention"
        return f"will expire in about {max(1, round(minutes_until_expiry))} minutes"
