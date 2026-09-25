"""Durable Telegram and SMS delivery for OAuth connection alerts."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from src.notifications.organization_settings_service import (
    organization_notification_settings_service,
)
from src.notifications.platform_settings_service import (
    platform_notification_settings_service,
)
from src.notifications.telegram_service import telegram_service

from shared.config import supabase_config

logger = logging.getLogger(__name__)

OUTBOX_TABLE = "oauth_attention_outbox"
CLAIM_LEASE_SECONDS = 60
MAX_DELIVERY_BATCH = 50
MAX_RETRY_SECONDS = 6 * 60 * 60


class OAuthAttentionOutbox:
    """Persist and retry platform and organization Telegram/SMS OAuth alerts.

    The database claim function uses ``FOR UPDATE SKIP LOCKED`` so multiple
    application instances can drain the queue without claiming the same row.
    Each destination has an independent state, so a retry never re-sends a
    channel that has already completed. Provider delivery is at-least-once: if
    a provider accepts a message and the database acknowledgment is lost, a
    retry can duplicate it.
    """

    def __init__(
        self,
        *,
        platform_settings_service: Any = None,
        organization_settings_service: Any = None,
        telegram_sender: Any = None,
        supabase_config_override: Any = None,
    ) -> None:
        """Initialize the outbox with replaceable delivery dependencies."""
        self.platform_settings_service = (
            platform_settings_service
            if platform_settings_service is not None
            else platform_notification_settings_service
        )
        self.organization_settings_service = (
            organization_settings_service
            if organization_settings_service is not None
            else organization_notification_settings_service
        )
        self.telegram_sender = (
            telegram_sender if telegram_sender is not None else telegram_service
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

    async def enqueue(
        self,
        *,
        event_key: str,
        agent_tool_id: str,
        organization_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Write one idempotent alert event, then make a delivery attempt."""
        self.supabase.table(OUTBOX_TABLE).upsert(
            {
                "event_key": event_key,
                "agent_tool_id": agent_tool_id,
                "organization_id": organization_id,
                "payload": payload,
            },
            on_conflict="event_key",
            ignore_duplicates=True,
        ).execute()
        await self.process_pending(event_key=event_key, limit=1)

    async def process_pending(
        self, *, event_key: Optional[str] = None, limit: int = MAX_DELIVERY_BATCH
    ) -> int:
        """Claim and attempt due channel deliveries; failures remain retryable."""
        claim = str(uuid4())
        try:
            response = self.supabase.rpc(
                "claim_oauth_attention_outbox",
                {
                    "p_claim": claim,
                    "p_event_key": event_key,
                    "p_limit": min(max(limit, 1), MAX_DELIVERY_BATCH),
                    "p_lease_seconds": CLAIM_LEASE_SECONDS,
                },
            ).execute()
            rows = getattr(response, "data", None) or []
        except Exception as exc:
            logger.error(
                "Could not claim OAuth alert deliveries (%s)", type(exc).__name__
            )
            return 0

        for row in rows:
            await self._deliver_claimed(row, claim)
        return len(rows)

    async def _deliver_claimed(self, row: dict[str, Any], claim: str) -> None:
        payload = row.get("payload") or {}
        states = {
            "telegram": row.get("telegram_state", "pending"),
            "sms": row.get("sms_state", "pending"),
            "organization_telegram": row.get("organization_telegram_state", "pending"),
            "organization_sms": row.get("organization_sms_state", "pending"),
        }
        attempted = {name: False for name in states}
        failed = False
        message = self._message(payload)
        platform_settings = None
        organization_delivery_settings = None

        if states["sms"] == "pending" or states["organization_sms"] == "pending":
            try:
                platform_settings = await self.platform_settings_service.get_settings()
            except Exception as exc:
                logger.error(
                    "Could not load platform SMS settings (%s)",
                    type(exc).__name__,
                )
                if states["sms"] == "pending":
                    attempted["sms"] = True
                if states["organization_sms"] == "pending":
                    attempted["organization_sms"] = True
                failed = True

        if (
            states["organization_telegram"] == "pending"
            or states["organization_sms"] == "pending"
        ):
            try:
                organization_delivery_settings = (
                    await self.organization_settings_service.get_delivery_settings(
                        UUID(str(row["organization_id"]))
                    )
                )
            except Exception as exc:
                logger.error(
                    "Could not load organization OAuth alert settings (%s)",
                    type(exc).__name__,
                )
                attempted["organization_telegram"] = (
                    states["organization_telegram"] == "pending"
                )
                attempted["organization_sms"] = states["organization_sms"] == "pending"
                failed = True

        if states["telegram"] == "pending":
            try:
                token, chat_id, enabled = (
                    await self.platform_settings_service.get_telegram_credentials()
                )
                if not enabled or not token or not chat_id:
                    states["telegram"] = "skipped"
                else:
                    attempted["telegram"] = True
                    sent = await self.telegram_sender.send_message(
                        token, chat_id, message
                    )
                    states["telegram"] = "sent" if sent else "pending"
                    failed = failed or not sent
            except Exception as exc:
                logger.warning(
                    "OAuth Telegram alert delivery failed (%s)", type(exc).__name__
                )
                attempted["telegram"] = True
                failed = True

        if states["sms"] == "pending" and platform_settings is not None:
            phone = platform_settings.platform_admin_sms_phone
            if (
                not platform_settings.platform_admin_sms_notifications_enabled
                or not phone
            ):
                states["sms"] = "skipped"
            elif not platform_settings.sms_sender_configured:
                attempted["sms"] = True
                failed = True
            else:
                try:
                    from src.phone_numbers.twilio_service import twilio_service

                    attempted["sms"] = True
                    sent = await twilio_service.send_sms(
                        phone, self._sms_message(payload)
                    )
                    states["sms"] = "sent" if sent else "pending"
                    failed = failed or not sent
                except Exception as exc:
                    logger.warning(
                        "OAuth SMS alert delivery failed (%s)", type(exc).__name__
                    )
                    attempted["sms"] = True
                    failed = True

        if organization_delivery_settings is not None:
            if states["organization_telegram"] == "pending":
                chat_id = organization_delivery_settings.telegram_chat_id
                bot_token = organization_delivery_settings.telegram_bot_token
                if (
                    not chat_id
                    or not organization_delivery_settings.telegram_bot_token_stored
                ):
                    states["organization_telegram"] = "skipped"
                elif not bot_token:
                    attempted["organization_telegram"] = True
                    failed = True
                else:
                    try:
                        attempted["organization_telegram"] = True
                        sent = await self.telegram_sender.send_message(
                            bot_token, chat_id, message
                        )
                        states["organization_telegram"] = "sent" if sent else "pending"
                        failed = failed or not sent
                    except Exception as exc:
                        logger.warning(
                            "Organization Telegram alert delivery failed (%s)",
                            type(exc).__name__,
                        )
                        attempted["organization_telegram"] = True
                        failed = True

            if states["organization_sms"] == "pending":
                phone = organization_delivery_settings.sms_phone
                if not phone:
                    states["organization_sms"] = "skipped"
                elif (
                    not platform_settings or not platform_settings.sms_sender_configured
                ):
                    attempted["organization_sms"] = True
                    failed = True
                else:
                    try:
                        from src.phone_numbers.twilio_service import twilio_service

                        attempted["organization_sms"] = True
                        sent = await twilio_service.send_sms(
                            phone, self._sms_message(payload)
                        )
                        states["organization_sms"] = "sent" if sent else "pending"
                        failed = failed or not sent
                    except Exception as exc:
                        logger.warning(
                            "Organization OAuth SMS alert delivery failed (%s)",
                            type(exc).__name__,
                        )
                        attempted["organization_sms"] = True
                        failed = True

        failed = failed or any(state == "pending" for state in states.values())
        attempts = max(
            int(row.get("telegram_attempts") or 0),
            int(row.get("sms_attempts") or 0),
            int(row.get("organization_telegram_attempts") or 0),
            int(row.get("organization_sms_attempts") or 0),
        )
        await self._complete(
            row,
            claim,
            states,
            attempted,
            "provider_delivery_failed" if failed else None,
            self._retry_delay(row, attempts + 1) if failed else 300,
        )

    async def _complete(
        self,
        row: dict[str, Any],
        claim: str,
        states: dict[str, str],
        attempted: dict[str, bool],
        error_code: Optional[str],
        retry_seconds: int,
    ) -> None:
        try:
            result = self.supabase.rpc(
                "complete_oauth_attention_outbox",
                {
                    "p_id": row["id"],
                    "p_claim": claim,
                    "p_telegram_state": states["telegram"],
                    "p_sms_state": states["sms"],
                    "p_organization_telegram_state": states["organization_telegram"],
                    "p_organization_sms_state": states["organization_sms"],
                    "p_attempted_telegram": attempted["telegram"],
                    "p_attempted_sms": attempted["sms"],
                    "p_attempted_organization_telegram": attempted[
                        "organization_telegram"
                    ],
                    "p_attempted_organization_sms": attempted["organization_sms"],
                    "p_error_code": error_code,
                    "p_retry_seconds": retry_seconds,
                },
            ).execute()
            data = getattr(result, "data", None)
            if isinstance(data, dict) and not data.get("updated"):
                logger.warning(
                    "OAuth alert delivery lease was lost before acknowledgment"
                )
        except Exception as exc:
            logger.error(
                "Could not acknowledge OAuth alert delivery (%s)", type(exc).__name__
            )

    @staticmethod
    def _message(payload: dict[str, Any]) -> str:
        """Build a provider-neutral message from safe, persisted display fields."""
        return (
            f"24x7 AI OAuth connection needs attention. "
            f"Organization: {payload.get('organization_name', 'your organization')}. "
            f"Agent: {payload.get('agent_name', 'the agent')}. "
            f"Tool: {payload.get('tool_name', 'connected tool')}. "
            f"Status: {payload.get('status_text', 'requires action')}. "
            f"{payload.get('reason', 'Reconnect the tool to restore access.')} "
            f"Next step: open the agent Tools page: {payload.get('action_url', '')}"
        )[:3500]

    @classmethod
    def _sms_message(cls, payload: dict[str, Any]) -> str:
        """Keep the SMS concise while retaining an actionable recovery link."""
        return cls._message(payload)[:900]

    @staticmethod
    def _retry_delay(row: dict[str, Any], attempt: Optional[int] = None) -> int:
        """Return bounded exponential backoff for a failed channel delivery."""
        if attempt is None:
            attempt = (
                max(
                    int(row.get("telegram_attempts") or 0),
                    int(row.get("sms_attempts") or 0),
                    int(row.get("organization_telegram_attempts") or 0),
                    int(row.get("organization_sms_attempts") or 0),
                )
                + 1
            )
        return min(60 * 2 ** min(max(attempt, 1), 9), MAX_RETRY_SECONDS)


oauth_attention_outbox = OAuthAttentionOutbox()
