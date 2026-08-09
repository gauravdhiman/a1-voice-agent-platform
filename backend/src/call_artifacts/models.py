"""Pydantic response models for call artifacts."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


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
