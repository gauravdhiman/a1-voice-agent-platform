"""Durable per-channel delivery for public interest-lead alerts."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from src.leads.service import lead_service
from src.notifications.lead_notifier import interest_lead_notifier
from src.notifications.platform_settings_service import (
    platform_notification_settings_service,
)
from src.notifications.whatsapp_service import whatsapp_service

from shared.config import supabase_config

logger = logging.getLogger(__name__)

OUTBOX_TABLE = "interest_lead_notification_outbox"
CLAIM_LEASE_SECONDS = 60
MAX_DELIVERY_BATCH = 50
MAX_RETRY_SECONDS = 6 * 60 * 60


class InterestLeadNotificationOutbox:
    """Persist and retry lead alerts independently for each admin channel.

    The interest-lead insert trigger creates the outbox row in the same
    database transaction. The worker retries channels that fail and never
    resends a channel already acknowledged as sent.
    """

    def __init__(
        self,
        *,
        notifier: Any = None,
        lead_service_override: Any = None,
        platform_settings_service: Any = None,
        supabase_config_override: Any = None,
    ) -> None:
        """Initialize delivery dependencies for runtime or isolated tests."""
        self.notifier = (
            notifier if notifier is not None else interest_lead_notifier
        )
        self.lead_service = (
            lead_service_override
            if lead_service_override is not None
            else lead_service
        )
        self.platform_settings_service = (
            platform_settings_service
            if platform_settings_service is not None
            else platform_notification_settings_service
        )
        self._supabase_config = (
            supabase_config_override
            if supabase_config_override is not None
            else supabase_config
        )

    @property
    def supabase(self):
        """Return the configured service-role Supabase client."""
        return self._supabase_config.service_client or self._supabase_config.client

    async def process_pending(
        self, *, lead_id: Optional[UUID] = None, limit: int = MAX_DELIVERY_BATCH
    ) -> int:
        """Claim and deliver due lead alerts, optionally for one new lead."""
        claim = str(uuid4())
        try:
            response = self.supabase.rpc(
                "claim_interest_lead_notification_outbox",
                {
                    "p_claim": claim,
                    "p_lead_id": str(lead_id) if lead_id else None,
                    "p_limit": min(max(limit, 1), MAX_DELIVERY_BATCH),
                    "p_lease_seconds": CLAIM_LEASE_SECONDS,
                },
            ).execute()
            rows = getattr(response, "data", None) or []
        except Exception as exc:
            logger.error(
                "Could not claim interest-lead alerts (%s)", type(exc).__name__
            )
            return 0

        for row in rows:
            await self._deliver_claimed(row, claim)
        return len(rows)

    async def _deliver_claimed(self, row: dict[str, Any], claim: str) -> None:
        """Attempt pending channels and save a safe retry state."""
        states = {
            channel: row.get(f"{channel}_state", "pending")
            for channel in ("email", "telegram", "whatsapp")
        }
        attempted = {channel: False for channel in states}
        errors: list[str] = []

        try:
            lead_id = UUID(str(row["lead_id"]))
            lead, lookup_error = await self.lead_service.get_lead(lead_id)
            if lookup_error or lead is None:
                raise RuntimeError("lead lookup failed")
            platform_settings = await self.platform_settings_service.get_settings()
        except Exception as exc:
            logger.warning(
                "Could not load interest lead for alert delivery (%s)",
                type(exc).__name__,
            )
            errors.append("lead_or_settings_lookup_failed")
            await self._complete_claim(
                row, claim, states, attempted, errors, retry_seconds=300
            )
            return

        if states["email"] == "pending":
            if not self.notifier._email_is_configured(platform_settings):
                errors.append("email_configuration_missing")
            else:
                attempted["email"] = True
                try:
                    await self.notifier._send_email(lead, platform_settings)
                    states["email"] = "sent"
                except Exception as exc:
                    logger.warning(
                        "Interest-lead email delivery failed (%s)",
                        type(exc).__name__,
                    )
                    errors.append("email_delivery_failed")

        if states["telegram"] == "pending":
            if not platform_settings.telegram_notifications_enabled:
                states["telegram"] = "skipped"
            else:
                attempted["telegram"] = True
                try:
                    await self.notifier._send_telegram(lead)
                    states["telegram"] = "sent"
                except Exception as exc:
                    logger.warning(
                        "Interest-lead Telegram delivery failed (%s)",
                        type(exc).__name__,
                    )
                    errors.append("telegram_delivery_failed")

        if states["whatsapp"] == "pending":
            if not platform_settings.platform_admin_whatsapp_notifications_enabled:
                states["whatsapp"] = "skipped"
            elif (
                not platform_settings.platform_admin_whatsapp_phone
                or not whatsapp_service.is_configured()
            ):
                errors.append("whatsapp_configuration_missing")
            else:
                attempted["whatsapp"] = True
                try:
                    await self.notifier._send_whatsapp(lead, platform_settings)
                    states["whatsapp"] = "sent"
                except Exception as exc:
                    logger.warning(
                        "Interest-lead WhatsApp delivery failed (%s)",
                        type(exc).__name__,
                    )
                    errors.append("whatsapp_delivery_failed")

        attempts = [
            int(row.get(f"{channel}_attempts") or 0)
            for channel in states
            if states[channel] == "pending"
        ]
        retry_seconds = min(
            300 * 2 ** min(max(attempts, default=0), 6), MAX_RETRY_SECONDS
        )
        await self._complete_claim(
            row, claim, states, attempted, errors, retry_seconds=retry_seconds
        )

    async def _complete_claim(
        self,
        row: dict[str, Any],
        claim: str,
        states: dict[str, str],
        attempted: dict[str, bool],
        errors: list[str],
        *,
        retry_seconds: int,
    ) -> None:
        """Persist delivery results without storing provider or lead details."""
        try:
            self.supabase.rpc(
                "complete_interest_lead_notification_outbox",
                {
                    "p_id": str(row["id"]),
                    "p_claim": claim,
                    "p_email_state": states["email"],
                    "p_telegram_state": states["telegram"],
                    "p_whatsapp_state": states["whatsapp"],
                    "p_attempted_email": attempted["email"],
                    "p_attempted_telegram": attempted["telegram"],
                    "p_attempted_whatsapp": attempted["whatsapp"],
                    "p_error_code": ",".join(errors) or None,
                    "p_retry_seconds": retry_seconds,
                },
            ).execute()
        except Exception as exc:
            logger.error(
                "Could not save interest-lead alert state (%s)",
                type(exc).__name__,
            )


interest_lead_notification_outbox = InterestLeadNotificationOutbox()

__all__ = ["InterestLeadNotificationOutbox", "interest_lead_notification_outbox"]
