"""Durable email delivery for legal document update notifications.

Rows are enqueued by :meth:`LegalDocumentService.publish_version` when a publish
requests user notification. This module drains them through the existing
notification pipeline. Delivery is idempotent per
``(document_key, version_number, user_id)`` via the notification service's
idempotency key, so a retry after a lost acknowledgment cannot duplicate an
email that was already recorded as sent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.notifications.models import SendNotificationRequest
from src.notifications.service import notification_service

from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)

OUTBOX_TABLE = "legal_update_notification_outbox"
EVENT_KEY = "legal.documents_updated"
MAX_DELIVERY_BATCH = 50
MAX_ATTEMPTS = 10
BASE_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 6 * 60 * 60

DOCUMENT_URL_PATHS = {"terms": "/terms", "privacy": "/privacy"}


class LegalUpdateNotificationOutbox:
    """Send and retry legal document update emails from durable outbox rows."""

    def __init__(self, *, supabase_config_override: Any = None) -> None:
        """Initialize the outbox with a replaceable Supabase configuration."""
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
        self, *, limit: int = MAX_DELIVERY_BATCH
    ) -> dict[str, int]:
        """Deliver pending outbox rows; failures stay retryable.

        Rows are claimed by a conditional update on ``processed_at`` so two
        schedulers cannot deliver the same row concurrently. Per-row retries use
        bounded exponential backoff and stop after ``MAX_ATTEMPTS`` failures.

        Args:
            limit: Maximum rows to claim in one pass.

        Returns:
            Counters for claimed, succeeded, failed, and skipped rows.
        """
        summary = {"claimed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
        now = datetime.now(timezone.utc)

        try:
            result = (
                self.supabase.table(OUTBOX_TABLE)
                .select("*")
                .is_("processed_at", "null")
                .order("created_at")
                .limit(limit)
                .execute()
            )
        except Exception as error:
            logger.error("Failed to read legal update outbox: %s", error)
            summary["failed"] += 1
            return summary

        for row in result.data or []:
            row_id = str(row.get("id"))
            attempt_count = int(row.get("attempt_count") or 0)
            last_attempt_at = self._parse_datetime(row.get("last_attempt_at"))

            if attempt_count >= MAX_ATTEMPTS:
                summary["skipped"] += 1
                logger.error(
                    "Legal update outbox row %s exhausted retries (%s); leaving for ops",
                    row_id,
                    row.get("last_error"),
                )
                continue

            if not self._claim(row_id, last_attempt_at, attempt_count, now):
                summary["skipped"] += 1
                continue

            summary["claimed"] += 1
            try:
                response = await self._send_row(row)
                if not response.success:
                    raise RuntimeError(
                        response.message or "notification delivery failed"
                    )
                self.supabase.table(OUTBOX_TABLE).update(
                    {
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                        "last_error": None,
                    }
                ).eq("id", row_id).execute()
                summary["succeeded"] += 1
            except Exception as error:
                summary["failed"] += 1
                self._record_failure(row, error)
                logger.warning(
                    "Legal update outbox row %s will be retried: %s", row_id, error
                )
        return summary

    def _claim(
        self,
        row_id: str,
        last_attempt_at: datetime | None,
        attempt_count: int,
        now: datetime,
    ) -> bool:
        """Claim one pending row once its retry backoff has elapsed.

        The conditional update on ``last_attempt_at`` serializes concurrent
        schedulers: only the caller whose expected value matches writes.

        Returns:
            True when the row is claimed and due for an attempt.
        """
        if last_attempt_at is not None:
            backoff = min(
                BASE_BACKOFF_SECONDS * (2**attempt_count), MAX_BACKOFF_SECONDS
            )
            if last_attempt_at + timedelta(seconds=backoff) > now:
                return False

        expected = last_attempt_at.isoformat() if last_attempt_at else None
        payload: dict[str, Any] = {
            "last_attempt_at": now.isoformat(),
            "attempt_count": attempt_count + 1,
        }
        query = self.supabase.table(OUTBOX_TABLE).update(payload).eq("id", row_id)
        query = (
            query.is_("last_attempt_at", "null")
            if expected is None
            else query.eq("last_attempt_at", expected)
        )
        result = query.execute()
        return bool(result.data)

    async def _send_row(self, row: dict[str, Any]):
        """Send one legal document update email through the notification service."""
        document_key = str(row.get("document_key"))
        version_number = int(row.get("version_number") or 0)
        user_id = str(row.get("user_id"))
        user_name = row.get("recipient_name") or "there"
        path = DOCUMENT_URL_PATHS.get(document_key, "/")
        title = "Terms & Conditions" if document_key == "terms" else "Privacy Policy"

        request = SendNotificationRequest(
            event_key=EVENT_KEY,
            recipient_email=str(row.get("recipient_email")),
            recipient_name=row.get("recipient_name"),
            user_id=UUID(user_id),
            template_variables={
                "user_name": user_name,
                "document_title": title,
                "version_number": version_number,
                "summary_of_changes": row.get("summary_of_changes")
                or "See the updated document for details.",
                "document_url": f"{settings.app_base_url}{path}",
            },
            idempotency_key=f"legal:{document_key}:{version_number}:{user_id}",
            log_metadata={
                "document_key": document_key,
                "version_number": version_number,
                "dispatch_id": str(row.get("dispatch_id")),
            },
        )
        return await notification_service.send_notification(request)

    def _record_failure(self, row: dict[str, Any], error: Exception) -> None:
        """Persist retry diagnostics for a failed delivery attempt."""
        try:
            self.supabase.table(OUTBOX_TABLE).update(
                {"last_error": str(error)[:1000]}
            ).eq("id", str(row.get("id"))).execute()
        except Exception:
            logger.exception(
                "Failed to record legal update outbox retry for row %s", row.get("id")
            )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse an ISO-8601 timestamp string into an aware datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


legal_update_outbox = LegalUpdateNotificationOutbox()
