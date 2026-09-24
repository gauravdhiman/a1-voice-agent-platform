"""Durable Telegram and SMS delivery for OAuth connection alerts."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import uuid4

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
    """Persist and retry platform-admin Telegram/SMS OAuth alerts.

    The database claim function uses ``FOR UPDATE SKIP LOCKED`` so multiple
    Cloud Run instances can drain the same queue without sending the same row
    concurrently. Provider delivery is at-least-once: if the provider accepts
    a message and the database acknowledgment is lost, a retry can duplicate it.
    """

    @property
    def supabase(self):
        return supabase_config.service_client or supabase_config.client

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
        telegram_state = row.get("telegram_state", "pending")
        sms_state = row.get("sms_state", "pending")
        attempted_telegram = False
        attempted_sms = False
        failed = False
        message = self._message(payload)

        try:
            settings = await platform_notification_settings_service.get_settings()
        except Exception as exc:
            logger.error(
                "Could not load OAuth alert channel settings (%s)", type(exc).__name__
            )
            await self._complete(
                row,
                claim,
                telegram_state,
                sms_state,
                False,
                False,
                "channel_settings_unavailable",
                self._retry_delay(row),
            )
            return

        if telegram_state == "pending":
            try:
                (
                    token,
                    chat_id,
                    enabled,
                ) = await (
                    platform_notification_settings_service.get_telegram_credentials()
                )
                if not enabled or not token or not chat_id:
                    telegram_state = "skipped"
                else:
                    attempted_telegram = True
                    sent = await telegram_service.send_message(token, chat_id, message)
                    telegram_state = "sent" if sent else "pending"
                    failed = not sent
            except Exception as exc:
                logger.warning(
                    "OAuth Telegram alert delivery failed (%s)", type(exc).__name__
                )
                telegram_state = "pending"
                attempted_telegram = True
                failed = True

        if sms_state == "pending":
            phone = settings.platform_admin_sms_phone
            if (
                not settings.platform_admin_sms_notifications_enabled
                or not phone
                or not settings.sms_sender_configured
            ):
                sms_state = "skipped"
            else:
                try:
                    from src.phone_numbers.twilio_service import twilio_service

                    attempted_sms = True
                    sent = await twilio_service.send_sms(
                        phone, self._sms_message(payload)
                    )
                    sms_state = "sent" if sent else "pending"
                    failed = failed or not sent
                except Exception as exc:
                    logger.warning(
                        "OAuth SMS alert delivery failed (%s)", type(exc).__name__
                    )
                    sms_state = "pending"
                    attempted_sms = True
                    failed = True

        attempts = max(
            int(row.get("telegram_attempts") or 0),
            int(row.get("sms_attempts") or 0),
        )
        await self._complete(
            row,
            claim,
            telegram_state,
            sms_state,
            attempted_telegram,
            attempted_sms,
            "provider_delivery_failed" if failed else None,
            self._retry_delay(row, attempts + 1) if failed else 300,
        )

    async def _complete(
        self,
        row: dict[str, Any],
        claim: str,
        telegram_state: str,
        sms_state: str,
        attempted_telegram: bool,
        attempted_sms: bool,
        error_code: Optional[str],
        retry_seconds: int,
    ) -> None:
        try:
            result = self.supabase.rpc(
                "complete_oauth_attention_outbox",
                {
                    "p_id": row["id"],
                    "p_claim": claim,
                    "p_telegram_state": telegram_state,
                    "p_sms_state": sms_state,
                    "p_attempted_telegram": attempted_telegram,
                    "p_attempted_sms": attempted_sms,
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
                )
                + 1
            )
        return min(60 * 2 ** min(max(attempt, 1), 9), MAX_RETRY_SECONDS)


oauth_attention_outbox = OAuthAttentionOutbox()
