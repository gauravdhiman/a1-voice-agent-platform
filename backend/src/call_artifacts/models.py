"""Pydantic response models for call artifacts."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID



class CallArtifact(BaseModel):
    """Organization-scoped metadata for one call artifact."""

    id: UUID
    call_log_id: UUID
    organization_id: UUID
    artifact_type: str
    status: str
    encryption_mode: str = "provider_managed"
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    retention_expires_at: Optional[datetime] = None
    download_url: Optional[str] = None


class CallArtifactsResponse(BaseModel):
    """Artifact metadata for one call."""

    items: list[CallArtifact]


MAX_BATCH_RECORDING_DELETE = 100


class RecordingBatchDeleteRequest(BaseModel):
    """Request body for deleting several recordings at once.

    Call-log rows are never deleted; only the audio artifacts are removed.
    The organization_id must match the caller's org-admin scope so a stale
    UI selection cannot cross tenants.
    """

    call_log_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_BATCH_RECORDING_DELETE,
        description="Call log IDs whose recordings should be deleted (1-100).",
    )
    organization_id: UUID = Field(
        ...,
        description=(
            "Organization scope of the deletion; every call log must belong "
            "to this organization."
        ),
    )
    reason: str = Field(
        default="user_requested",
        max_length=64,
        description="Machine-readable audit reason for the deletion.",
    )


class RecordingBatchDeleteItem(BaseModel):
    """Per-call outcome inside a batch recording deletion."""

    call_log_id: str = Field(..., description="Call log ID the item refers to.")
    status: str = Field(
        ...,
        description=(
            "One of: deleted, forbidden, not_found, not_deletable, failed."
        ),
    )
    detail: Optional[str] = Field(
        None, description="Human-readable context for non-deleted outcomes."
    )


class RecordingBatchDeleteResponse(BaseModel):
    """Aggregate result of a batch recording deletion."""

    items: list[RecordingBatchDeleteItem]
    deleted_count: int
