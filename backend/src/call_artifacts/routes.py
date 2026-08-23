"""Authenticated call recording metadata and playback routes."""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from src.auth.dependencies import assert_has_permission
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.call_recordings.factory import get_recording_storage
from shared.config import settings

from .models import (
    CallArtifact,
    CallArtifactsResponse,
    RecordingBatchDeleteRequest,
    RecordingBatchDeleteResponse,
)
from .service import call_artifact_service

logger = logging.getLogger(__name__)
call_artifacts_router = APIRouter(prefix="/api/v1/calls", tags=["Call Artifacts"])


def _check_delete_access(user_profile: UserProfile, organization_id: UUID) -> None:
    """Allow only platform admins or ``call_log:delete`` org admins."""
    assert_has_permission(
        user_profile,
        "call_log",
        "delete",
        organization_id,
        error_message=(
            "Only organization admins can delete call recordings"
        ),
    )


async def _delete_one_recording(
    artifact: dict[str, Any],
) -> tuple[bool, Optional[str]]:
    """Delete one recording's backing object after existence verification.

    Returns ``(True, None)`` when the object was deleted. On the R2 backend
    a missing object short-circuits to ``(False, "gone")`` so the caller can
    tombstone via :meth:`mark_recording_missing` instead of failing.
    """
    storage = get_recording_storage()
    object_key = artifact["storage_path"]
    if settings.recording_storage_backend == "r2":
        try:
            object_available = await storage.object_exists(object_key)
        except Exception as exc:  # noqa: BLE001 - provider boundary
            logger.exception("Could not verify recording object availability")
            return False, "storage_unreachable"
        if not object_available:
            return False, "gone"
    try:
        await storage.delete_object(object_key)
    except FileNotFoundError:
        # Local backend race: object already gone — treat as deleted.
        return True, None
    except Exception:  # noqa: BLE001 - provider boundary
        logger.exception("Could not delete recording object from storage")
        return False, "storage_unreachable"
    return True, None


@call_artifacts_router.delete("/{call_log_id}/recording")
async def delete_call_recording(
    call_log_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Response:
    """Delete one private recording, keeping the call log row intact.

    The audio object is removed from storage and the artifact row is
    tombstoned (``status='deleted'``) with audit metadata. Requires
    ``call_log:delete`` on the call's organization.
    """
    _, user_profile = user_data
    artifact, error = await call_artifact_service.get_recording(call_log_id)
    if error or artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    _check_delete_access(
        user_profile, UUID(str(artifact["organization_id"]))
    )

    deleted, failure = await _delete_one_recording(artifact)
    if failure == "gone":
        await call_artifact_service.mark_recording_missing(artifact)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Recording is no longer available",
        )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Recording storage could not be reached; nothing was deleted. "
                "Please try again later."
            ),
        )

    ok, tombstone_error = await call_artifact_service.mark_recording_deleted(
        artifact,
        deleted_by=str(user_data[0]),
    )
    if not ok:
        logger.error(
            "Recording object deleted but DB tombstone failed for call %s: %s",
            call_log_id,
            tombstone_error,
        )
    return Response(
        content=(
            '{"call_log_id": "%s", "status": "deleted"}' % str(call_log_id)
        ),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )


@call_artifacts_router.post("/recordings/delete-batch")
async def batch_delete_recordings(
    request: RecordingBatchDeleteRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> RecordingBatchDeleteResponse:
    """Delete several recordings in one audited request.

    Every call log must belong to ``request.organization_id``; cross-tenant
    IDs are reported as ``forbidden`` without touching their storage. The
    caller must hold ``call_log:delete`` on that organization. Call-log rows
    are never removed — only audio artifacts are deleted and tombstoned.
    """
    user_id, user_profile = user_data
    _check_delete_access(user_profile, request.organization_id)

    items: list[dict[str, str]] = []
    deleted_count = 0
    storage = get_recording_storage()
    for call_log_id in request.call_log_ids:
        try:
            log_uuid = UUID(str(call_log_id))
        except ValueError:
            items.append(
                {
                    "call_log_id": str(call_log_id),
                    "status": "not_found",
                    "detail": "Invalid call identifier",
                }
            )
            continue

        artifact, error = await call_artifact_service.get_recording(log_uuid)
        if error or artifact is None:
            items.append(
                {
                    "call_log_id": str(call_log_id),
                    "status": "not_found",
                    "detail": error or "Recording not found",
                }
            )
            continue

        artifact_org = UUID(str(artifact["organization_id"]))
        if (
            not user_profile.has_role("platform_admin")
            and artifact_org != request.organization_id
        ):
            logger.warning(
                "Batch delete skipped cross-tenant recording %s (org %s)",
                call_log_id,
                artifact_org,
            )
            items.append(
                {
                    "call_log_id": str(call_log_id),
                    "status": "forbidden",
                    "detail": "Recording belongs to a different organization",
                }
            )
            continue

        deleted, failure = await _delete_one_recording(artifact)
        if failure == "gone":
            await call_artifact_service.mark_recording_missing(artifact)
            items.append(
                {
                    "call_log_id": str(call_log_id),
                    "status": "deleted",
                    "detail": "Already unavailable; metadata updated",
                }
            )
            deleted_count += 1
            continue
        if not deleted:
            items.append(
                {
                    "call_log_id": str(call_log_id),
                    "status": "failed",
                    "detail": (
                        "Storage could not be reached; recording was kept"
                    ),
                }
            )
            continue

        ok, _tombstone_error = await call_artifact_service.mark_recording_deleted(
            artifact,
            deleted_by=str(user_id),
            reason=request.reason,
        )
        items.append(
            {
                "call_log_id": str(call_log_id),
                "status": "deleted" if ok else "failed",
                "detail": None if ok else "Could not update call record",
            }
        )
        if ok:
            deleted_count += 1

    return RecordingBatchDeleteResponse(
        items=items,
        deleted_count=deleted_count,
    )


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
