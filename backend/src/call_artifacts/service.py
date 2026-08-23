"""Service methods for authorized call-artifact metadata and object access."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from shared.config import supabase_config

logger = logging.getLogger(__name__)


class CallArtifactService:
    """Read organization-owned artifacts without exposing storage credentials."""

    @property
    def supabase(self):
        """Return the shared service-role Supabase client."""
        return supabase_config.client

    async def get_organization_id(
        self, call_log_id: UUID
    ) -> tuple[Optional[UUID], Optional[str]]:
        """Resolve a call's organization from the database, never from the URL."""
        try:
            result = (
                self.supabase.table("call_logs")
                .select("organization_id")
                .eq("id", str(call_log_id))
                .limit(1)
                .execute()
            )
            if not result.data:
                return None, "Call log not found"
            return UUID(str(result.data[0]["organization_id"])), None
        except Exception as exc:  # noqa: BLE001 - service boundary
            logger.error("Error resolving call organization: %s", exc, exc_info=True)
            return None, str(exc)

    async def list_artifacts(
        self, call_log_id: UUID
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """Return all metadata rows for a call."""
        try:
            result = (
                self.supabase.table("call_artifacts")
                .select(
                    "id,call_log_id,organization_id,artifact_type,status,mime_type,"
                    "encryption_mode,size_bytes,duration_seconds,metadata,"
                    "retention_expires_at,created_at,updated_at"
                )
                .eq("call_log_id", str(call_log_id))
                .order("created_at")
                .execute()
            )
            return result.data or [], None
        except Exception as exc:  # noqa: BLE001 - service boundary
            logger.error("Error listing call artifacts: %s", exc, exc_info=True)
            return [], str(exc)

    async def get_recording(
        self, call_log_id: UUID
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Return one completed recording row, including its private object key."""
        try:
            result = (
                self.supabase.table("call_artifacts")
                .select("*")
                .eq("call_log_id", str(call_log_id))
                .eq("artifact_type", "recording")
                .limit(1)
                .execute()
            )
            if not result.data:
                return None, "Recording not found"
            row = result.data[0]
            if row.get("status") != "completed" or not row.get("storage_path"):
                return None, "Recording is not ready"
            return row, None
        except Exception as exc:  # noqa: BLE001 - service boundary
            logger.error("Error loading recording artifact: %s", exc, exc_info=True)
            return None, str(exc)

    async def mark_recording_missing(
        self, artifact: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Mark metadata unavailable after the backing object is gone.

        The row is retained for auditability, but its status no longer counts as
        playable. This prevents subsequent call-log refreshes from presenting a
        Listen action for an object that storage has already removed.

        Args:
            artifact: Completed recording metadata row containing its database ID
                and optional existing metadata.

        Returns:
            A ``(success, error)`` tuple. Storage cleanup failures are reported
            without masking the user's clear missing-recording response.
        """
        try:
            artifact_id = artifact.get("id")
            if not artifact_id:
                return False, "Recording artifact identifier is missing"
            metadata = dict(artifact.get("metadata") or {})
            metadata.update(
                {
                    "availability": "missing",
                    "missing_reason": "storage_object_not_found",
                    "missing_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self.supabase.table("call_artifacts").update(
                {
                    "status": "missing",
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", str(artifact_id)).execute()
            return True, None
        except Exception as exc:  # noqa: BLE001 - service boundary
            logger.error(
                "Error marking recording artifact missing: %s", exc, exc_info=True
            )
            return False, str(exc)

    async def mark_recording_deleted(
        self,
        artifact: dict[str, Any],
        *,
        deleted_by: str,
        reason: str = "user_requested",
    ) -> tuple[bool, Optional[str]]:
        """Tombstone one recording artifact after its object was removed.

        The database row is retained for auditability (mirroring
        :meth:`mark_recording_missing`), but the status flips to ``deleted``
        so call-log queries stop advertising a playable recording. Existing
        metadata is preserved and a ``deletion`` block records who deleted
        the audio, when, and why.

        Args:
            artifact: Completed recording metadata row containing its
                database ID and optional existing metadata.
            deleted_by: Identifier of the authenticated user who requested
                the deletion (used for audit).
            reason: Machine-readable deletion reason; defaults to
                ``user_requested`` for admin-initiated deletes.

        Returns:
            A ``(success, error)`` tuple. Database failures are reported via
            ``error`` without raising.

        Example:
            ```python
            ok, error = await call_artifact_service.mark_recording_deleted(
                artifact, deleted_by=str(user_id)
            )
            ```
        """
        try:
            artifact_id = artifact.get("id")
            if not artifact_id:
                return False, "Recording artifact identifier is missing"
            now = datetime.now(timezone.utc).isoformat()
            metadata = dict(artifact.get("metadata") or {})
            metadata["deletion"] = {
                "reason": reason,
                "deleted_by": deleted_by,
                "deleted_at": now,
            }
            self.supabase.table("call_artifacts").update(
                {
                    "status": "deleted",
                    "metadata": metadata,
                    "updated_at": now,
                }
            ).eq("id", str(artifact_id)).execute()
            return True, None
        except Exception as exc:  # noqa: BLE001 - service boundary
            logger.error(
                "Error marking recording artifact deleted: %s", exc, exc_info=True
            )
            return False, str(exc)


call_artifact_service = CallArtifactService()
