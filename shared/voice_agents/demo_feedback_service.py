"""Visitor star ratings for public demo calls, stored in the platform.

Ratings are PII-free (demo slug plus a 1-5 score, never names or contact
details) and are recorded once per voice session: repeat taps update the
same row instead of ballot-stuffing. Like demo outcome receipts, the table
is service-role only with no public database policy; visitors write through
the signed receipt-token endpoint and platform admins read through the
service-role API. The PostHog funnel event remains the analytics copy.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from shared.config.supabase import supabase_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoFeedbackSummary:
    """Aggregate rating counts for one demo slug."""

    demo_slug: str
    count: int
    average_rating: Optional[float]


@dataclass(frozen=True)
class DemoFeedbackRecord:
    """One stored visitor rating, safe to show platform admins."""

    id: str
    session_id: str
    agent_id: str
    organization_id: str
    demo_slug: str
    rating: int
    created_at: str


def _response_rows(response: Any) -> list[dict[str, Any]]:
    """Return row dicts from a Supabase response without raising."""
    return list(getattr(response, "data", None) or [])


class DemoFeedbackService:
    """Persist and read PII-free public demo ratings."""

    def __init__(self, client: Any = None) -> None:
        self.client = client

    def _client(self) -> Any:
        """Resolve the service-role client at call time for testability."""
        return self.client or supabase_config.service_client

    async def submit(
        self,
        *,
        session_id: str,
        agent_id: str,
        organization_id: str,
        demo_slug: str,
        rating: int,
    ) -> bool:
        """Record one session's rating, updating any earlier tap.

        Args:
            session_id: Voice session the rating belongs to.
            agent_id: Demo agent that was rated.
            organization_id: Owning organization.
            demo_slug: Public demo slug.
            rating: Star value from 1 to 5.

        Returns:
            True when the row was stored. Out-of-range ratings are rejected
            without touching storage.
        """
        if not isinstance(rating, int) or not 1 <= rating <= 5:
            logger.warning("Rejected out-of-range demo rating")
            return False
        client = self._client()
        if client is None:
            return False
        row = {
            "session_id": session_id,
            "agent_id": agent_id,
            "organization_id": organization_id,
            "demo_slug": demo_slug,
            "rating": rating,
        }
        try:
            response = await asyncio.to_thread(
                lambda: client.table("demo_feedback")
                .upsert(row, on_conflict="session_id")
                .execute()
            )
        except Exception:
            logger.error("Demo feedback upsert failed", exc_info=True)
            return False
        return bool(_response_rows(response))

    async def summary(self) -> list[DemoFeedbackSummary]:
        """Aggregate rating counts and averages per demo slug."""
        client = self._client()
        if client is None:
            return []
        try:
            response = await asyncio.to_thread(
                lambda: client.table("demo_feedback")
                .select("demo_slug,rating")
                .execute()
            )
        except Exception:
            logger.error("Demo feedback summary failed", exc_info=True)
            return []
        totals: dict[str, list[int]] = {}
        for row in _response_rows(response):
            slug = str(row.get("demo_slug") or "")
            rating = row.get("rating")
            if not slug or not isinstance(rating, int):
                continue
            totals.setdefault(slug, []).append(rating)
        return [
            DemoFeedbackSummary(
                demo_slug=slug,
                count=len(ratings),
                average_rating=round(sum(ratings) / len(ratings), 2),
            )
            for slug, ratings in sorted(totals.items())
        ]

    async def recent(self, *, limit: int = 50) -> list[DemoFeedbackRecord]:
        """Return the newest ratings for the platform admin surface."""
        client = self._client()
        if client is None:
            return []
        try:
            response = await asyncio.to_thread(
                lambda: client.table("demo_feedback")
                .select(
                    "id,session_id,agent_id,organization_id,demo_slug,"
                    "rating,created_at"
                )
                .order("created_at", desc=True)
                .limit(max(1, min(limit, 200)))
                .execute()
            )
        except Exception:
            logger.error("Demo feedback listing failed", exc_info=True)
            return []
        records = []
        for row in _response_rows(response):
            try:
                records.append(
                    DemoFeedbackRecord(
                        id=str(row.get("id") or ""),
                        session_id=str(row.get("session_id") or ""),
                        agent_id=str(row.get("agent_id") or ""),
                        organization_id=str(row.get("organization_id") or ""),
                        demo_slug=str(row.get("demo_slug") or ""),
                        rating=int(row.get("rating") or 0),
                        created_at=str(row.get("created_at") or ""),
                    )
                )
            except (TypeError, ValueError):
                continue
        return records


demo_feedback_service = DemoFeedbackService()


__all__ = [
    "DemoFeedbackRecord",
    "DemoFeedbackSummary",
    "DemoFeedbackService",
    "demo_feedback_service",
]
