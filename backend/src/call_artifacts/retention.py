"""Bounded, retry-safe removal of recordings past their stored retention date."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from shared.call_recordings.factory import get_recording_storage
from shared.config import supabase_config

logger = logging.getLogger(__name__)


def recording_expired(artifact: dict[str, Any]) -> bool:
    """Deny expired or malformed retention dates; legacy null dates remain valid."""
    value = artifact.get("retention_expires_at")
    if value is None:
        return False
    try:
        expiry = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
        if expiry.tzinfo is None:
            return True
        return expiry <= datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return True


async def remove_expired_recordings(
    batch_size: int = 100, *, strict: bool = False
) -> int:
    """Delete at most 100 expired audio objects and retain audited tombstones.

    Object deletion is idempotent. A provider or metadata failure leaves the row
    eligible for the next pass. Multiple workers may delete the same immutable
    key safely; conditional updates preserve concurrent manual tombstones.
    Exceptions contain no object paths in the operational event.
    """
    client = supabase_config.service_client
    now = datetime.now(timezone.utc).isoformat()

    def load():
        return (
            client.table("call_artifacts")
            .select("*")
            .eq("artifact_type", "recording")
            .eq("status", "completed")
            .lte("retention_expires_at", now)
            .order("retention_expires_at")
            .limit(max(1, min(batch_size, 100)))
            .execute()
        )

    rows = (await asyncio.to_thread(load)).data or []
    if not rows:
        return 0
    storage = get_recording_storage()
    removed = 0
    failed = False
    for artifact in rows:
        if not recording_expired(artifact) or not artifact.get("storage_path"):
            continue
        try:
            await storage.delete_object(artifact["storage_path"])
            metadata = dict(artifact.get("metadata") or {})
            metadata["deletion"] = {
                "reason": "retention_expired",
                "deleted_by": "system",
                "deleted_at": now,
            }

            def tombstone():
                return (
                    client.table("call_artifacts")
                    .update(
                        {"status": "deleted", "metadata": metadata, "updated_at": now}
                    )
                    .eq("id", str(artifact["id"]))
                    .eq("status", "completed")
                    .execute()
                )

            if (await asyncio.to_thread(tombstone)).data:
                removed += 1
        except Exception:
            failed = True
            logger.exception(
                "Recording retention cleanup failed",
                extra={"event.name": "recording.retention_failed"},
            )
    if strict and failed:
        raise RuntimeError("Recording retention pass had failures")
    return removed
