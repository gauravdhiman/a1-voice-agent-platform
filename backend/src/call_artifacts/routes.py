"""Authenticated call recording metadata and playback routes."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.call_recordings.factory import get_recording_storage
from shared.config import settings

from .models import CallArtifact, CallArtifactsResponse
from .service import call_artifact_service

logger = logging.getLogger(__name__)
call_artifacts_router = APIRouter(prefix="/api/v1/calls", tags=["Call Artifacts"])


def _check_artifact_access(user_profile: UserProfile, organization_id: UUID) -> None:
    """Allow only platform admins or org admins to access call recordings."""
    if user_profile.has_role("platform_admin"):
        return
    if user_profile.has_role("org_admin", str(organization_id)):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization or platform administrators can access recordings",
    )


@call_artifacts_router.get(
    "/{call_log_id}/artifacts", response_model=CallArtifactsResponse
)
async def list_call_artifacts(
    call_log_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> CallArtifactsResponse:
    """List non-sensitive artifact metadata for an authorized call."""
    _, user_profile = user_data
    organization_id, error = await call_artifact_service.get_organization_id(
        call_log_id
    )
    if error or organization_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    _check_artifact_access(user_profile, organization_id)

    rows, error = await call_artifact_service.list_artifacts(call_log_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    items = [
        CallArtifact(
            **row,
            download_url=(
                f"/api/v1/calls/{call_log_id}/recording"
                if row.get("artifact_type") == "recording"
                and row.get("status") == "completed"
                else None
            ),
        )
        for row in rows
    ]
    return CallArtifactsResponse(items=items)


@call_artifacts_router.get("/{call_log_id}/recording")
async def download_call_recording(
    call_log_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Stream a private recording through the authenticated backend."""
    _, user_profile = user_data
    artifact, error = await call_artifact_service.get_recording(call_log_id)
    if error or artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    _check_artifact_access(user_profile, UUID(str(artifact["organization_id"])))

    storage = get_recording_storage()
    object_key = artifact["storage_path"]
    if settings.recording_storage_backend == "r2":
        # Do this only after an admin clicks Listen. Call-list queries rely on
        # database metadata and never fan out into one storage request per row.
        try:
            object_available = await storage.object_exists(object_key)
        except Exception as exc:  # noqa: BLE001 - provider boundary
            logger.exception("Could not verify recording object availability")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Recording storage could not be reached",
            ) from exc
        if not object_available:
            await call_artifact_service.mark_recording_missing(artifact)
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Recording is no longer available",
            )
        # Stream through the authenticated API instead of redirecting the
        # browser to R2. This works for localhost, a future staging origin,
        # and production without requiring per-bucket browser CORS rules.
        # TODO: [Performance] Revisit direct signed playback with explicit R2
        # CORS when recording traffic justifies bypassing backend bandwidth.
        return StreamingResponse(
            storage.stream_object(object_key),
            media_type=artifact.get("mime_type") or "audio/wav",
            headers={"Content-Disposition": "inline; filename=recording.wav"},
        )

    try:
        content = await storage.read_object(object_key)
    except FileNotFoundError as exc:
        await call_artifact_service.mark_recording_missing(artifact)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Recording is no longer available",
        ) from exc
    return Response(
        content=content,
        media_type=artifact.get("mime_type") or "audio/wav",
        headers={"Content-Disposition": "inline; filename=recording.wav"},
    )
